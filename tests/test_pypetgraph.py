"""Comprehensive tests for pypetgraph — all graph types, algorithms, edge cases."""
import pytest

from pypetgraph import (
    CsrGraph,
    DiGraph,
    FastDiGraph,
    IntDiGraphMap,
    IntGraphMap,
    MatrixDiGraph,
    StableDiGraph,
    UnGraph,
    UnionFind,
    is_isomorphic,
)


# ════════════════════════════════════════════════════════════
# DiGraph — construction
# ════════════════════════════════════════════════════════════


class TestDiGraphConstruction:
    def test_empty(self):
        g = DiGraph()
        assert g.node_count == 0
        assert g.edge_count == 0

    def test_with_capacity(self):
        g = DiGraph(100, 200)
        assert g.node_count == 0
        assert g.edge_count == 0

    def test_from_edges_auto_nodes(self):
        g = DiGraph.from_edges([(0, 1, 1.0), (1, 2, 2.0)])
        assert g.node_count == 3
        assert g.edge_count == 2

    def test_from_edges_explicit_nodes(self):
        g = DiGraph.from_edges([(0, 1, 1.0)], node_count=5)
        assert g.node_count == 5
        assert g.edge_count == 1

    def test_from_edges_empty(self):
        g = DiGraph.from_edges([])
        assert g.node_count == 0
        assert g.edge_count == 0


# ════════════════════════════════════════════════════════════
# DiGraph — mutations
# ════════════════════════════════════════════════════════════


class TestDiGraphMutation:
    def test_add_node(self):
        g = DiGraph()
        n0 = g.add_node("A")
        n1 = g.add_node("B")
        assert n0 == 0
        assert n1 == 1
        assert g.node_count == 2

    def test_add_edge(self):
        g = DiGraph()
        n0 = g.add_node("A")
        n1 = g.add_node("B")
        e = g.add_edge(n0, n1, 1.0)
        assert e == 0
        assert g.edge_count == 1

    def test_add_edge_invalid_node(self):
        g = DiGraph()
        g.add_node("A")
        with pytest.raises(IndexError):
            g.add_edge(0, 99, 1.0)
        with pytest.raises(IndexError):
            g.add_edge(99, 0, 1.0)

    def test_update_edge(self):
        g = DiGraph()
        n0 = g.add_node("A")
        n1 = g.add_node("B")
        e0 = g.add_edge(n0, n1, 1.0)
        g.update_edge(n0, n1, 2.0)
        assert g.edge_weight(e0) == 2.0

    def test_remove_edge(self):
        g = DiGraph()
        n0 = g.add_node("A")
        n1 = g.add_node("B")
        e0 = g.add_edge(n0, n1, 42)
        w = g.remove_edge(e0)
        assert w == 42
        assert g.edge_count == 0

    def test_remove_edge_nonexistent(self):
        g = DiGraph()
        g.add_node("A")
        assert g.remove_edge(99) is None

    def test_remove_node_swap(self):
        """petgraph's Graph swaps the removed node with the last node."""
        g = DiGraph()
        g.add_node("A")  # 0
        g.add_node("B")  # 1
        g.add_node("C")  # 2
        g.remove_node(0)  # A removed, C -> index 0
        assert g.node_count == 2
        assert g.node_weight(0) == "C"  # C took index 0
        assert g.node_weight(1) == "B"

    def test_remove_node_with_edges(self):
        g = DiGraph()
        n0 = g.add_node("A")
        n1 = g.add_node("B")
        g.add_edge(n0, n1, 1.0)
        g.remove_node(n0)
        assert g.edge_count == 0
        assert g.node_count == 1

    def test_remove_node_nonexistent(self):
        g = DiGraph()
        assert g.remove_node(99) is None

    def test_clear(self):
        g = DiGraph()
        g.add_node("A")
        g.add_node("B")
        g.add_edge(0, 1, 1.0)
        g.clear()
        assert g.node_count == 0
        assert g.edge_count == 0

    def test_clear_edges(self):
        g = DiGraph()
        g.add_node("A")
        g.add_node("B")
        g.add_edge(0, 1, 1.0)
        g.clear_edges()
        assert g.edge_count == 0
        assert g.node_count == 2

    def test_reverse(self):
        g = DiGraph()
        n0 = g.add_node("A")
        n1 = g.add_node("B")
        g.add_edge(n0, n1, 1.0)
        assert g.find_edge(n0, n1) is not None
        assert g.find_edge(n1, n0) is None
        g.reverse()
        assert g.find_edge(n0, n1) is None
        assert g.find_edge(n1, n0) is not None


# ════════════════════════════════════════════════════════════
# DiGraph — properties & queries
# ════════════════════════════════════════════════════════════


