use petgraph::algo;
use petgraph::csr::Csr;
use petgraph::graph::{EdgeIndex, NodeIndex};
use petgraph::graphmap::GraphMap;
use petgraph::matrix_graph::MatrixGraph;
use petgraph::stable_graph::StableGraph;
use petgraph::unionfind::UnionFind as PetUnionFind;
use petgraph::visit::{Bfs, Dfs, EdgeRef, NodeIndexable};
use petgraph::{Directed, Direction, Undirected};
use pyo3::exceptions::{PyIndexError, PyValueError};
use pyo3::prelude::*;
use std::collections::HashMap;
use std::fmt::Write;

type PetDiGraph = petgraph::Graph<Py<PyAny>, Py<PyAny>, Directed>;
type PetUnGraph = petgraph::Graph<Py<PyAny>, Py<PyAny>, Undirected>;
type PetStableDiGraph = StableGraph<Py<PyAny>, Py<PyAny>, Directed>;
type PetFastDiGraph = petgraph::Graph<Py<PyAny>, f64, Directed>;
type PetGraphMap = GraphMap<i32, Py<PyAny>, Undirected>;
type PetDiGraphMap = GraphMap<i32, Py<PyAny>, Directed>;
type PetMatrixGraph = MatrixGraph<Py<PyAny>, f64, Directed>;
type PetCsrGraph = Csr<(), f64>;

/// Pre-extracts edge weights to f64 to enable GIL-free algorithm execution.
fn extract_edge_costs(graph: &PetDiGraph, py: Python<'_>) -> PyResult<HashMap<EdgeIndex, f64>> {
    let mut costs = HashMap::with_capacity(graph.edge_count());
    for edge in graph.edge_references() {
        let w: f64 = edge.weight().bind(py).extract::<f64>().map_err(|_| {
            PyValueError::new_err(format!(
                "Edge ({}, {}) weight cannot be converted to float",
                edge.source().index(),
                edge.target().index()
            ))
        })?;
        costs.insert(edge.id(), w);
    }
    Ok(costs)
}

fn py_obj_to_label(w: &Py<PyAny>, py: Python<'_>) -> String {
    w.bind(py)
        .str()
        .and_then(|s| s.to_str().map(|s| s.to_string()))
        .ok()
        .unwrap_or_else(|| "<error>".to_string())
}

/// Shared helper: filter floyd-warshall map to only finite, reachable entries.
/// petgraph encodes unreachable pairs as f64::MAX/2 (not f64::INFINITY),
/// so we must filter using a threshold slightly below that sentinel.
fn finalize_floyd_warshall<N: Copy + std::hash::Hash + Eq + Into<usize>>(
    map: HashMap<(N, N), f64>,
) -> HashMap<usize, HashMap<usize, f64>> {
    // petgraph initialises distances to f64::MAX/2 for unreachable pairs.
    // Anything at or above this threshold is treated as unreachable.
    const SENTINEL: f64 = f64::MAX / 4.0;
    let mut out: HashMap<usize, HashMap<usize, f64>> = HashMap::new();
    for ((u, v), w) in map {
        if w.is_finite() && w < SENTINEL {
            out.entry(u.into()).or_default().insert(v.into(), w);
        }
    }
    out
}

/// Shared helper: filter bellman-ford distances to only reachable nodes.
fn finalize_bellman_ford(distances: Vec<f64>) -> HashMap<usize, f64> {
    distances
        .into_iter()
        .enumerate()
        .filter(|(_, d)| d.is_finite())
        .map(|(i, d)| (i, d))
        .collect()
}

// ════════════════════════════════════════════════════════════
// UnionFind
// ════════════════════════════════════════════════════════════

#[pyclass]
pub struct UnionFind {
    inner: PetUnionFind<usize>,
    size: usize,
}

#[pymethods]
impl UnionFind {
    #[new]
    fn new(n: usize) -> Self {
        UnionFind {
            inner: PetUnionFind::new(n),
            size: n,
        }
    }
    fn find(&mut self, i: usize) -> usize {
        self.inner.find(i)
    }
    fn union(&mut self, i: usize, j: usize) -> bool {
        self.inner.union(i, j)
    }
    fn equiv(&mut self, i: usize, j: usize) -> bool {
        self.inner.find(i) == self.inner.find(j)
    }
    fn into_labeling(&self) -> Vec<usize> {
        self.inner.clone().into_labeling()
    }
    fn __repr__(&self) -> String {
        format!("UnionFind(size={})", self.size)
    }
    fn __len__(&self) -> usize {
        self.size
    }
}

// ════════════════════════════════════════════════════════════
// DiGraph
// ════════════════════════════════════════════════════════════

#[pyclass]
pub struct DiGraph {
    pub(crate) inner: PetDiGraph,
}

#[pymethods]
impl DiGraph {
    #[new]
    #[pyo3(signature = (nodes=0, edges=0))]
    fn new(nodes: usize, edges: usize) -> Self {
        DiGraph {
            inner: PetDiGraph::with_capacity(nodes, edges),
        }
    }

    #[staticmethod]
    #[pyo3(signature = (edges, node_count=None))]
    fn from_edges(
        py: Python<'_>,
        edges: Vec<(usize, usize, Py<PyAny>)>,
        node_count: Option<usize>,
    ) -> PyResult<Self> {
        let n = node_count.unwrap_or_else(|| {
            edges
                .iter()
                .flat_map(|(u, v, _)| [*u, *v])
                .max()
                .map_or(0, |m| m + 1)
        });
        let mut g = PetDiGraph::with_capacity(n, edges.len());
        // Use Python None as the default node weight (cleaner semantics than integer index).
        for _ in 0..n {
            g.add_node(py.None().into_bound(py).unbind());
        }
        for (u, v, w) in edges {
            g.add_edge(NodeIndex::new(u), NodeIndex::new(v), w);
        }
        Ok(DiGraph { inner: g })
    }

