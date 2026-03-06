"""
Tests for specific correctness properties that are easy to miss:
- bellman_ford / floyd_warshall negative cycle detection
- bellman_ford unreachable node filtering
- floyd_warshall sentinel filtering (petgraph uses f64::MAX/2, not infinity)
- update_edge validation (fixed bug: previously could panic Rust)
- from_edges default node weight is now None
- to_scipy_coo correctness
- bfs/dfs invalid start node error (fixed bug: was silently returning [])
- UnGraph new methods: find_edge, edge_weight, edge_indices, node_indices
- StableDiGraph stable index behaviour across remove+add cycles
"""
import pytest

from pypetgraph import (
    CsrGraph,
    DiGraph,
    FastDiGraph,
    MatrixDiGraph,
    StableDiGraph,
    UnGraph,
)


# ════════════════════════════════════════════════════════════
# Correctness regressions for fixed bugs
# ════════════════════════════════════════════════════════════


class TestBellmanFordCorrectness:
    """Verifies bellman_ford filters unreachable nodes (was broken before fix)."""

    def test_unreachable_nodes_not_in_result_fast(self):
        """Nodes unreachable from start must be absent, not returned as infinity."""
        g = FastDiGraph()
        g.add_node(0)
        g.add_node(1)
        g.add_node(2)
        g.add_edge(0, 1, 1.0)
        # Node 2 is not reachable from 0
        dists = g.bellman_ford(0)
        assert 0 in dists
        assert 1 in dists
        assert 2 not in dists, "Unreachable node must not appear in bellman_ford result"

    def test_unreachable_nodes_not_in_result_matrix(self):
        g = MatrixDiGraph()
        g.add_node("A")
        g.add_node("B")
        g.add_node("C")
        g.add_edge(0, 1, 5.0)
        dists = g.bellman_ford(0)
        assert 2 not in dists, "Unreachable node must not appear in bellman_ford result"

    def test_unreachable_nodes_not_in_result_csr(self):
        # node 2 has no incoming edges from node 0
        g = CsrGraph.from_edges(3, [(0, 1, 1.0)])
        dists = g.bellman_ford(0)
        assert 2 not in dists, "Unreachable node must not appear in bellman_ford result"

    def test_negative_weight_edge_fast(self):
        """bellman_ford must handle negative edge weights correctly."""
        g = FastDiGraph()
        for i in range(4):
            g.add_node(i)
        g.add_edge(0, 1, 4.0)
        g.add_edge(0, 2, 5.0)
        g.add_edge(1, 2, -3.0)  # negative: path 0→1→2 = 1.0 total
        g.add_edge(2, 3, 2.0)
        dists = g.bellman_ford(0)
        assert dists[2] == pytest.approx(1.0)
        assert dists[3] == pytest.approx(3.0)

    def test_negative_cycle_raises_fast(self):
        g = FastDiGraph()
        for i in range(3):
            g.add_node(i)
        g.add_edge(0, 1, 1.0)
        g.add_edge(1, 2, -3.0)
        g.add_edge(2, 0, 1.0)  # negative cycle: total -1
        with pytest.raises(ValueError, match="Negative cycle"):
            g.bellman_ford(0)

    def test_negative_cycle_raises_matrix(self):
        g = MatrixDiGraph()
        for i in range(3):
            g.add_node(i)
        g.add_edge(0, 1, 1.0)
        g.add_edge(1, 2, -3.0)
        g.add_edge(2, 0, 1.0)
        with pytest.raises(ValueError, match="Negative cycle"):
            g.bellman_ford(0)

    def test_negative_cycle_raises_csr(self):
        g = CsrGraph.from_edges(3, [(0, 1, 1.0), (1, 2, -3.0), (2, 0, 1.0)])
        with pytest.raises(ValueError, match="Negative cycle"):
            g.bellman_ford(0)