class TestDiGraphQueries:
    def test_is_directed(self):
        assert DiGraph().is_directed is True

    def test_node_weight(self):
        g = DiGraph()
        g.add_node({"key": "value"})
        assert g.node_weight(0) == {"key": "value"}
        assert g.node_weight(99) is None

    def test_edge_weight(self):
        g = DiGraph()
        g.add_node("A")
        g.add_node("B")
        g.add_edge(0, 1, [1, 2, 3])
        assert g.edge_weight(0) == [1, 2, 3]
        assert g.edge_weight(99) is None

    def test_find_edge(self):
        g = DiGraph()
        g.add_node("A")
        g.add_node("B")
        g.add_edge(0, 1, 1.0)
        assert g.find_edge(0, 1) is not None
        assert g.find_edge(1, 0) is None
        assert g.find_edge(0, 99) is None

    def test_neighbors(self):
        g = DiGraph()
        n0 = g.add_node("A")
        n1 = g.add_node("B")
        n2 = g.add_node("C")
        g.add_edge(n0, n1, 1.0)
        g.add_edge(n0, n2, 1.0)
        assert set(g.neighbors(n0)) == {n1, n2}
        assert g.neighbors(n2) == []

    def test_degree(self):
        g = DiGraph()
        n0 = g.add_node(0)
        n1 = g.add_node(1)
        n2 = g.add_node(2)
        g.add_edge(n0, n1, 1.0)
        g.add_edge(n2, n0, 1.0)
        assert g.out_degree(n0) == 1
        assert g.in_degree(n0) == 1
        assert g.out_degree(n2) == 1
        assert g.in_degree(n2) == 0

    def test_node_indices(self):
        g = DiGraph()
        g.add_node("A")
        g.add_node("B")
        g.add_node("C")
        assert g.node_indices() == [0, 1, 2]

    def test_edge_indices(self):
        g = DiGraph()
        g.add_node("A")
        g.add_node("B")
        g.add_edge(0, 1, 1.0)
        g.add_edge(1, 0, 2.0)
        assert g.edge_indices() == [0, 1]


# ════════════════════════════════════════════════════════════
# DiGraph — algorithms
# ════════════════════════════════════════════════════════════


class TestDiGraphAlgorithms:
    def test_bfs_linear(self):
        g = DiGraph()
        for i in range(5):
            g.add_node(i)
        for i in range(4):
            g.add_edge(i, i + 1, 1.0)
        result = g.bfs(0)
        assert result == [0, 1, 2, 3, 4]

    def test_bfs_disconnected(self):
        g = DiGraph()
        g.add_node("A")
        g.add_node("B")  # no edges
        assert g.bfs(0) == [0]  # only reachable from start

    def test_dfs_linear(self):
        g = DiGraph()
        for i in range(5):
            g.add_node(i)
        for i in range(4):
            g.add_edge(i, i + 1, 1.0)
        result = g.dfs(0)
        assert result == [0, 1, 2, 3, 4]

    def test_is_cyclic_dag(self):
        g = DiGraph()
        g.add_node(0)
        g.add_node(1)
        g.add_node(2)
        g.add_edge(0, 1, 1.0)
        g.add_edge(1, 2, 1.0)
        assert g.is_cyclic() is False

    def test_is_cyclic_with_cycle(self):
        g = DiGraph()
        g.add_node(0)
        g.add_node(1)
        g.add_edge(0, 1, 1.0)
        g.add_edge(1, 0, 1.0)
        assert g.is_cyclic() is True

    def test_is_cyclic_self_loop(self):
        g = DiGraph()
        n0 = g.add_node(0)
        g.add_edge(n0, n0, 1.0)
        assert g.is_cyclic() is True

    def test_toposort(self):
        g = DiGraph()
        g.add_node("A")
        g.add_node("B")
        g.add_node("C")
        g.add_edge(0, 1, 1.0)
        g.add_edge(1, 2, 1.0)
        order = g.toposort()
        assert order.index(0) < order.index(1) < order.index(2)

    def test_toposort_cyclic_raises(self):
        g = DiGraph()
        g.add_node(0)
        g.add_node(1)
        g.add_edge(0, 1, 1.0)
        g.add_edge(1, 0, 1.0)
        with pytest.raises(ValueError, match="cycle"):
            g.toposort()

    def test_toposort_empty(self):
        assert DiGraph().toposort() == []

    def test_dijkstra_basic(self):
        g = DiGraph()
        g.add_node(0)
        g.add_node(1)
        g.add_node(2)
        g.add_edge(0, 1, 1.0)
        g.add_edge(1, 2, 2.0)
        g.add_edge(0, 2, 10.0)
        dists = g.dijkstra(0)
        assert dists[0] == 0.0
        assert dists[1] == 1.0
        assert dists[2] == 3.0

    def test_dijkstra_invalid_start(self):
        g = DiGraph()
        g.add_node(0)
        with pytest.raises(IndexError):
            g.dijkstra(99)

    def test_dijkstra_non_float_weight_raises(self):
        g = DiGraph()
        g.add_node(0)
        g.add_node(1)
        g.add_edge(0, 1, "not_a_number")
        with pytest.raises(ValueError, match="cannot be converted"):
            g.dijkstra(0)

    def test_dijkstra_single_node(self):
        g = DiGraph()
        g.add_node(0)
        assert g.dijkstra(0) == {0: 0.0}

    def test_astar(self):
        g = DiGraph()
        g.add_node(0)
        g.add_node(1)
        g.add_node(2)
        g.add_edge(0, 1, 1.0)
        g.add_edge(1, 2, 2.0)
        g.add_edge(0, 2, 10.0)
        cost, path = g.astar(0, 2, lambda n: 0)
        assert cost == 3.0
        assert path == [0, 1, 2]

    def test_astar_no_path(self):
        g = DiGraph()
        g.add_node(0)
        g.add_node(1)
        assert g.astar(0, 1, lambda n: 0) is None

    def test_astar_invalid_node(self):
        g = DiGraph()
        g.add_node(0)
        with pytest.raises(IndexError):
            g.astar(0, 99, lambda n: 0)

    def test_tarjan_scc_single_component(self):
        g = DiGraph()
        for i in range(3):
            g.add_node(i)
        g.add_edge(0, 1, 1.0)
        g.add_edge(1, 2, 1.0)
        g.add_edge(2, 0, 1.0)
        sccs = g.tarjan_scc()
        assert len(sccs) == 1
        assert set(sccs[0]) == {0, 1, 2}

    def test_tarjan_scc_multiple_components(self):
        g = DiGraph()
        for i in range(4):
            g.add_node(i)
        g.add_edge(0, 1, 1.0)
        g.add_edge(1, 0, 1.0)
        g.add_edge(2, 3, 1.0)
        g.add_edge(3, 2, 1.0)
        sccs = g.tarjan_scc()
        assert len(sccs) == 2

    def test_tarjan_scc_empty(self):
        assert DiGraph().tarjan_scc() == []

    def test_kosaraju_scc(self):
        g = DiGraph()
        for i in range(3):
            g.add_node(i)
        g.add_edge(0, 1, 1.0)
        g.add_edge(1, 2, 1.0)
        g.add_edge(2, 0, 1.0)
        sccs = g.kosaraju_scc()
        assert len(sccs) == 1
        assert set(sccs[0]) == {0, 1, 2}

    def test_all_simple_paths(self):
        g = DiGraph()
        for i in range(3):
            g.add_node(i)
        g.add_edge(0, 1, 1.0)
        g.add_edge(1, 2, 1.0)
        g.add_edge(0, 2, 1.0)
        paths = g.all_simple_paths(0, 2, 0, None)
        assert len(paths) == 2
        assert [0, 2] in paths
        assert [0, 1, 2] in paths

    def test_all_simple_paths_with_min(self):
        g = DiGraph()
        for i in range(3):
            g.add_node(i)
        g.add_edge(0, 1, 1.0)
        g.add_edge(1, 2, 1.0)
        g.add_edge(0, 2, 1.0)
        paths = g.all_simple_paths(0, 2, 1, None)
        assert len(paths) == 1
        assert [0, 1, 2] in paths

    def test_all_simple_paths_invalid_node(self):
        g = DiGraph()
        g.add_node(0)
        with pytest.raises(IndexError):
            g.all_simple_paths(0, 99, 0, None)

    def test_has_path_connecting(self):
        g = DiGraph()
        g.add_node(0)
        g.add_node(1)
        g.add_node(2)
        g.add_edge(0, 1, 1.0)
        assert g.has_path_connecting(0, 1) is True
        assert g.has_path_connecting(0, 2) is False
        assert g.has_path_connecting(0, 0) is True  # self

    def test_page_rank(self):
        g = DiGraph()
        g.add_node(0)
        g.add_node(1)
        g.add_edge(0, 1, 1.0)
        g.add_edge(1, 0, 1.0)
        ranks = g.page_rank(0.85, 50)
        assert len(ranks) == 2
        assert all(r > 0 for r in ranks)
        assert abs(sum(ranks) - 1.0) < 0.01

    def test_page_rank_empty(self):
        assert DiGraph().page_rank() == []

    def test_page_rank_custom_params(self):
        g = DiGraph()
        g.add_node(0)
        g.add_node(1)
        g.add_edge(0, 1, 1.0)
        ranks = g.page_rank(damping_factor=0.5, iterations=10)
        assert len(ranks) == 2