    fn add_node(&mut self, weight: Py<PyAny>) -> usize {
        self.inner.add_node(weight).index()
    }

    fn remove_node(&mut self, index: usize) -> Option<Py<PyAny>> {
        self.inner.remove_node(NodeIndex::new(index))
    }

    fn add_edge(&mut self, u: usize, v: usize, weight: Py<PyAny>) -> PyResult<usize> {
        if self.inner.node_weight(NodeIndex::new(u)).is_none()
            || self.inner.node_weight(NodeIndex::new(v)).is_none()
        {
            return Err(PyIndexError::new_err("Node index out of range"));
        }
        Ok(self
            .inner
            .add_edge(NodeIndex::new(u), NodeIndex::new(v), weight)
            .index())
    }

    fn update_edge(&mut self, u: usize, v: usize, weight: Py<PyAny>) -> PyResult<usize> {
        // Validate nodes to prevent Rust panic on out-of-bounds access.
        if self.inner.node_weight(NodeIndex::new(u)).is_none()
            || self.inner.node_weight(NodeIndex::new(v)).is_none()
        {
            return Err(PyIndexError::new_err("Node index out of range"));
        }
        Ok(self
            .inner
            .update_edge(NodeIndex::new(u), NodeIndex::new(v), weight)
            .index())
    }

    fn remove_edge(&mut self, index: usize) -> Option<Py<PyAny>> {
        self.inner.remove_edge(EdgeIndex::new(index))
    }

    fn clear(&mut self) {
        self.inner.clear();
    }

    fn clear_edges(&mut self) {
        self.inner.clear_edges();
    }

    fn reverse(&mut self) {
        self.inner.reverse();
    }

    #[getter]
    fn node_count(&self) -> usize {
        self.inner.node_count()
    }
    #[getter]
    fn edge_count(&self) -> usize {
        self.inner.edge_count()
    }
    #[getter]
    fn is_directed(&self) -> bool {
        true
    }

    fn node_weight(&self, py: Python<'_>, index: usize) -> Option<Py<PyAny>> {
        self.inner
            .node_weight(NodeIndex::new(index))
            .map(|w| w.clone_ref(py))
    }

    fn edge_weight(&self, py: Python<'_>, index: usize) -> Option<Py<PyAny>> {
        self.inner
            .edge_weight(EdgeIndex::new(index))
            .map(|w| w.clone_ref(py))
    }

    fn find_edge(&self, u: usize, v: usize) -> Option<usize> {
        self.inner
            .find_edge(NodeIndex::new(u), NodeIndex::new(v))
            .map(|e| e.index())
    }

    fn neighbors(&self, index: usize) -> Vec<usize> {
        self.inner
            .neighbors(NodeIndex::new(index))
            .map(|n| n.index())
            .collect()
    }

    fn out_degree(&self, index: usize) -> usize {
        self.inner
            .edges_directed(NodeIndex::new(index), Direction::Outgoing)
            .count()
    }

    fn in_degree(&self, index: usize) -> usize {
        self.inner
            .edges_directed(NodeIndex::new(index), Direction::Incoming)
            .count()
    }

    fn node_indices(&self) -> Vec<usize> {
        self.inner.node_indices().map(|n| n.index()).collect()
    }

    fn edge_indices(&self) -> Vec<usize> {
        self.inner.edge_indices().map(|e| e.index()).collect()
    }

    fn bfs(&self, start: usize) -> PyResult<Vec<usize>> {
        if self.inner.node_weight(NodeIndex::new(start)).is_none() {
            return Err(PyIndexError::new_err("Start node index out of range"));
        }
        let mut bfs = Bfs::new(&self.inner, NodeIndex::new(start));
        let mut res = Vec::with_capacity(self.inner.node_count());
        while let Some(nx) = bfs.next(&self.inner) {
            res.push(nx.index());
        }
        Ok(res)
    }

    fn dfs(&self, start: usize) -> PyResult<Vec<usize>> {
        if self.inner.node_weight(NodeIndex::new(start)).is_none() {
            return Err(PyIndexError::new_err("Start node index out of range"));
        }
        let mut dfs = Dfs::new(&self.inner, NodeIndex::new(start));
        let mut res = Vec::with_capacity(self.inner.node_count());
        while let Some(nx) = dfs.next(&self.inner) {
            res.push(nx.index());
        }
        Ok(res)
    }

    fn is_cyclic(&self, py: Python<'_>) -> bool {
        py.detach(|| algo::is_cyclic_directed(&self.inner))
    }

    fn toposort(&self, py: Python<'_>) -> PyResult<Vec<usize>> {
        let res = py.detach(|| algo::toposort(&self.inner, None));
        match res {
            Ok(nodes) => Ok(nodes.into_iter().map(|n| n.index()).collect()),
            Err(_) => Err(PyValueError::new_err("Graph has a cycle")),
        }
    }

    fn dijkstra(&self, py: Python<'_>, start: usize) -> PyResult<HashMap<usize, f64>> {
        if self.inner.node_weight(NodeIndex::new(start)).is_none() {
            return Err(PyIndexError::new_err("Start node index out of range"));
        }
        let edge_costs = extract_edge_costs(&self.inner, py)?;
        let res = py.detach(|| {
            algo::dijkstra(&self.inner, NodeIndex::new(start), None, |e| {
                *edge_costs.get(&e.id()).unwrap()
            })
        });
        Ok(res.into_iter().map(|(n, d)| (n.index(), d)).collect())
    }