class TestFloydWarshallCorrectness:
    """Verifies floyd_warshall correctly filters petgraph's sentinel value."""

    def test_unreachable_pair_absent_fast(self):
        """Pairs with no path must be absent (petgraph uses f64::MAX/2, not inf)."""
        g = FastDiGraph()
        for i in range(4):
            g.add_node(i)
        g.add_edge(0, 1, 1.0)
        g.add_edge(2, 3, 1.0)  # disconnected component
        res = g.floyd_warshall()
        assert 0 not in res or 2 not in res.get(0, {}), "No path 0→2 must be absent"
        assert 0 not in res or 3 not in res.get(0, {}), "No path 0→3 must be absent"

    def test_unreachable_pair_absent_csr(self):
        g = CsrGraph.from_edges(4, [(0, 1, 1.0), (2, 3, 1.0)])
        res = g.floyd_warshall()
        assert res.get(0, {}).get(2) is None, "No path 0→2 must be absent"

    def test_self_distance_is_zero(self):
        """floyd_warshall must include self-distance = 0 for all nodes."""
        g = FastDiGraph()
        for i in range(3):
            g.add_node(i)
        g.add_edge(0, 1, 1.0)
        g.add_edge(1, 2, 1.0)
        res = g.floyd_warshall()
        assert res[0][0] == 0.0
        assert res[1][1] == 0.0

    def test_negative_cycle_raises_fast(self):
        g = FastDiGraph()
        for i in range(3):
            g.add_node(i)
        g.add_edge(0, 1, 1.0)
        g.add_edge(1, 0, -2.0)  # negative cycle
        with pytest.raises(ValueError, match="Negative cycle"):
            g.floyd_warshall()

    def test_path_via_intermediate_fast(self):
        """0→1→2 must be shorter than direct 0→2 when edge weights dictate it."""
        g = FastDiGraph()
        for i in range(3):
            g.add_node(i)
        g.add_edge(0, 1, 1.0)
        g.add_edge(1, 2, 1.0)
        g.add_edge(0, 2, 10.0)  # direct is slower
        res = g.floyd_warshall()
        assert res[0][2] == pytest.approx(2.0)


class TestUpdateEdgeValidation:
    """Regression tests for bug: update_edge could panic Rust on bad node indices."""

    def test_update_edge_invalid_u_raises(self):
        g = DiGraph()
        g.add_node("A")
        g.add_node("B")
        with pytest.raises(IndexError):
            g.update_edge(99, 1, 5.0)

    def test_update_edge_invalid_v_raises(self):
        g = DiGraph()
        g.add_node("A")
        g.add_node("B")
        with pytest.raises(IndexError):
            g.update_edge(0, 99, 5.0)

    def test_update_edge_changes_weight(self):
        g = DiGraph()
        g.add_node("A")
        g.add_node("B")
        e = g.add_edge(0, 1, 1.0)
        g.update_edge(0, 1, 99.0)
        assert g.edge_weight(e) == 99.0

    def test_update_edge_creates_if_absent(self):
        """update_edge on petgraph creates the edge if it doesn't exist."""
        g = DiGraph()
        g.add_node("A")
        g.add_node("B")
        # No existing edge — update_edge should create it
        e = g.update_edge(0, 1, 42.0)
        assert g.edge_count == 1
        assert g.edge_weight(e) == 42.0


class TestBfsRaisesOnInvalidStart:
    """Regression: bfs/dfs previously returned [] silently on invalid start."""

    def test_digraph_bfs_invalid_raises(self):
        g = DiGraph()
        g.add_node("A")
        with pytest.raises(IndexError):
            g.bfs(99)

    def test_digraph_dfs_invalid_raises(self):
        g = DiGraph()
        g.add_node("A")
        with pytest.raises(IndexError):
            g.dfs(99)

    def test_ungraph_bfs_invalid_raises(self):
        g = UnGraph()
        g.add_node("A")
        with pytest.raises(IndexError):
            g.bfs(99)

    def test_ungraph_dfs_invalid_raises(self):
        g = UnGraph()
        g.add_node("A")
        with pytest.raises(IndexError):
            g.dfs(99)

    def test_fast_bfs_invalid_raises(self):
        g = FastDiGraph()
        g.add_node("A")
        with pytest.raises(IndexError):
            g.bfs(99)

    def test_fast_dfs_invalid_raises(self):
        g = FastDiGraph()
        g.add_node("A")
        with pytest.raises(IndexError):
            g.dfs(99)


class TestFromEdgesDefaultWeight:
    """Regression: from_edges previously set auto-node weight to integer index."""

    def test_auto_nodes_have_none_weight(self):
        """Nodes auto-created by from_edges must have None as weight, not int."""
        g = DiGraph.from_edges([(0, 1, "edge_w")])
        # Nodes 0 and 1 were auto-created; their weights should be None
        assert g.node_weight(0) is None, "Auto-created node weight must be None"
        assert g.node_weight(1) is None, "Auto-created node weight must be None"

    def test_explicit_edges_preserved(self):
        g = DiGraph.from_edges([(0, 1, 99)])
        assert g.edge_weight(0) == 99

    def test_node_count_with_explicit_count(self):
        g = DiGraph.from_edges([(0, 1, 1.0)], node_count=5)
        assert g.node_count == 5
        for i in range(5):
            assert g.node_weight(i) is None


