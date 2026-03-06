import pytest

from pypetgraph import (
    CsrGraph,
    DiGraph,
    FastDiGraph,
)

# ════════════════════════════════════════════════════════════
# Sync Tests for New APIs
# ════════════════════════════════════════════════════════════

class TestNewAPIsSync:
    def test_floyd_warshall(self):
        # Test on multiple graph types
        for GCls in [DiGraph, FastDiGraph]:
            g = GCls()
            for i in range(3):
                g.add_node(i)
            g.add_edge(0, 1, 1.0)
            g.add_edge(1, 2, 2.0)
            g.add_edge(0, 2, 5.0)

            res = g.floyd_warshall()
            assert res[0][1] == 1.0
            assert res[1][2] == 2.0
            assert res[0][2] == 3.0 # Shortest via 1
            assert 2 not in res or 1 not in res[2] # No path from 2 to 1

    def test_csr_floyd_warshall(self):
        g = CsrGraph.from_edges(3, [(0, 1, 1.0), (1, 2, 2.0), (0, 2, 5.0)])
        res = g.floyd_warshall()
        assert res[0][2] == 3.0

    def test_k_shortest_path(self):
        g = DiGraph()
        for i in range(4):
            g.add_node(i)
        # 0 -> 1 (1.0) -> 3 (1.0) = 2.0  (1st shortest)
        # 0 -> 2 (2.0) -> 3 (1.0) = 3.0  (2nd shortest)
        # 0 -> 3 (10.0) = 10.0           (3rd shortest)
        g.add_edge(0, 1, 1.0)
        g.add_edge(1, 3, 1.0)
        g.add_edge(0, 2, 2.0)
        g.add_edge(2, 3, 1.0)
        g.add_edge(0, 3, 10.0)

        # In 0.7.1, k_shortest_path(..., k) returns the cost of the k-th shortest path
        res1 = g.k_shortest_path(0, 3, 1)
        assert res1[3] == 2.0

        res2 = g.k_shortest_path(0, 3, 2)
        assert res2[3] == 3.0

        res3 = g.k_shortest_path(0, 3, 3)
        assert res3[3] == 10.0

    def test_k_shortest_path_custom_weight(self):
        g = DiGraph()
        for i in range(3):
            g.add_node(i)
        g.add_edge(0, 1, {"cost": 10})
        g.add_edge(1, 2, {"cost": 5})

        # weight_fn receives (u, v, weight_obj)
        def weight_fn(u, v, w):
            return float(w["cost"])

        res = g.k_shortest_path(0, 2, 1, weight_fn=weight_fn)
        assert res[2] == 15.0

    def test_fast_digraph_bellman_ford(self):
        g = FastDiGraph()
        for i in range(3):
            g.add_node(i)
        g.add_edge(0, 1, 5.0)
        g.add_edge(1, 2, -2.0)
        dists = g.bellman_ford(0)
        assert dists[2] == 3.0

# ════════════════════════════════════════════════════════════
# Async Tests for New APIs
# ════════════════════════════════════════════════════════════

@pytest.mark.asyncio
class TestNewAPIsAsync:
    async def test_floyd_warshall_async(self):
        g = FastDiGraph()
        for i in range(3):
            g.add_node(i)
        g.add_edge(0, 1, 1.0)
        g.add_edge(1, 2, 1.0)
        res = await g.floyd_warshall_async()
        assert res[0][2] == 2.0

    async def test_k_shortest_path_async(self):
        g = DiGraph()
        for i in range(3):
            g.add_node(i)
        g.add_edge(0, 1, 1.0)
        g.add_edge(1, 2, 1.0)
        res = await g.k_shortest_path_async(0, 2, 1)
        assert res[2] == 2.0