    fn floyd_warshall(&self, py: Python<'_>) -> PyResult<HashMap<usize, HashMap<usize, f64>>> {
        let edge_costs = extract_edge_costs(&self.inner, py)?;
        let res =
            py.detach(|| algo::floyd_warshall(&self.inner, |e| *edge_costs.get(&e.id()).unwrap()));
        match res {
            Ok(map) => Ok(finalize_floyd_warshall(
                map.into_iter()
                    .map(|((u, v), w)| ((u.index(), v.index()), w))
                    .collect(),
            )),
            Err(_) => Err(PyValueError::new_err("Negative cycle detected")),
        }
    }

    #[pyo3(signature = (start, goal, k, weight_fn=None))]
    fn k_shortest_path(
        &self,
        py: Python<'_>,
        start: usize,
        goal: usize,
        k: usize,
        weight_fn: Option<Py<PyAny>>,
    ) -> PyResult<HashMap<usize, f64>> {
        if self.inner.node_weight(NodeIndex::new(start)).is_none()
            || self.inner.node_weight(NodeIndex::new(goal)).is_none()
        {
            return Err(PyIndexError::new_err("Node index out of range"));
        }

        let edge_costs = if let Some(wf) = weight_fn {
            let mut costs = HashMap::with_capacity(self.inner.edge_count());
            for edge in self.inner.edge_references() {
                let cost: f64 = wf
                    .call1(
                        py,
                        (
                            edge.source().index(),
                            edge.target().index(),
                            edge.weight().clone_ref(py),
                        ),
                    )?
                    .bind(py)
                    .extract()?;
                costs.insert(edge.id(), cost);
            }
            costs
        } else {
            extract_edge_costs(&self.inner, py)?
        };

        let res = py.detach(|| {
            algo::k_shortest_path(
                &self.inner,
                NodeIndex::new(start),
                Some(NodeIndex::new(goal)),
                k,
                |e| *edge_costs.get(&e.id()).unwrap(),
            )
        });
        Ok(res.into_iter().map(|(n, d)| (n.index(), d)).collect())
    }

    fn astar(
        &self,
        py: Python<'_>,
        start: usize,
        goal: usize,
        heuristic: Py<PyAny>,
    ) -> PyResult<Option<(f64, Vec<usize>)>> {
        if self.inner.node_weight(NodeIndex::new(start)).is_none()
            || self.inner.node_weight(NodeIndex::new(goal)).is_none()
        {
            return Err(PyIndexError::new_err("Node index out of range"));
        }
        let edge_costs = extract_edge_costs(&self.inner, py)?;
        // Pre-compute heuristic for all nodes to enable safe GIL release during search.
        let mut h_values = vec![0.0f64; self.inner.node_bound()];
        for idx in self.inner.node_indices() {
            h_values[idx.index()] = heuristic
                .call1(py, (idx.index(),))
                .and_then(|v| v.bind(py).extract::<f64>())
                .unwrap_or(0.0);
        }
        let res = py.detach(|| {
            algo::astar(
                &self.inner,
                NodeIndex::new(start),
                |finish| finish.index() == goal,
                |e| *edge_costs.get(&e.id()).unwrap(),
                |n| h_values[n.index()],
            )
        });
        Ok(res.map(|(cost, path)| (cost, path.into_iter().map(|n| n.index()).collect())))
    }

    fn tarjan_scc(&self, py: Python<'_>) -> Vec<Vec<usize>> {
        py.detach(|| {
            algo::tarjan_scc(&self.inner)
                .into_iter()
                .map(|scc| scc.into_iter().map(|n| n.index()).collect())
                .collect()
        })
    }

    fn kosaraju_scc(&self, py: Python<'_>) -> Vec<Vec<usize>> {
        py.detach(|| {
            algo::kosaraju_scc(&self.inner)
                .into_iter()
                .map(|scc| scc.into_iter().map(|n| n.index()).collect())
                .collect()
        })
    }

    #[pyo3(signature = (from_node, to_node, min_intermediate_nodes=0, max_intermediate_nodes=None))]
    fn all_simple_paths(
        &self,
        py: Python<'_>,
        from_node: usize,
        to_node: usize,
        min_intermediate_nodes: usize,
        max_intermediate_nodes: Option<usize>,
    ) -> PyResult<Vec<Vec<usize>>> {
        if self.inner.node_weight(NodeIndex::new(from_node)).is_none()
            || self.inner.node_weight(NodeIndex::new(to_node)).is_none()
        {
            return Err(PyIndexError::new_err("Node index out of range"));
        }
        Ok(py.detach(|| {
            algo::all_simple_paths::<Vec<_>, _>(
                &self.inner,
                NodeIndex::new(from_node),
                NodeIndex::new(to_node),
                min_intermediate_nodes,
                max_intermediate_nodes,
            )
            .map(|path| path.into_iter().map(|n| n.index()).collect())
            .collect()
        }))
    }

    fn has_path_connecting(&self, py: Python<'_>, from: usize, to: usize) -> bool {
        py.detach(|| {
            algo::has_path_connecting(&self.inner, NodeIndex::new(from), NodeIndex::new(to), None)
        })
    }

    fn to_scipy_coo(&self, py: Python<'_>) -> PyResult<(Vec<u32>, Vec<u32>, Vec<f64>)> {
        let mut u_indices = Vec::with_capacity(self.inner.edge_count());
        let mut v_indices = Vec::with_capacity(self.inner.edge_count());
        let mut weights = Vec::with_capacity(self.inner.edge_count());

        for edge in self.inner.edge_references() {
            let w: f64 = edge.weight().bind(py).extract::<f64>().unwrap_or(1.0);
            u_indices.push(edge.source().index() as u32);
            v_indices.push(edge.target().index() as u32);
            weights.push(w);
        }
        Ok((u_indices, v_indices, weights))
    }