# ════════════════════════════════════════════════════════════
# DiGraph — output & protocols
# ════════════════════════════════════════════════════════════


class TestDiGraphProtocols:
    def test_to_dot_structure(self):
        g = DiGraph()
        g.add_node("hello")
        g.add_node("world")
        g.add_edge(0, 1, 42)
        dot = g.to_dot()
        assert dot.startswith("digraph {")
        assert "hello" in dot
        assert "world" in dot
        assert "42" in dot
        assert "->" in dot

    def test_to_dot_empty(self):
        dot = DiGraph().to_dot()
        assert "digraph" in dot

    def test_repr(self):
        g = DiGraph()
        assert repr(g) == "DiGraph(nodes=0, edges=0)"
        g.add_node("A")
        g.add_node("B")
        g.add_edge(0, 1, 1.0)
        assert repr(g) == "DiGraph(nodes=2, edges=1)"

    def test_len(self):
        g = DiGraph()
        assert len(g) == 0
        g.add_node("A")
        assert len(g) == 1

    def test_bool(self):
        g = DiGraph()
        assert not g
        g.add_node("A")
        assert g

    def test_contains(self):
        g = DiGraph()
        n = g.add_node("A")
        assert n in g
        assert 99 not in g

    def test_contains_after_remove(self):
        g = DiGraph()
        g.add_node("A")
        g.add_node("B")
        g.remove_node(0)
        assert 0 in g  # B moved to index 0
        assert 1 not in g  # index 1 no longer valid


# ════════════════════════════════════════════════════════════
# UnGraph
# ════════════════════════════════════════════════════════════