class TestUnGraphNewMethods:
    """Tests for find_edge / edge_weight / edge_indices / node_indices on UnGraph."""

    def test_find_edge_existing(self):
        g = UnGraph()
        g.add_node("A")
        g.add_node("B")
        e = g.add_edge(0, 1, "w")
        assert g.find_edge(0, 1) == e
        # undirected: reverse direction also works
        assert g.find_edge(1, 0) == e

    def test_find_edge_missing(self):
        g = UnGraph()
        g.add_node("A")
        g.add_node("B")
        assert g.find_edge(0, 1) is None

    def test_edge_weight(self):
        g = UnGraph()
        g.add_node("A")
        g.add_node("B")
        g.add_edge(0, 1, {"meta": "data"})
        assert g.edge_weight(0) == {"meta": "data"}
        assert g.edge_weight(99) is None

    def test_edge_indices(self):
        g = UnGraph()
        for i in range(3):
            g.add_node(i)
        g.add_edge(0, 1, 1.0)
        g.add_edge(1, 2, 2.0)
        assert sorted(g.edge_indices()) == [0, 1]

    def test_node_indices(self):
        g = UnGraph()
        for i in range(3):
            g.add_node(i)
        assert g.node_indices() == [0, 1, 2]

    def test_node_indices_after_remove(self):
        g = UnGraph()
        for i in range(3):
            g.add_node(i)
        g.remove_node(1)  # Graph's remove swaps with last
        indices = g.node_indices()
        assert len(indices) == 2
        assert set(indices) == {0, 1}


class TestStableDiGraphStability:
    """Verifies stable index contract across add/remove cycles."""

    def test_removed_index_not_reused_immediately(self):
        """After removing a node, its index must not be considered valid."""
        g = StableDiGraph()
        n0 = g.add_node("A")
        n1 = g.add_node("B")
        g.remove_node(n1)
        assert not g.contains_node(n1)
        # n0 must still be valid
        assert g.contains_node(n0)

    def test_surviving_nodes_keep_original_indices(self):
        """The stable contract: surviving nodes must keep their original indices
        when other nodes are removed.
        """
        g = StableDiGraph()
        n0 = g.add_node("A")
        n1 = g.add_node("B")
        n2 = g.add_node("C")

        g.remove_node(n1)  # Remove middle node
        # n0 and n2 must still be accessible at their ORIGINAL indices
        assert g.contains_node(n0), "Surviving node n0 must keep its index"
        assert g.contains_node(n2), "Surviving node n2 must keep its index"
        assert not g.contains_node(n1), "Removed node must be gone"

    def test_add_edge_after_remove_uses_contains_not_bound(self):
        """add_edge must use contains_node check (not node_bound), 
        so it rejects properly-removed nodes even if their index < node_bound."""
        g = StableDiGraph()
        n0 = g.add_node("A")
        n1 = g.add_node("B")
        g.remove_node(n1)
        # n1 was removed: must raise even though n1 < node_bound
        with pytest.raises(IndexError):
            g.add_edge(n0, n1, "edge")

    def test_edge_survives_unrelated_node_removal(self):
        """Edges between surviving nodes must survive removal of other nodes."""
        g = StableDiGraph()
        n0 = g.add_node("A")
        n1 = g.add_node("B")
        n2 = g.add_node("C")
        g.add_edge(n0, n2, "direct")
        g.remove_node(n1)  # unrelated node
        assert g.edge_count == 1  # edge between n0 and n2 must survive


class TestToScipyCoo:
    """to_scipy_coo is used by SciPy PageRank — must return correct COO format."""

    def test_basic_structure(self):
        g = DiGraph()
        for i in range(3):
            g.add_node(i)
        g.add_edge(0, 1, 2.0)
        g.add_edge(1, 2, 3.0)
        rows, cols, weights = g.to_scipy_coo()
        assert len(rows) == 2
        assert len(cols) == 2
        assert len(weights) == 2
        pairs = set(zip(rows, cols))
        assert (0, 1) in pairs
        assert (1, 2) in pairs

    def test_weights_match_edges(self):
        g = DiGraph()
        g.add_node("A")
        g.add_node("B")
        g.add_edge(0, 1, 7.5)
        rows, cols, weights = g.to_scipy_coo()
        assert weights[0] == pytest.approx(7.5)

    def test_empty_graph(self):
        g = DiGraph()
        rows, cols, weights = g.to_scipy_coo()
        assert rows == []
        assert cols == []
        assert weights == []

    def test_fast_digraph_coo(self):
        g = FastDiGraph()
        for i in range(3):
            g.add_node(i)
        g.add_edge(0, 1, 1.0)
        g.add_edge(0, 2, 2.0)
        rows, cols, weights = g.to_scipy_coo()
        assert len(weights) == 2
        assert set(zip(rows, cols)) == {(0, 1), (0, 2)}