    #[pyo3(signature = (damping_factor=0.85, iterations=100))]
    fn page_rank(&self, py: Python<'_>, damping_factor: f64, iterations: usize) -> Vec<f64> {
        py.detach(|| algo::page_rank(&self.inner, damping_factor, iterations))
    }

    fn to_dot(&self, py: Python<'_>) -> String {
        let mut s = String::from("digraph {\n");
        for idx in self.inner.node_indices() {
            if let Some(w) = self.inner.node_weight(idx) {
                let _ = writeln!(
                    s,
                    "    {} [ label = \"{}\" ]",
                    idx.index(),
                    py_obj_to_label(w, py)
                );
            }
        }
        for edge in self.inner.edge_references() {
            let _ = writeln!(
                s,
                "    {} -> {} [ label = \"{}\" ]",
                edge.source().index(),
                edge.target().index(),
                py_obj_to_label(edge.weight(), py)
            );
        }
        s.push_str("}\n");
        s
    }

    fn __repr__(&self) -> String {
        format!(
            "DiGraph(nodes={}, edges={})",
            self.inner.node_count(),
            self.inner.edge_count()
        )
    }
    fn __len__(&self) -> usize {
        self.inner.node_count()
    }
    fn __bool__(&self) -> bool {
        self.inner.node_count() > 0
    }
    fn __contains__(&self, index: usize) -> bool {
        self.inner.node_weight(NodeIndex::new(index)).is_some()
    }
}

// ════════════════════════════════════════════════════════════
// UnGraph
// ════════════════════════════════════════════════════════════

#[pyclass]
pub struct UnGraph {
    pub(crate) inner: PetUnGraph,
}

#[pymethods]
impl UnGraph {
    #[new]
    #[pyo3(signature = (nodes=0, edges=0))]
    fn new(nodes: usize, edges: usize) -> Self {
        UnGraph {
            inner: PetUnGraph::with_capacity(nodes, edges),
        }
    }

    fn add_node(&mut self, weight: Py<PyAny>) -> usize {
        self.inner.add_node(weight).index()
    }

    fn remove_node(&mut self, index: usize) -> Option<Py<PyAny>> {
        self.inner.remove_node(NodeIndex::new(index))
    }

    fn add_edge(&mut self, u: usize, v: usize, weight: Py<PyAny>) -> PyResult<usize> {
        if self.inner.node_weight(NodeIndex::new(u)).is_none()
            || self.inner.node_weight(NodeIndex::new(v)).is_none()
        {
            return Err(PyIndexError::new_err("Node index out of range"));
        }
        Ok(self
            .inner
            .add_edge(NodeIndex::new(u), NodeIndex::new(v), weight)
            .index())
    }

    #[getter]
    fn node_count(&self) -> usize {
        self.inner.node_count()
    }
    #[getter]
    fn edge_count(&self) -> usize {
        self.inner.edge_count()
    }
    #[getter]
    fn is_directed(&self) -> bool {
        false
    }

    fn degree(&self, index: usize) -> usize {
        self.inner.edges(NodeIndex::new(index)).count()
    }

    fn clear(&mut self) {
        self.inner.clear();
    }

    fn connected_components(&self, py: Python<'_>) -> usize {
        py.detach(|| algo::connected_components(&self.inner))
    }

    fn bfs(&self, start: usize) -> PyResult<Vec<usize>> {
        if self.inner.node_weight(NodeIndex::new(start)).is_none() {
            return Err(PyIndexError::new_err("Start node index out of range"));
        }
        let mut bfs = Bfs::new(&self.inner, NodeIndex::new(start));
        let mut res = Vec::with_capacity(self.inner.node_count());
        while let Some(nx) = bfs.next(&self.inner) {
            res.push(nx.index());
        }
        Ok(res)
    }

    fn dfs(&self, start: usize) -> PyResult<Vec<usize>> {
        if self.inner.node_weight(NodeIndex::new(start)).is_none() {
            return Err(PyIndexError::new_err("Start node index out of range"));
        }
        let mut dfs = Dfs::new(&self.inner, NodeIndex::new(start));
        let mut res = Vec::with_capacity(self.inner.node_count());
        while let Some(nx) = dfs.next(&self.inner) {
            res.push(nx.index());
        }
        Ok(res)
    }

    fn find_edge(&self, u: usize, v: usize) -> Option<usize> {
        self.inner
            .find_edge(NodeIndex::new(u), NodeIndex::new(v))
            .map(|e| e.index())
    }

    fn edge_weight(&self, py: Python<'_>, index: usize) -> Option<Py<PyAny>> {
        self.inner
            .edge_weight(EdgeIndex::new(index))
            .map(|w| w.clone_ref(py))
    }

    fn edge_indices(&self) -> Vec<usize> {
        self.inner.edge_indices().map(|e| e.index()).collect()
    }

    fn node_indices(&self) -> Vec<usize> {
        self.inner.node_indices().map(|n| n.index()).collect()
    }

    fn has_path_connecting(&self, py: Python<'_>, from: usize, to: usize) -> bool {
        py.detach(|| {
            algo::has_path_connecting(&self.inner, NodeIndex::new(from), NodeIndex::new(to), None)
        })
    }

    fn is_bipartite(&self, py: Python<'_>, start: usize) -> bool {
        py.detach(|| algo::is_bipartite_undirected(&self.inner, NodeIndex::new(start)))
    }