class TestUnGraph:
    def test_basics(self):
        g = UnGraph()
        n0 = g.add_node("A")
        n1 = g.add_node("B")
        g.add_edge(n0, n1, 1.0)
        assert g.node_count == 2
        assert g.edge_count == 1
        assert g.is_directed is False

    def test_with_capacity(self):
        g = UnGraph(50, 100)
        assert g.node_count == 0

    def test_degree(self):
        g = UnGraph()
        n0 = g.add_node(0)
        n1 = g.add_node(1)
        n2 = g.add_node(2)
        g.add_edge(n0, n1, 1.0)
        g.add_edge(n0, n2, 1.0)
        assert g.degree(n0) == 2
        assert g.degree(n1) == 1

    def test_connected_components(self):
        g = UnGraph()
        g.add_node(0)
        g.add_node(1)
        g.add_node(2)
        g.add_edge(0, 1, 1.0)
        assert g.connected_components() == 2
        g.add_edge(1, 2, 1.0)
        assert g.connected_components() == 1

    def test_remove_node(self):
        g = UnGraph()
        g.add_node("A")
        g.add_node("B")
        g.remove_node(0)
        assert g.node_count == 1

    def test_add_edge_invalid(self):
        g = UnGraph()
        g.add_node("A")
        with pytest.raises(IndexError):
            g.add_edge(0, 99, 1.0)

    def test_clear(self):
        g = UnGraph()
        g.add_node("A")
        g.add_node("B")
        g.add_edge(0, 1, 1.0)
        g.clear()
        assert g.node_count == 0

    def test_bfs(self):
        g = UnGraph()
        for i in range(4):
            g.add_node(i)
        g.add_edge(0, 1, 1.0)
        g.add_edge(1, 2, 1.0)
        g.add_edge(2, 3, 1.0)
        assert set(g.bfs(0)) == {0, 1, 2, 3}

    def test_dfs(self):
        g = UnGraph()
        for i in range(3):
            g.add_node(i)
        g.add_edge(0, 1, 1.0)
        g.add_edge(1, 2, 1.0)
        assert set(g.dfs(0)) == {0, 1, 2}

    def test_has_path_connecting(self):
        g = UnGraph()
        g.add_node(0)
        g.add_node(1)
        g.add_node(2)
        g.add_edge(0, 1, 1.0)
        assert g.has_path_connecting(0, 1) is True
        assert g.has_path_connecting(0, 2) is False

    def test_is_bipartite(self):
        # K2,2 is bipartite
        g = UnGraph()
        for i in range(4):
            g.add_node(i)
        g.add_edge(0, 2, 1.0)
        g.add_edge(0, 3, 1.0)
        g.add_edge(1, 2, 1.0)
        g.add_edge(1, 3, 1.0)
        assert g.is_bipartite(0) is True

    def test_is_not_bipartite(self):
        # triangle is NOT bipartite
        g = UnGraph()
        for i in range(3):
            g.add_node(i)
        g.add_edge(0, 1, 1.0)
        g.add_edge(1, 2, 1.0)
        g.add_edge(2, 0, 1.0)
        assert g.is_bipartite(0) is False

    def test_to_dot(self):
        g = UnGraph()
        g.add_node("X")
        g.add_node("Y")
        g.add_edge(0, 1, 1.0)
        dot = g.to_dot()
        assert "graph {" in dot
        assert "--" in dot

    def test_protocols(self):
        g = UnGraph()
        assert repr(g) == "UnGraph(nodes=0, edges=0)"
        assert len(g) == 0
        assert not g
        g.add_node("A")
        assert len(g) == 1
        assert g


# ════════════════════════════════════════════════════════════
# FastDiGraph
# ════════════════════════════════════════════════════════════


