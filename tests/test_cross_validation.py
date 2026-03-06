import networkx as nx
import pytest

from pypetgraph import DiGraph, FastDiGraph, UnGraph


def nx_to_pypet(nx_g, pypet_cls):
    """Helper to convert a NetworkX graph to a pypetgraph instance."""
    if isinstance(nx_g, nx.DiGraph):
        pypet_g = pypet_cls()
        for n in nx_g.nodes():
            pypet_g.add_node(n)
        for u, v, data in nx_g.edges(data=True):
            weight = data.get("weight", 1.0)
            pypet_g.add_edge(u, v, weight)
        return pypet_g
    else:
        pypet_g = pypet_cls()
        for n in nx_g.nodes():
            pypet_g.add_node(n)
        for u, v, data in nx_g.edges(data=True):
            weight = data.get("weight", 1.0)
            pypet_g.add_edge(u, v, weight)
        return pypet_g

class TestCrossValidation:
    @pytest.fixture
    def random_digraph(self):
        # Create a random directed graph with 20 nodes and 100 edges
        return nx.gnm_random_graph(20, 100, directed=True, seed=42)

    @pytest.fixture
    def random_weighted_digraph(self):
        G = nx.gnm_random_graph(20, 100, directed=True, seed=42)
        import random
        rng = random.Random(42)
        for u, v in G.edges():
            G[u][v]['weight'] = rng.uniform(1.0, 10.0)
        return G

    def test_dijkstra_comparison(self, random_weighted_digraph):
        nx_g = random_weighted_digraph
        pg_g = nx_to_pypet(nx_g, FastDiGraph)

        start_node = 0
        nx_dists = nx.single_source_dijkstra_path_length(nx_g, start_node)
        pg_dists = pg_g.dijkstra(start_node)

        # Compare results
        for node, dist in nx_dists.items():
            assert pg_dists[node] == pytest.approx(dist)
        assert len(nx_dists) == len(pg_dists)

    def test_bellman_ford_comparison(self, random_weighted_digraph):
        nx_g = random_weighted_digraph
        pg_g = nx_to_pypet(nx_g, FastDiGraph)

        start_node = 0
        nx_dists = nx.single_source_bellman_ford_path_length(nx_g, start_node)
        pg_dists = pg_g.bellman_ford(start_node)

        for node, dist in nx_dists.items():
            assert pg_dists[node] == pytest.approx(dist)

    def test_floyd_warshall_comparison(self, random_weighted_digraph):
        nx_g = random_weighted_digraph
        pg_g = nx_to_pypet(nx_g, FastDiGraph)

        nx_res = dict(nx.floyd_warshall(nx_g))
        pg_res = pg_g.floyd_warshall()

        for u in nx_g.nodes():
            for v in nx_g.nodes():
                nx_val = nx_res[u][v]
                if nx_val == float('inf'):
                    assert u not in pg_res or v not in pg_res[u]
                else:
                    assert pg_res[u][v] == pytest.approx(nx_val)

    def test_pagerank_comparison(self, random_digraph):
        nx_g = random_digraph
        pg_g = nx_to_pypet(nx_g, FastDiGraph)

        # NetworkX's default tolerance is 1e-6, petgraph's might be different.
        # Also handling of dangling nodes might vary slightly.
        nx_ranks = nx.pagerank(nx_g, alpha=0.85, max_iter=100)
        pg_ranks = pg_g.page_rank(damping_factor=0.85, iterations=100)

        for node, rank in nx_ranks.items():
            assert pg_ranks[node] == pytest.approx(rank, rel=2e-2)

    def test_scc_comparison(self, random_digraph):
        nx_g = random_digraph
        pg_g = nx_to_pypet(nx_g, DiGraph)

        nx_sccs = [set(s) for s in nx.strongly_connected_components(nx_g)]
        pg_sccs = [set(s) for s in pg_g.tarjan_scc()]

        # Sort by smallest element to compare sets
        nx_sccs.sort(key=lambda s: min(s))
        pg_sccs.sort(key=lambda s: min(s))

        assert nx_sccs == pg_sccs

    def test_toposort_comparison(self):
        # Create a DAG
        nx_g = nx.DiGraph([(0, 1), (1, 2), (0, 2), (2, 3)])
        pg_g = nx_to_pypet(nx_g, FastDiGraph)

        pg_order = pg_g.toposort()

        # Verify the order is valid for NetworkX
        # A list is a valid topological sort if for every edge (u, v), u comes before v
        node_to_pos = {node: i for i, node in enumerate(pg_order)}
        for u, v in nx_g.edges():
            assert node_to_pos[u] < node_to_pos[v]

    def test_is_cyclic_comparison(self, random_digraph):
        nx_g = random_digraph
        pg_g = nx_to_pypet(nx_g, FastDiGraph)

        assert pg_g.is_cyclic() == (not nx.is_directed_acyclic_graph(nx_g))

    def test_connected_components_ungraph(self):
        nx_g = nx.Graph([(0, 1), (2, 3), (4, 4)])
        pg_g = nx_to_pypet(nx_g, UnGraph)

        assert pg_g.connected_components() == nx.number_connected_components(nx_g)

    def test_bellman_ford_unreachable_nodes_absent(self):
        """Regression: bellman_ford used to return f64::INFINITY for unreachable nodes.
        Now they must be absent from the result dict, consistent with NetworkX.
        """
        # Make a graph where some nodes are unreachable from node 0
        nx_g = nx.DiGraph()
        nx_g.add_weighted_edges_from([(0, 1, 1.0), (1, 2, 2.0)])  # node 3 is isolated
        nx_g.add_node(3)
        pg_g = nx_to_pypet(nx_g, FastDiGraph)

        nx_dists = dict(nx.single_source_bellman_ford_path_length(nx_g, 0))
        pg_dists = pg_g.bellman_ford(0)

        # NetworkX only includes reachable nodes; our implementation must match
        assert set(nx_dists.keys()) == set(pg_dists.keys()), (
            f"bellman_ford result keys differ. NX: {set(nx_dists)}, PG: {set(pg_dists)}"
        )
        for node, dist in nx_dists.items():
            assert pg_dists[node] == pytest.approx(dist)

    def test_floyd_warshall_self_distances_zero(self):
        """floyd_warshall must include self-distance = 0 for all nodes (matches NetworkX)."""
        nx_g = nx.DiGraph([(0, 1, ), (1, 2)])
        for u, v in nx_g.edges():
            nx_g[u][v]['weight'] = 1.0
        pg_g = nx_to_pypet(nx_g, FastDiGraph)

        nx_res = dict(nx.floyd_warshall(nx_g))
        pg_res = pg_g.floyd_warshall()

        for node in nx_g.nodes():
            assert pg_res.get(node, {}).get(node, None) == pytest.approx(0.0), (
                f"Self-distance for node {node} must be 0.0"
            )