    fn to_dot(&self, py: Python<'_>) -> String {
        let mut s = String::from("graph {\n");
        for idx in self.inner.node_indices() {
            if let Some(w) = self.inner.node_weight(idx) {
                let _ = writeln!(
                    s,
                    "    {} [ label = \"{}\" ]",
                    idx.index(),
                    py_obj_to_label(w, py)
                );
            }
        }
        for edge in self.inner.edge_references() {
            let _ = writeln!(
                s,
                "    {} -- {} [ label = \"{}\" ]",
                edge.source().index(),
                edge.target().index(),
                py_obj_to_label(edge.weight(), py)
            );
        }
        s.push_str("}\n");
        s
    }

    fn __repr__(&self) -> String {
        format!(
            "UnGraph(nodes={}, edges={})",
            self.inner.node_count(),
            self.inner.edge_count()
        )
    }
    fn __len__(&self) -> usize {
        self.inner.node_count()
    }
    fn __bool__(&self) -> bool {
        self.inner.node_count() > 0
    }
}

// ════════════════════════════════════════════════════════════
// FastDiGraph
// ════════════════════════════════════════════════════════════

#[pyclass]
pub struct FastDiGraph {
    pub(crate) inner: PetFastDiGraph,
}

#[pymethods]
impl FastDiGraph {
    #[new]
    #[pyo3(signature = (nodes=0, edges=0))]
    fn new(nodes: usize, edges: usize) -> Self {
        FastDiGraph {
            inner: PetFastDiGraph::with_capacity(nodes, edges),
        }
    }

    fn add_node(&mut self, weight: Py<PyAny>) -> usize {
        self.inner.add_node(weight).index()
    }

    fn add_edge(&mut self, u: usize, v: usize, weight: f64) -> PyResult<usize> {
        if self.inner.node_weight(NodeIndex::new(u)).is_none()
            || self.inner.node_weight(NodeIndex::new(v)).is_none()
        {
            return Err(PyIndexError::new_err("Node index out of range"));
        }
        Ok(self
            .inner
            .add_edge(NodeIndex::new(u), NodeIndex::new(v), weight)
            .index())
    }

    #[getter]
    fn node_count(&self) -> usize {
        self.inner.node_count()
    }
    #[getter]
    fn edge_count(&self) -> usize {
        self.inner.edge_count()
    }

    fn node_weight(&self, py: Python<'_>, index: usize) -> Option<Py<PyAny>> {
        self.inner
            .node_weight(NodeIndex::new(index))
            .map(|w| w.clone_ref(py))
    }

    fn dijkstra(&self, py: Python<'_>, start: usize) -> PyResult<HashMap<usize, f64>> {
        if self.inner.node_weight(NodeIndex::new(start)).is_none() {
            return Err(PyIndexError::new_err("Start node index out of range"));
        }
        let res =
            py.detach(|| algo::dijkstra(&self.inner, NodeIndex::new(start), None, |e| *e.weight()));
        Ok(res.into_iter().map(|(n, d)| (n.index(), d)).collect())
    }

    fn bellman_ford(&self, py: Python<'_>, start: usize) -> PyResult<HashMap<usize, f64>> {
        if self.inner.node_weight(NodeIndex::new(start)).is_none() {
            return Err(PyIndexError::new_err("Start node index out of range"));
        }
        let result = py.detach(|| algo::bellman_ford(&self.inner, NodeIndex::new(start)));
        match result {
            Ok(paths) => Ok(finalize_bellman_ford(paths.distances)),
            Err(_) => Err(PyValueError::new_err("Negative cycle detected")),
        }
    }

    fn floyd_warshall(&self, py: Python<'_>) -> PyResult<HashMap<usize, HashMap<usize, f64>>> {
        let res = py.detach(|| algo::floyd_warshall(&self.inner, |e| *e.weight()));
        match res {
            Ok(map) => Ok(finalize_floyd_warshall(
                map.into_iter()
                    .map(|((u, v), w)| ((u.index(), v.index()), w))
                    .collect(),
            )),
            Err(_) => Err(PyValueError::new_err("Negative cycle detected")),
        }
    }

    fn astar(
        &self,
        py: Python<'_>,
        start: usize,
        goal: usize,
        heuristic: Py<PyAny>,
    ) -> PyResult<Option<(f64, Vec<usize>)>> {
        if self.inner.node_weight(NodeIndex::new(start)).is_none()
            || self.inner.node_weight(NodeIndex::new(goal)).is_none()
        {
            return Err(PyIndexError::new_err("Node index out of range"));
        }
        let mut h_values = vec![0.0f64; self.inner.node_bound()];
        for idx in self.inner.node_indices() {
            h_values[idx.index()] = heuristic
                .call1(py, (idx.index(),))
                .and_then(|v| v.bind(py).extract::<f64>())
                .unwrap_or(0.0);
        }
        let res = py.detach(|| {
            algo::astar(
                &self.inner,
                NodeIndex::new(start),
                |finish| finish.index() == goal,
                |e| *e.weight(),
                |n| h_values[n.index()],
            )
        });
        Ok(res.map(|(cost, path)| (cost, path.into_iter().map(|n| n.index()).collect())))
    }

    fn is_cyclic(&self, py: Python<'_>) -> bool {
        py.detach(|| algo::is_cyclic_directed(&self.inner))
    }

    fn toposort(&self, py: Python<'_>) -> PyResult<Vec<usize>> {
        let res = py.detach(|| algo::toposort(&self.inner, None));
        match res {
            Ok(nodes) => Ok(nodes.into_iter().map(|n| n.index()).collect()),
            Err(_) => Err(PyValueError::new_err("Graph has a cycle")),
        }
    }

    fn tarjan_scc(&self, py: Python<'_>) -> Vec<Vec<usize>> {
        py.detach(|| {
            algo::tarjan_scc(&self.inner)
                .into_iter()
                .map(|scc| scc.into_iter().map(|n| n.index()).collect())
                .collect()
        })
    }