class TestFastDiGraph:
    def test_basics(self):
        g = FastDiGraph()
        n0 = g.add_node("A")
        n1 = g.add_node("B")
        g.add_edge(n0, n1, 1.5)
        assert g.node_count == 2
        assert g.edge_count == 1

    def test_with_capacity(self):
        g = FastDiGraph(50, 100)
        assert g.node_count == 0

    def test_node_weight(self):
        g = FastDiGraph()
        g.add_node("hello")
        assert g.node_weight(0) == "hello"
        assert g.node_weight(99) is None

    def test_add_edge_invalid(self):
        g = FastDiGraph()
        g.add_node("A")
        with pytest.raises(IndexError):
            g.add_edge(0, 99, 1.0)

    def test_dijkstra(self):
        g = FastDiGraph()
        g.add_node(0)
        g.add_node(1)
        g.add_node(2)
        g.add_edge(0, 1, 1.0)
        g.add_edge(1, 2, 2.0)
        dists = g.dijkstra(0)
        assert dists[2] == 3.0

    def test_dijkstra_invalid(self):
        g = FastDiGraph()
        g.add_node(0)
        with pytest.raises(IndexError):
            g.dijkstra(99)

    def test_astar(self):
        g = FastDiGraph()
        g.add_node(0)
        g.add_node(1)
        g.add_node(2)
        g.add_edge(0, 1, 1.0)
        g.add_edge(1, 2, 2.0)
        g.add_edge(0, 2, 10.0)
        cost, path = g.astar(0, 2, lambda n: 0)
        assert cost == 3.0
        assert path == [0, 1, 2]

    def test_astar_invalid(self):
        g = FastDiGraph()
        g.add_node(0)
        with pytest.raises(IndexError):
            g.astar(0, 99, lambda n: 0)

    def test_bellman_ford(self):
        g = FastDiGraph()
        g.add_node(0)
        g.add_node(1)
        g.add_node(2)
        g.add_edge(0, 1, 1.0)
        g.add_edge(1, 2, 2.0)
        g.add_edge(0, 2, 10.0)
        dists = g.bellman_ford(0)
        assert dists[2] == 3.0

    def test_bellman_ford_invalid(self):
        g = FastDiGraph()
        g.add_node(0)
        with pytest.raises(IndexError):
            g.bellman_ford(99)

    def test_is_cyclic(self):
        g = FastDiGraph()
        g.add_node(0)
        g.add_node(1)
        g.add_edge(0, 1, 1.0)
        assert g.is_cyclic() is False
        g.add_edge(1, 0, 1.0)
        assert g.is_cyclic() is True

    def test_toposort(self):
        g = FastDiGraph()
        g.add_node(0)
        g.add_node(1)
        g.add_edge(0, 1, 1.0)
        order = g.toposort()
        assert order.index(0) < order.index(1)

    def test_toposort_cyclic_raises(self):
        g = FastDiGraph()
        g.add_node(0)
        g.add_node(1)
        g.add_edge(0, 1, 1.0)
        g.add_edge(1, 0, 1.0)
        with pytest.raises(ValueError):
            g.toposort()

    def test_tarjan_scc(self):
        g = FastDiGraph()
        for i in range(3):
            g.add_node(i)
        g.add_edge(0, 1, 1.0)
        g.add_edge(1, 2, 1.0)
        g.add_edge(2, 0, 1.0)
        sccs = g.tarjan_scc()
        assert len(sccs) == 1

    def test_has_path_connecting(self):
        g = FastDiGraph()
        g.add_node(0)
        g.add_node(1)
        g.add_edge(0, 1, 1.0)
        assert g.has_path_connecting(0, 1) is True
        assert g.has_path_connecting(1, 0) is False

    def test_page_rank(self):
        g = FastDiGraph()
        g.add_node(0)
        g.add_node(1)
        g.add_edge(0, 1, 1.0)
        ranks = g.page_rank(0.85, 10)
        assert len(ranks) == 2

    def test_bfs_dfs(self):
        g = FastDiGraph()
        for i in range(3):
            g.add_node(i)
        g.add_edge(0, 1, 1.0)
        g.add_edge(1, 2, 1.0)
        assert set(g.bfs(0)) == {0, 1, 2}
        assert set(g.dfs(0)) == {0, 1, 2}

    def test_all_simple_paths(self):
        g = FastDiGraph()
        for i in range(3):
            g.add_node(i)
        g.add_edge(0, 1, 1.0)
        g.add_edge(1, 2, 1.0)
        g.add_edge(0, 2, 1.0)
        paths = g.all_simple_paths(0, 2)
        assert len(paths) == 2

    def test_all_simple_paths_invalid(self):
        g = FastDiGraph()
        g.add_node(0)
        with pytest.raises(IndexError):
            g.all_simple_paths(0, 99)

    def test_to_dot(self):
        g = FastDiGraph()
        g.add_node("start")
        g.add_node("end")
        g.add_edge(0, 1, 3.14)
        dot = g.to_dot()
        assert "digraph" in dot
        assert "3.14" in dot

    def test_protocols(self):
        g = FastDiGraph()
        assert repr(g) == "FastDiGraph(nodes=0, edges=0)"
        assert not g
        g.add_node("A")
        assert g
        assert len(g) == 1


# ════════════════════════════════════════════════════════════
# StableDiGraph
# ════════════════════════════════════════════════════════════


class TestStableDiGraph:
    def test_stable_indices(self):
        g = StableDiGraph()
        n0 = g.add_node("A")
        n1 = g.add_node("B")
        n2 = g.add_node("C")
        g.remove_node(n1)
        assert g.node_count == 2
        assert g.contains_node(n0)
        assert not g.contains_node(n1)  # removed
        assert g.contains_node(n2)  # stable!

    def test_add_edge_to_removed_node(self):
        g = StableDiGraph()
        n0 = g.add_node("A")
        n1 = g.add_node("B")
        g.remove_node(n1)
        with pytest.raises(IndexError):
            g.add_edge(n0, n1, 1.0)

    def test_remove_edge(self):
        g = StableDiGraph()
        g.add_node("A")
        g.add_node("B")
        e = g.add_edge(0, 1, "data")
        assert g.edge_count == 1
        w = g.remove_edge(e)
        assert w == "data"
        assert g.edge_count == 0

    def test_remove_edge_nonexistent(self):
        g = StableDiGraph()
        assert g.remove_edge(99) is None

    def test_protocols(self):
        g = StableDiGraph()
        assert repr(g) == "StableDiGraph(nodes=0, edges=0)"
        assert not g
        n = g.add_node("A")
        assert g
        assert n in g
        assert 99 not in g
        assert len(g) == 1


# ════════════════════════════════════════════════════════════
# IntGraphMap
# ════════════════════════════════════════════════════════════


