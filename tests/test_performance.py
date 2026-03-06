import os

import networkx as nx
import psutil
import pytest

from pypetgraph import DiGraph, FastDiGraph


def get_process_memory():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)

@pytest.fixture(scope="module")
def large_graph_data():
    """Generate a larger graph for meaningful benchmarking: 5000 nodes, 50,000 edges."""
    n = 5000
    edges = []
    for i in range(n):
        for j in range(1, 11):
            if i + j < n:
                edges.append((i, i + j, float(j)))
    return n, edges

# ════════════════════════════════════════════════════════════
# Dijkstra Benchmarks
# ════════════════════════════════════════════════════════════

@pytest.mark.benchmark
def test_benchmark_nx_dijkstra(benchmark, large_graph_data):
    n, edges = large_graph_data
    G = nx.DiGraph()
    G.add_nodes_from(range(n))
    G.add_weighted_edges_from(edges)

    def run():
        return nx.single_source_dijkstra_path_length(G, 0)

    benchmark.pedantic(run, rounds=10, iterations=1)

@pytest.mark.benchmark
def test_benchmark_pg_digraph_dijkstra(benchmark, large_graph_data):
    n, edges = large_graph_data
    g = DiGraph()
    for i in range(n):
        g.add_node(i)
    for u, v, w in edges:
        g.add_edge(u, v, w)

    def run():
        return g.dijkstra(0)

    benchmark.pedantic(run, rounds=10, iterations=1)

@pytest.mark.benchmark
def test_benchmark_pg_fast_digraph_dijkstra(benchmark, large_graph_data):
    n, edges = large_graph_data
    g = FastDiGraph()
    for i in range(n):
        g.add_node(i)
    for u, v, w in edges:
        g.add_edge(u, v, w)

    def run():
        return g.dijkstra(0)

    benchmark.pedantic(run, rounds=10, iterations=1)

# ════════════════════════════════════════════════════════════
# PageRank Benchmarks
# ════════════════════════════════════════════════════════════

@pytest.mark.benchmark
def test_benchmark_nx_pagerank(benchmark, large_graph_data):
    n, edges = large_graph_data
    G = nx.DiGraph()
    G.add_nodes_from(range(n))
    G.add_weighted_edges_from(edges)

    # Note: NetworkX pagerank requires scipy/numpy for performance
    def run():
        return nx.pagerank(G, alpha=0.85, max_iter=50)

    benchmark.pedantic(run, rounds=5, iterations=1)

@pytest.mark.benchmark
def test_benchmark_pg_fast_digraph_pagerank(benchmark, large_graph_data):
    n, edges = large_graph_data
    g = FastDiGraph()
    for i in range(n):
        g.add_node(i)
    for u, v, w in edges:
        g.add_edge(u, v, w)

    def run():
        return g.page_rank(damping_factor=0.85, iterations=50)

    benchmark.pedantic(run, rounds=5, iterations=1)

# ════════════════════════════════════════════════════════════
# Memory Benchmark (More accurate with larger scale)
# ════════════════════════════════════════════════════════════

@pytest.mark.benchmark
def test_memory_usage_info():
    # Use 100,000 nodes and 1,000,000 edges for distinct memory measurement
    n = 100_000
    edge_count = 1_000_000
    import random
    rng = random.Random(42)
    edges = [
        (rng.randint(0, n - 1), rng.randint(0, n - 1), rng.uniform(0, 1))
        for _ in range(edge_count)
    ]

    import gc
    gc.collect()

    # NetworkX
    start_mem = get_process_memory()
    G = nx.DiGraph()
    G.add_weighted_edges_from(edges)
    nx_mem = get_process_memory() - start_mem
    print(f"\n[Memory] NetworkX ({n} nodes, {edge_count} edges): {nx_mem:.2f} MB")

    del G
    gc.collect()

    # pypetgraph FastDiGraph
    start_mem = get_process_memory()
    g = FastDiGraph()
    for i in range(n):
        g.add_node(i)
    for u, v, w in edges:
        g.add_edge(u, v, w)
    pg_mem = get_process_memory() - start_mem
    print(f"[Memory] pypetgraph FastDiGraph: {pg_mem:.2f} MB")

    reduction_pct = ((nx_mem - pg_mem) / nx_mem) * 100 if nx_mem > 0 else 0
    print(f"📊 Memory Reduction: {reduction_pct:.1f}%")

    # pypetgraph must use meaningfully less memory than NetworkX.
    # We conservatively require ≥50% reduction (README claims ~93%).
    assert pg_mem < nx_mem, (
        f"pypetgraph ({pg_mem:.1f}MB) must use less memory than NetworkX ({nx_mem:.1f}MB)"
    )
    assert reduction_pct >= 50, (
        f"Expected ≥50% memory reduction, got {reduction_pct:.1f}%"
    )