    fn has_path_connecting(&self, py: Python<'_>, from: usize, to: usize) -> bool {
        py.detach(|| {
            algo::has_path_connecting(&self.inner, NodeIndex::new(from), NodeIndex::new(to), None)
        })
    }

    fn to_scipy_coo(&self, _py: Python<'_>) -> PyResult<(Vec<u32>, Vec<u32>, Vec<f64>)> {
        let mut u_indices = Vec::with_capacity(self.inner.edge_count());
        let mut v_indices = Vec::with_capacity(self.inner.edge_count());
        let mut weights = Vec::with_capacity(self.inner.edge_count());

        for edge in self.inner.edge_references() {
            u_indices.push(edge.source().index() as u32);
            v_indices.push(edge.target().index() as u32);
            weights.push(*edge.weight());
        }
        Ok((u_indices, v_indices, weights))
    }

    // NOTE: page_rank is handled by the Python SciPy layer, same as DiGraph.

    fn bfs(&self, start: usize) -> PyResult<Vec<usize>> {
        if self.inner.node_weight(NodeIndex::new(start)).is_none() {
            return Err(PyIndexError::new_err("Start node index out of range"));
        }
        let mut bfs = Bfs::new(&self.inner, NodeIndex::new(start));
        let mut res = Vec::with_capacity(self.inner.node_count());
        while let Some(nx) = bfs.next(&self.inner) {
            res.push(nx.index());
        }
        Ok(res)
    }

    fn dfs(&self, start: usize) -> PyResult<Vec<usize>> {
        if self.inner.node_weight(NodeIndex::new(start)).is_none() {
            return Err(PyIndexError::new_err("Start node index out of range"));
        }
        let mut dfs = Dfs::new(&self.inner, NodeIndex::new(start));
        let mut res = Vec::with_capacity(self.inner.node_count());
        while let Some(nx) = dfs.next(&self.inner) {
            res.push(nx.index());
        }
        Ok(res)
    }

    #[pyo3(signature = (from_node, to_node, min_intermediate_nodes=0, max_intermediate_nodes=None))]
    fn all_simple_paths(
        &self,
        py: Python<'_>,
        from_node: usize,
        to_node: usize,
        min_intermediate_nodes: usize,
        max_intermediate_nodes: Option<usize>,
    ) -> PyResult<Vec<Vec<usize>>> {
        if self.inner.node_weight(NodeIndex::new(from_node)).is_none()
            || self.inner.node_weight(NodeIndex::new(to_node)).is_none()
        {
            return Err(PyIndexError::new_err("Node index out of range"));
        }
        Ok(py.detach(|| {
            algo::all_simple_paths::<Vec<_>, _>(
                &self.inner,
                NodeIndex::new(from_node),
                NodeIndex::new(to_node),
                min_intermediate_nodes,
                max_intermediate_nodes,
            )
            .map(|path| path.into_iter().map(|n| n.index()).collect())
            .collect()
        }))
    }

    fn to_dot(&self, py: Python<'_>) -> String {
        let mut s = String::from("digraph {\n");
        for idx in self.inner.node_indices() {
            if let Some(w) = self.inner.node_weight(idx) {
                let _ = writeln!(
                    s,
                    "    {} [ label = \"{}\" ]",
                    idx.index(),
                    py_obj_to_label(w, py)
                );
            }
        }
        for edge in self.inner.edge_references() {
            let _ = writeln!(
                s,
                "    {} -> {} [ label = \"{}\" ]",
                edge.source().index(),
                edge.target().index(),
                edge.weight()
            );
        }
        s.push_str("}\n");
        s
    }

    fn __repr__(&self) -> String {
        format!(
            "FastDiGraph(nodes={}, edges={})",
            self.inner.node_count(),
            self.inner.edge_count()
        )
    }
    fn __len__(&self) -> usize {
        self.inner.node_count()
    }
    fn __bool__(&self) -> bool {
        self.inner.node_count() > 0
    }
}

// ════════════════════════════════════════════════════════════
// StableDiGraph
// ════════════════════════════════════════════════════════════

#[pyclass]
pub struct StableDiGraph {
    inner: PetStableDiGraph,
}

#[pymethods]
impl StableDiGraph {
    #[new]
    fn new() -> Self {
        StableDiGraph {
            inner: PetStableDiGraph::new(),
        }
    }

    fn add_node(&mut self, weight: Py<PyAny>) -> usize {
        self.inner.add_node(weight).index()
    }
    fn remove_node(&mut self, index: usize) -> Option<Py<PyAny>> {
        self.inner.remove_node(NodeIndex::new(index))
    }
    fn add_edge(&mut self, u: usize, v: usize, weight: Py<PyAny>) -> PyResult<usize> {
        // Use contains_node only — node_bound() is unreliable after removals in StableGraph.
        if !self.inner.contains_node(NodeIndex::new(u))
            || !self.inner.contains_node(NodeIndex::new(v))
        {
            return Err(PyIndexError::new_err("Node does not exist"));
        }
        Ok(self
            .inner
            .add_edge(NodeIndex::new(u), NodeIndex::new(v), weight)
            .index())
    }
    fn remove_edge(&mut self, index: usize) -> Option<Py<PyAny>> {
        self.inner.remove_edge(EdgeIndex::new(index))
    }
    fn contains_node(&self, index: usize) -> bool {
        self.inner.contains_node(NodeIndex::new(index))
    }

    #[getter]
    fn node_count(&self) -> usize {
        self.inner.node_count()
    }
    #[getter]
    fn edge_count(&self) -> usize {
        self.inner.edge_count()
    }