class TestIntGraphMap:
    def test_basics(self):
        g = IntGraphMap()
        g.add_node(42)
        g.add_node(10)
        g.add_edge(42, 10, "edge")
        assert g.node_count == 2
        assert g.edge_count == 1

    def test_contains(self):
        g = IntGraphMap()
        g.add_node(5)
        assert g.contains_node(5)
        assert not g.contains_node(99)

    def test_contains_edge(self):
        g = IntGraphMap()
        g.add_node(1)
        g.add_node(2)
        g.add_edge(1, 2, "w")
        assert g.contains_edge(1, 2)
        assert g.contains_edge(2, 1)  # undirected!
        assert not g.contains_edge(1, 99)

    def test_neighbors(self):
        g = IntGraphMap()
        g.add_node(1)
        g.add_node(2)
        g.add_node(3)
        g.add_edge(1, 2, "a")
        g.add_edge(1, 3, "b")
        assert set(g.neighbors(1)) == {2, 3}

    def test_degree(self):
        g = IntGraphMap()
        g.add_node(1)
        g.add_node(2)
        g.add_node(3)
        g.add_edge(1, 2, "a")
        g.add_edge(1, 3, "b")
        assert g.degree(1) == 2
        assert g.degree(2) == 1

    def test_all_nodes(self):
        g = IntGraphMap()
        g.add_node(10)
        g.add_node(20)
        assert set(g.all_nodes()) == {10, 20}

    def test_all_edges(self):
        g = IntGraphMap()
        g.add_node(1)
        g.add_node(2)
        g.add_edge(1, 2, "w")
        edges = g.all_edges()
        assert len(edges) == 1
        u, v, w = edges[0]
        assert {u, v} == {1, 2}
        assert w == "w"

    def test_remove_node(self):
        g = IntGraphMap()
        g.add_node(1)
        g.add_node(2)
        g.add_edge(1, 2, "w")
        assert g.remove_node(1) is True
        assert g.remove_node(1) is False  # already removed
        assert g.node_count == 1
        assert g.edge_count == 0

    def test_remove_edge(self):
        g = IntGraphMap()
        g.add_node(1)
        g.add_node(2)
        g.add_edge(1, 2, "w")
        w = g.remove_edge(1, 2)
        assert w == "w"
        assert g.edge_count == 0
        assert g.remove_edge(1, 2) is None  # already removed

    def test_protocols(self):
        g = IntGraphMap()
        assert repr(g) == "IntGraphMap(nodes=0, edges=0)"
        assert not g
        g.add_node(1)
        assert g
        assert len(g) == 1


# ════════════════════════════════════════════════════════════
# IntDiGraphMap
# ════════════════════════════════════════════════════════════


class TestIntDiGraphMap:
    def test_basics(self):
        g = IntDiGraphMap()
        g.add_node(1)
        g.add_node(2)
        g.add_edge(1, 2, "weight")
        assert g.node_count == 2
        assert g.edge_count == 1

    def test_directed_neighbors(self):
        g = IntDiGraphMap()
        g.add_node(1)
        g.add_node(2)
        g.add_edge(1, 2, "w")
        assert 2 in g.neighbors(1)
        assert 1 not in g.neighbors(2)

    def test_degree(self):
        g = IntDiGraphMap()
        g.add_node(1)
        g.add_node(2)
        g.add_node(3)
        g.add_edge(1, 2, "a")
        g.add_edge(3, 1, "b")
        assert g.out_degree(1) == 1
        assert g.in_degree(1) == 1

    def test_remove(self):
        g = IntDiGraphMap()
        g.add_node(1)
        g.add_node(2)
        g.add_edge(1, 2, "w")
        w = g.remove_edge(1, 2)
        assert w == "w"
        assert g.edge_count == 0
        assert g.remove_node(2) is True
        assert g.node_count == 1

    def test_dijkstra(self):
        g = IntDiGraphMap()
        g.add_node(1)
        g.add_node(2)
        g.add_node(3)
        g.add_edge(1, 2, 1.0)
        g.add_edge(2, 3, 2.0)
        dists = g.dijkstra(1)
        assert dists[3] == 3.0

    def test_dijkstra_invalid(self):
        g = IntDiGraphMap()
        g.add_node(1)
        with pytest.raises(IndexError):
            g.dijkstra(99)

    def test_protocols(self):
        g = IntDiGraphMap()
        assert repr(g) == "IntDiGraphMap(nodes=0, edges=0)"
        assert not g
        g.add_node(1)
        assert g
        assert len(g) == 1


# ════════════════════════════════════════════════════════════
# MatrixDiGraph
# ════════════════════════════════════════════════════════════


class TestMatrixDiGraph:
    def test_basics(self):
        g = MatrixDiGraph()
        n0 = g.add_node("A")
        n1 = g.add_node("B")
        g.add_edge(n0, n1, 1.5)
        assert g.node_count == 2
        assert g.edge_count == 1

    def test_has_edge(self):
        g = MatrixDiGraph()
        g.add_node("A")
        g.add_node("B")
        g.add_edge(0, 1, 1.0)
        assert g.has_edge(0, 1) is True
        assert g.has_edge(1, 0) is False

    def test_remove_edge(self):
        g = MatrixDiGraph()
        g.add_node("A")
        g.add_node("B")
        g.add_edge(0, 1, 1.0)
        assert g.remove_edge(0, 1) is True
        assert g.edge_count == 0
        assert g.remove_edge(0, 1) is False

    def test_add_edge_invalid(self):
        g = MatrixDiGraph()
        g.add_node("A")
        with pytest.raises(IndexError):
            g.add_edge(0, 99, 1.0)

    def test_dijkstra(self):
        g = MatrixDiGraph()
        g.add_node("A")
        g.add_node("B")
        g.add_edge(0, 1, 1.5)
        dists = g.dijkstra(0)
        assert dists[1] == 1.5

    def test_dijkstra_invalid(self):
        g = MatrixDiGraph()
        g.add_node("A")
        with pytest.raises(IndexError):
            g.dijkstra(99)

    def test_bellman_ford(self):
        g = MatrixDiGraph()
        g.add_node("A")
        g.add_node("B")
        g.add_node("C")
        g.add_edge(0, 1, 1.0)
        g.add_edge(1, 2, 2.0)
        dists = g.bellman_ford(0)
        assert dists[2] == 3.0

    def test_bellman_ford_invalid(self):
        g = MatrixDiGraph()
        g.add_node("A")
        with pytest.raises(IndexError):
            g.bellman_ford(99)

    def test_protocols(self):
        g = MatrixDiGraph()
        assert repr(g) == "MatrixDiGraph(nodes=0, edges=0)"
        assert not g
        g.add_node("A")
        assert g
        assert len(g) == 1


