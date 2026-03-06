# 🦀 pypetgraph API Reference

Welcome to the **pypetgraph** API reference. This library provides high-performance Rust-backed graph data structures and algorithms for Python, powered by [petgraph](https://github.com/petgraph/petgraph).

---

## 🗺️ Table of Contents

- [**DiGraph**](#digraph) - Directed Adjacency List
- [**UnGraph**](#ungraph) - Undirected Adjacency List
- [**FastDiGraph**](#fastdigraph) - Numeric-optimized Directed Graph
- [**StableDiGraph**](#stabledigraph) - Removal-stable Adjacency List
- [**IntGraphMap**](#intgraphmap) / [**IntDiGraphMap**](#intdigraphmap) - Hash-based Graphs
- [**MatrixDiGraph**](#matrixdigraph) - Dense Matrix Graph
- [**CsrGraph**](#csrgraph) - Compressed Sparse Row
- [**UnionFind**](#unionfind) - Disjoint Set Union
- [**Global Functions**](#global-functions) - Utility methods

---

## <a name="digraph"></a> 🔹 DiGraph

The standard directed graph implementation. Nodes and edges can store any Python object.

### 🏗️ Construction & Mutation

#### `__init__(nodes=0, edges=0)`
Creates an empty graph with pre-allocated capacity.
- **Parameters**:
    - `nodes` (*int*): Initial node capacity.
    - `edges` (*int*): Initial edge capacity.
- **Returns**: `DiGraph` instance.

#### `from_edges(edges, node_count=None)` *(static)*
Constructs a graph from an edge list.
- **Parameters**:
    - `edges` (*list[tuple]*): A list of `(source_index, target_index, weight)`.
    - `node_count` (*int | None*): Total number of nodes. If `None`, inferred from `edges`.
- **Returns**: `DiGraph` instance.

#### `add_node(weight)`
Adds a node to the graph.
- **Parameters**:
    - `weight` (*Any*): The data to store in the node.
- **Returns**: `int` - The index of the new node.

#### `remove_node(index)`
Removes a node and all its connected edges.
- **Parameters**:
    - `index` (*int*): The index of the node to remove.
- **Returns**: `Any | None` - The weight of the removed node, or `None` if not found.
- **⚠️ Warning**: This method uses "swap-remove". The last node in the internal array will be moved to the index of the deleted node to keep the storage compact. **This changes the index of the last node.**

#### `add_edge(u, v, weight)`
Adds a directed edge from `u` to `v`.
- **Parameters**:
    - `u` (*int*): Source node index.
    - `v` (*int*): Target node index.
    - `weight` (*Any*): Edge data.
- **Returns**: `int` - The index of the new edge.
- **Exceptions**: `IndexError` if `u` or `v` do not exist.

#### `update_edge(u, v, weight)`
Updates the weight of an existing edge between `u` and `v`, or adds a new one.
- **Returns**: `int` - The edge index.

#### `remove_edge(index)`
Removes an edge by its index.
- **Returns**: `Any | None` - The weight of the removed edge.

#### `clear()` / `clear_edges()`
Clears the entire graph or just the edges.

#### `reverse()`
Inverts the direction of every edge in the graph in-place.

---

### 📊 Properties & Queries

#### `node_count` / `edge_count` *(property)*
Returns the number of nodes or edges in the graph as an `int`.

#### `node_weight(index)` / `edge_weight(index)`
Returns the data stored at the given index. Returns `None` if index is invalid.

#### `neighbors(index)`
- **Returns**: `list[int]` - Indices of nodes reachable from `index`.

#### `out_degree(index)` / `in_degree(index)`
- **Returns**: `int` - Count of outgoing or incoming edges for the node.

#### `node_indices()` / `edge_indices()`
- **Returns**: `list[int]` - All valid indices currently in the graph.

---

### 🚀 Algorithms (Synchronous & Asynchronous)

All algorithm methods have an `_async` version (e.g., `dijkstra_async`) that runs in a thread pool to avoid blocking the GIL.

#### `dijkstra(start) -> dict[int, float]`
Computes the shortest path from `start` to all reachable nodes using Dijkstra's algorithm.
- **Parameters**:
    - `start` (*int*): Starting node index.
- **Returns**: `dict` mapping node index to its distance from `start`.
- **Note**: Edge weights must be convertible to `float`. Negative weights are not supported.

#### `floyd_warshall() -> dict[int, dict[int, float]]`
Computes shortest paths between all pairs of nodes.
- **Returns**: A nested dictionary `{source: {target: distance}}`. 
- **Note**: Unreachable pairs are omitted from the result.

#### `k_shortest_path(start, goal, k, weight_fn=None) -> dict[int, float]`
Computes the cost of the **k-th** shortest path.
- **Parameters**:
    - `start` (*int*): Source node.
    - `goal` (*int*): Target node.
    - `k` (*int*): The sequence number of the path (e.g., 2 for second-shortest).
    - `weight_fn` (*Callable | None*): Optional function `(u, v, weight) -> float` to determine edge costs.
- **Returns**: `dict` mapping target nodes to the cost of their k-th shortest path from `start`.

#### `astar(start, goal, heuristic_fn) -> tuple[float, list[int]] | None`
A* search algorithm.
- **Parameters**:
    - `heuristic_fn`: A function taking a node index and returning a `float` estimate to the goal.
- **Returns**: `(total_cost, path_list)` or `None` if no path exists.

#### `toposort()`
- **Returns**: `list[int]` - A valid topological ordering.
- **Exceptions**: `ValueError` if the graph contains a cycle.

#### `tarjan_scc()` / `kosaraju_scc()`
- **Returns**: `list[list[int]]` - A list of strongly connected components.

#### `page_rank(damping_factor=0.85, iterations=100)`
- **Returns**: `list[float]` - PageRank scores for all nodes.

---

## <a name="ungraph"></a> 🔸 UnGraph

Undirected adjacency list. Most methods are identical to `DiGraph`.

| Method | Parameters | Description |
| :--- | :--- | :--- |
| `degree(idx)` | `idx: int` | Returns total neighbors (incident edges). |
| `connected_components()`| None | Returns the number of connected components. |
| `is_bipartite(start)` | `start: int`| Checks if the graph is 2-colorable. |

---

## <a name="fastdigraph"></a> ⚡ FastDiGraph

A specialized `DiGraph` where edge weights are strictly **`f64`**.

- **Why use it?** It is significantly faster for algorithms because it avoids Python object overhead when accessing weights.
- **Unique Method**: 
    - `bellman_ford(start) -> dict[int, float]`: Supports negative weights and detects negative cycles.

---

## <a name="stabledigraph"></a> 🛡️ StableDiGraph

Similar to `DiGraph`, but **guarantees stable indices**.
- When a node is removed, other node indices **do not change**.
- Deleted indices are not reused immediately.
- Use `contains_node(index)` to check if an index is valid.

---

## <a name="intgraphmap"></a> 🗺️ IntGraphMap / IntDiGraphMap

Graphs where nodes are identified by **arbitrary `i32` integers** (keys) rather than zero-based indices.

- `add_node(key: int)`: Adds node with key.
- `neighbors(key: int)`: Returns list of neighbor keys.
- **Note**: Extremely efficient for sparse graphs with non-sequential integer IDs.

---

## <a name="matrixdigraph"></a> ⬛ MatrixDiGraph

Uses an **Adjacency Matrix** for storage.
- **Best for**: Dense graphs where most possible edges exist.
- **Edge weights**: Must be `f64`.
- **Complexity**: `has_edge(u, v)` is **O(1)**.

---

## <a name="csrgraph"></a> 📉 CsrGraph

Compressed Sparse Row format.
- **Static**: You cannot add or remove nodes/edges after creation.
- **Memory**: Most efficient for very large graphs (millions of nodes).
- **Construction**: `CsrGraph.from_edges(node_count, edges, sorted=False)`.

---

## <a name="unionfind"></a> 🔗 UnionFind

Disjoint Set Union (DSU) implementation.

- `find(i)`: Returns representative of element `i`.
- `union(i, j)`: Merges two sets. Returns `True` if they were separate.
- `equiv(i, j)`: Checks if `i` and `j` are in the same set.

---

## <a name="global-functions"></a> 🌍 Global Functions

#### `is_isomorphic(g1, g2) -> bool`
Returns `True` if two `DiGraph` instances have the same structure. 
- **⚠️ Important**: Weights are ignored. Only the topology is checked.

---

*Generated for pypetgraph v0.1.0*