    fn __repr__(&self) -> String {
        format!(
            "StableDiGraph(nodes={}, edges={})",
            self.inner.node_count(),
            self.inner.edge_count()
        )
    }
    fn __len__(&self) -> usize {
        self.inner.node_count()
    }
    fn __bool__(&self) -> bool {
        self.inner.node_count() > 0
    }
    fn __contains__(&self, index: usize) -> bool {
        self.inner.contains_node(NodeIndex::new(index))
    }
}

// ════════════════════════════════════════════════════════════
// IntGraphMap
// ════════════════════════════════════════════════════════════

#[pyclass]
pub struct IntGraphMap {
    inner: PetGraphMap,
}

#[pymethods]
impl IntGraphMap {
    #[new]
    fn new() -> Self {
        IntGraphMap {
            inner: PetGraphMap::new(),
        }
    }

    fn add_node(&mut self, node: i32) {
        self.inner.add_node(node);
    }
    fn remove_node(&mut self, node: i32) -> bool {
        self.inner.remove_node(node)
    }
    fn add_edge(&mut self, u: i32, v: i32, weight: Py<PyAny>) {
        self.inner.add_edge(u, v, weight);
    }
    fn remove_edge(&mut self, u: i32, v: i32) -> Option<Py<PyAny>> {
        self.inner.remove_edge(u, v)
    }

    fn contains_node(&self, node: i32) -> bool {
        self.inner.contains_node(node)
    }
    fn contains_edge(&self, u: i32, v: i32) -> bool {
        self.inner.contains_edge(u, v)
    }

    #[getter]
    fn node_count(&self) -> usize {
        self.inner.node_count()
    }
    #[getter]
    fn edge_count(&self) -> usize {
        self.inner.edge_count()
    }

    fn neighbors(&self, node: i32) -> Vec<i32> {
        self.inner.neighbors(node).collect()
    }
    fn all_nodes(&self) -> Vec<i32> {
        self.inner.nodes().collect()
    }
    fn all_edges(&self, py: Python<'_>) -> Vec<(i32, i32, Py<PyAny>)> {
        self.inner
            .all_edges()
            .map(|(u, v, w)| (u, v, w.clone_ref(py)))
            .collect()
    }
    fn degree(&self, node: i32) -> usize {
        self.inner.neighbors(node).count()
    }

    fn __repr__(&self) -> String {
        format!(
            "IntGraphMap(nodes={}, edges={})",
            self.inner.node_count(),
            self.inner.edge_count()
        )
    }
    fn __len__(&self) -> usize {
        self.inner.node_count()
    }
    fn __bool__(&self) -> bool {
        self.inner.node_count() > 0
    }
}

// ════════════════════════════════════════════════════════════
// IntDiGraphMap
// ════════════════════════════════════════════════════════════

#[pyclass]
pub struct IntDiGraphMap {
    inner: PetDiGraphMap,
}

#[pymethods]
impl IntDiGraphMap {
    #[new]
    fn new() -> Self {
        IntDiGraphMap {
            inner: PetDiGraphMap::new(),
        }
    }

    fn add_node(&mut self, node: i32) {
        self.inner.add_node(node);
    }
    fn remove_node(&mut self, node: i32) -> bool {
        self.inner.remove_node(node)
    }
    fn add_edge(&mut self, u: i32, v: i32, weight: Py<PyAny>) {
        self.inner.add_edge(u, v, weight);
    }
    fn remove_edge(&mut self, u: i32, v: i32) -> Option<Py<PyAny>> {
        self.inner.remove_edge(u, v)
    }

    #[getter]
    fn node_count(&self) -> usize {
        self.inner.node_count()
    }
    #[getter]
    fn edge_count(&self) -> usize {
        self.inner.edge_count()
    }

    fn neighbors(&self, node: i32) -> Vec<i32> {
        self.inner.neighbors(node).collect()
    }
    fn out_degree(&self, node: i32) -> usize {
        self.inner
            .neighbors_directed(node, Direction::Outgoing)
            .count()
    }
    fn in_degree(&self, node: i32) -> usize {
        self.inner
            .neighbors_directed(node, Direction::Incoming)
            .count()
    }

    fn dijkstra(&self, py: Python<'_>, start: i32) -> PyResult<HashMap<i32, f64>> {
        if !self.inner.contains_node(start) {
            return Err(PyIndexError::new_err("Start node not in graph"));
        }
        let res = algo::dijkstra(&self.inner, start, None, |e| {
            e.weight()
                .bind(py)
                .extract::<f64>()
                .map_err(|_| PyValueError::new_err("Edge weight cannot be converted to float"))
                .unwrap_or(1.0)
        });
        Ok(res)
    }

    fn __repr__(&self) -> String {
        format!(
            "IntDiGraphMap(nodes={}, edges={})",
            self.inner.node_count(),
            self.inner.edge_count()
        )
    }
    fn __len__(&self) -> usize {
        self.inner.node_count()
    }
    fn __bool__(&self) -> bool {
        self.inner.node_count() > 0
    }
}

// ════════════════════════════════════════════════════════════
// MatrixDiGraph
// ════════════════════════════════════════════════════════════

#[pyclass]
pub struct MatrixDiGraph {
    inner: PetMatrixGraph,
}

#[pymethods]
impl MatrixDiGraph {
    #[new]
    fn new() -> Self {
        MatrixDiGraph {
            inner: PetMatrixGraph::new(),
        }
    }

    fn add_node(&mut self, weight: Py<PyAny>) -> usize {
        self.inner.add_node(weight).index()
    }

    fn add_edge(&mut self, u: usize, v: usize, weight: f64) -> PyResult<()> {
        if u >= self.inner.node_count() || v >= self.inner.node_count() {
            return Err(PyIndexError::new_err("Node index out of range"));
        }
        self.inner
            .add_edge(NodeIndex::new(u), NodeIndex::new(v), weight);
        Ok(())
    }