# ════════════════════════════════════════════════════════════
# CsrGraph
# ════════════════════════════════════════════════════════════


class TestCsrGraph:
    def test_basics(self):
        g = CsrGraph.from_edges(3, [(0, 1, 1.5), (1, 2, 2.0)])
        assert g.node_count == 3
        assert g.edge_count == 2

    def test_sorted_flag(self):
        g = CsrGraph.from_edges(3, [(0, 1, 1.0), (1, 2, 2.0)], sorted=True)
        assert g.node_count == 3
        dists = g.dijkstra(0)
        assert dists[2] == 3.0

    def test_dijkstra(self):
        g = CsrGraph.from_edges(3, [(0, 1, 1.5), (1, 2, 2.0)])
        dists = g.dijkstra(0)
        assert dists[2] == 3.5

    def test_dijkstra_invalid(self):
        g = CsrGraph.from_edges(2, [(0, 1, 1.0)])
        with pytest.raises(IndexError):
            g.dijkstra(99)

    def test_bellman_ford(self):
        g = CsrGraph.from_edges(3, [(0, 1, 1.0), (1, 2, 2.0)])
        dists = g.bellman_ford(0)
        assert dists[2] == 3.0

    def test_bellman_ford_invalid(self):
        g = CsrGraph.from_edges(2, [(0, 1, 1.0)])
        with pytest.raises(IndexError):
            g.bellman_ford(99)

    def test_protocols(self):
        g = CsrGraph.from_edges(3, [(0, 1, 1.0)])
        assert "CsrGraph" in repr(g)
        assert g
        assert len(g) == 3

    def test_empty(self):
        g = CsrGraph.from_edges(0, [])
        assert g.node_count == 0
        assert g.edge_count == 0
        assert not g


# ════════════════════════════════════════════════════════════
# UnionFind
# ════════════════════════════════════════════════════════════


class TestUnionFind:
    def test_basics(self):
        uf = UnionFind(5)
        assert len(uf) == 5
        assert "UnionFind(size=5)" in repr(uf)

    def test_find(self):
        uf = UnionFind(3)
        assert uf.find(0) == 0
        assert uf.find(1) == 1

    def test_union(self):
        uf = UnionFind(3)
        assert uf.union(0, 1) is True
        assert uf.find(0) == uf.find(1)

    def test_union_same(self):
        uf = UnionFind(3)
        uf.union(0, 1)
        assert uf.union(0, 1) is False  # already unioned

    def test_equiv(self):
        uf = UnionFind(3)
        assert not uf.equiv(0, 1)
        uf.union(0, 1)
        assert uf.equiv(0, 1)
        assert not uf.equiv(0, 2)

    def test_into_labeling(self):
        uf = UnionFind(4)
        uf.union(0, 1)
        uf.union(2, 3)
        labels = uf.into_labeling()
        assert len(labels) == 4
        assert labels[0] == labels[1]
        assert labels[2] == labels[3]
        assert labels[0] != labels[2]

    def test_transitive(self):
        uf = UnionFind(5)
        uf.union(0, 1)
        uf.union(1, 2)
        assert uf.equiv(0, 2)

    def test_single_element(self):
        uf = UnionFind(1)
        assert uf.find(0) == 0
        assert len(uf) == 1

    def test_empty(self):
        uf = UnionFind(0)
        assert len(uf) == 0


# ════════════════════════════════════════════════════════════
# Isomorphism
# ════════════════════════════════════════════════════════════


class TestIsomorphism:
    def test_isomorphic(self):
        g1 = DiGraph()
        g1.add_node(0)
        g1.add_node(1)
        g1.add_edge(0, 1, 1.0)

        g2 = DiGraph()
        g2.add_node("A")
        g2.add_node("B")
        g2.add_edge(0, 1, 5.0)

        assert is_isomorphic(g1, g2)

    def test_not_isomorphic(self):
        g1 = DiGraph()
        g1.add_node(0)
        g1.add_node(1)
        g1.add_edge(0, 1, 1.0)

        g2 = DiGraph()
        g2.add_node(0)
        g2.add_node(1)
        # no edge
        assert not is_isomorphic(g1, g2)

    def test_empty_graphs_isomorphic(self):
        assert is_isomorphic(DiGraph(), DiGraph())

    def test_single_node(self):
        g1 = DiGraph()
        g1.add_node(0)
        g2 = DiGraph()
        g2.add_node("X")
        assert is_isomorphic(g1, g2)