    fn has_edge(&self, u: usize, v: usize) -> bool {
        self.inner.has_edge(NodeIndex::new(u), NodeIndex::new(v))
    }

    fn remove_edge(&mut self, u: usize, v: usize) -> bool {
        if self.inner.has_edge(NodeIndex::new(u), NodeIndex::new(v)) {
            self.inner.remove_edge(NodeIndex::new(u), NodeIndex::new(v));
            true
        } else {
            false
        }
    }

    #[getter]
    fn node_count(&self) -> usize {
        self.inner.node_count()
    }
    #[getter]
    fn edge_count(&self) -> usize {
        self.inner.edge_count()
    }

    fn dijkstra(&self, py: Python<'_>, start: usize) -> PyResult<HashMap<usize, f64>> {
        if start >= self.inner.node_count() {
            return Err(PyIndexError::new_err("Start node index out of range"));
        }
        let res =
            py.detach(|| algo::dijkstra(&self.inner, NodeIndex::new(start), None, |e| *e.weight()));
        Ok(res.into_iter().map(|(n, d)| (n.index(), d)).collect())
    }

    fn bellman_ford(&self, py: Python<'_>, start: usize) -> PyResult<HashMap<usize, f64>> {
        if start >= self.inner.node_count() {
            return Err(PyIndexError::new_err("Start node index out of range"));
        }
        let result = py.detach(|| algo::bellman_ford(&self.inner, NodeIndex::new(start)));
        match result {
            Ok(paths) => Ok(finalize_bellman_ford(paths.distances)),
            Err(_) => Err(PyValueError::new_err("Negative cycle detected")),
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "MatrixDiGraph(nodes={}, edges={})",
            self.inner.node_count(),
            self.inner.edge_count()
        )
    }
    fn __len__(&self) -> usize {
        self.inner.node_count()
    }
    fn __bool__(&self) -> bool {
        self.inner.node_count() > 0
    }
}

// ════════════════════════════════════════════════════════════
// CsrGraph
// ════════════════════════════════════════════════════════════

#[pyclass]
pub struct CsrGraph {
    inner: PetCsrGraph,
}

#[pymethods]
impl CsrGraph {
    #[staticmethod]
    #[pyo3(signature = (node_count, edges, sorted=false))]
    fn from_edges(
        _py: Python<'_>,
        node_count: usize,
        edges: Vec<(u32, u32, f64)>,
        sorted: bool,
    ) -> Self {
        let sorted_edges = if sorted {
            edges
        } else {
            let mut e = edges;
            e.sort_by_key(|e| e.0);
            e
        };
        let mut csr = PetCsrGraph::with_nodes(node_count);
        for (u, v, w) in sorted_edges {
            csr.add_edge(u, v, w);
        }
        CsrGraph { inner: csr }
    }

    #[getter]
    fn node_count(&self) -> usize {
        self.inner.node_count()
    }
    #[getter]
    fn edge_count(&self) -> usize {
        self.inner.edge_count()
    }

    fn dijkstra(&self, py: Python<'_>, start: usize) -> PyResult<HashMap<usize, f64>> {
        if start >= self.inner.node_count() {
            return Err(PyIndexError::new_err("Start node index out of range"));
        }
        let res = py.detach(|| algo::dijkstra(&self.inner, start as u32, None, |e| *e.weight()));
        Ok(res.into_iter().map(|(n, d)| (n as usize, d)).collect())
    }

    fn bellman_ford(&self, py: Python<'_>, start: usize) -> PyResult<HashMap<usize, f64>> {
        if start >= self.inner.node_count() {
            return Err(PyIndexError::new_err("Start node index out of range"));
        }
        let result = py.detach(|| algo::bellman_ford(&self.inner, start as u32));
        match result {
            Ok(paths) => Ok(finalize_bellman_ford(paths.distances)),
            Err(_) => Err(PyValueError::new_err("Negative cycle detected")),
        }
    }

    fn floyd_warshall(&self, py: Python<'_>) -> PyResult<HashMap<usize, HashMap<usize, f64>>> {
        let res = py.detach(|| algo::floyd_warshall(&self.inner, |e| *e.weight()));
        match res {
            Ok(map) => Ok(finalize_floyd_warshall(
                map.into_iter()
                    .map(|((u, v), w)| ((u as usize, v as usize), w))
                    .collect(),
            )),
            Err(_) => Err(PyValueError::new_err("Negative cycle detected")),
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "CsrGraph(nodes={}, edges={})",
            self.inner.node_count(),
            self.inner.edge_count()
        )
    }
    fn __len__(&self) -> usize {
        self.inner.node_count()
    }
    fn __bool__(&self) -> bool {
        self.inner.node_count() > 0
    }
}

// ════════════════════════════════════════════════════════════
// Module-level functions
// ════════════════════════════════════════════════════════════

#[pyfunction]
fn is_isomorphic(py: Python<'_>, g1: &DiGraph, g2: &DiGraph) -> bool {
    py.detach(|| algo::is_isomorphic(&g1.inner, &g2.inner))
}

// ════════════════════════════════════════════════════════════
// Module registration
// ════════════════════════════════════════════════════════════

#[pymodule]
fn _pypetgraph(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<DiGraph>()?;
    m.add_class::<FastDiGraph>()?;
    m.add_class::<UnGraph>()?;
    m.add_class::<StableDiGraph>()?;
    m.add_class::<IntGraphMap>()?;
    m.add_class::<IntDiGraphMap>()?;
    m.add_class::<MatrixDiGraph>()?;
    m.add_class::<CsrGraph>()?;
    m.add_class::<UnionFind>()?;
    m.add_function(wrap_pyfunction!(is_isomorphic, m)?)?;
    Ok(())
}