# ════════════════════════════════════════════════════════════
# Edge cases & boundary conditions
# ════════════════════════════════════════════════════════════


class TestEdgeCases:
    def test_empty_graph_operations(self):
        """All operations on an empty graph should not crash."""
        g = DiGraph()
        assert g.node_count == 0
        assert g.edge_count == 0
        assert g.toposort() == []
        assert g.tarjan_scc() == []
        assert g.kosaraju_scc() == []
        assert g.is_cyclic() is False
        assert g.page_rank() == []
        assert g.node_indices() == []
        assert g.edge_indices() == []
        assert not g
        assert len(g) == 0

    def test_single_node_graph(self):
        g = DiGraph()
        n = g.add_node("alone")
        assert g.bfs(n) == [0]
        assert g.dfs(n) == [0]
        assert g.dijkstra(n) == {0: 0.0}
        assert g.is_cyclic() is False
        assert g.toposort() == [0]
        assert g.has_path_connecting(n, n) is True
        ranks = g.page_rank()
        assert len(ranks) == 1

    def test_self_loop_detection(self):
        g = DiGraph()
        n = g.add_node(0)
        g.add_edge(n, n, 1.0)
        assert g.is_cyclic() is True
        assert g.neighbors(n) == [0]
        assert g.out_degree(n) == 1
        assert g.in_degree(n) == 1

    def test_parallel_edges(self):
        g = DiGraph()
        g.add_node(0)
        g.add_node(1)
        e0 = g.add_edge(0, 1, "first")
        e1 = g.add_edge(0, 1, "second")
        assert g.edge_count == 2
        assert g.edge_weight(e0) == "first"
        assert g.edge_weight(e1) == "second"

    def test_large_graph_bfs(self):
        """Test traversal on a larger graph."""
        g = DiGraph()
        n = 100
        for i in range(n):
            g.add_node(i)
        for i in range(n - 1):
            g.add_edge(i, i + 1, 1.0)
        result = g.bfs(0)
        assert len(result) == n
        assert result[0] == 0
        assert result[-1] == n - 1

    def test_disconnected_graph_bfs(self):
        g = DiGraph()
        g.add_node("A")
        g.add_node("B")
        g.add_node("C")
        g.add_edge(0, 1, 1.0)
        # C is disconnected
        assert set(g.bfs(0)) == {0, 1}
        assert g.bfs(2) == [2]

    def test_complex_weight_types(self):
        """Nodes and edges can hold any Python object."""
        g = DiGraph()
        g.add_node({"key": "value", "nested": [1, 2, 3]})
        g.add_node((1, 2, 3))
        g.add_node(None)
        g.add_edge(0, 1, {"edge_info": True})
        assert g.node_weight(0) == {"key": "value", "nested": [1, 2, 3]}
        assert g.node_weight(1) == (1, 2, 3)
        assert g.node_weight(2) is None

    def test_diamond_graph_all_simple_paths(self):
        """Diamond: 0->{1,2}, 1->3, 2->3"""
        g = DiGraph()
        for i in range(4):
            g.add_node(i)
        g.add_edge(0, 1, 1.0)
        g.add_edge(0, 2, 1.0)
        g.add_edge(1, 3, 1.0)
        g.add_edge(2, 3, 1.0)
        paths = g.all_simple_paths(0, 3, 0, None)
        assert len(paths) == 2

    def test_multiple_sccs(self):
        """Graph with 3 separate SCCs."""
        g = DiGraph()
        for i in range(6):
            g.add_node(i)
        # SCC1: 0 <-> 1
        g.add_edge(0, 1, 1.0)
        g.add_edge(1, 0, 1.0)
        # SCC2: 2 <-> 3
        g.add_edge(2, 3, 1.0)
        g.add_edge(3, 2, 1.0)
        # SCC3: 4, 5 (singletons)
        sccs = g.tarjan_scc()
        assert len(sccs) == 4  # two 2-node SCCs + two singletons

    def test_add_edge_after_remove_node(self):
        """After remove_node, old indices may be invalid."""
        g = DiGraph()
        g.add_node("A")  # 0
        g.add_node("B")  # 1
        g.add_node("C")  # 2
        g.remove_node(1)  # C -> 1, count = 2
        # Now valid indices are 0 and 1
        g.add_edge(0, 1, 1.0)  # should work
        assert g.edge_count == 1
        with pytest.raises(IndexError):
            g.add_edge(0, 2, 1.0)  # index 2 doesn't exist

    def test_ungraph_self_loop(self):
        g = UnGraph()
        n = g.add_node(0)
        g.add_edge(n, n, 1.0)
        assert g.edge_count == 1

    def test_stable_digraph_add_after_remove(self):
        """StableDiGraph should keep stable indices."""
        g = StableDiGraph()
        n0 = g.add_node("A")
        n1 = g.add_node("B")
        n2 = g.add_node("C")
        g.remove_node(n1)
        # n2 should still be accessible at original index
        assert g.contains_node(n2)
        # Adding new node should get next available index
        n3 = g.add_node("D")
        assert n3 >= 0
        assert g.node_count == 3

    def test_from_edges_with_py_objects(self):
        """from_edges should handle arbitrary Python objects as weights."""
        g = DiGraph.from_edges([(0, 1, {"w": 1}), (1, 2, [1, 2])])
        assert g.node_count == 3
        assert g.edge_count == 2
