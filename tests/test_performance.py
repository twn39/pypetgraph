import os

import psutil
import pytest

from pypetgraph import DiGraph, FastDiGraph


def get_process_memory():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)


@pytest.fixture
def graph_data():
    n = 2000
    edges = []
    for i in range(n):
        for j in range(1, 11):
            if i + j < n:
                edges.append((i, i + j, float(j)))
    return n, edges


def test_benchmark_digraph_py(benchmark, graph_data):
    n, edges = graph_data
    g = DiGraph()
    nodes = [g.add_node(i) for i in range(n)]
    for u, v, w in edges:
        g.add_edge(nodes[u], nodes[v], w)

    def run():
        return g.dijkstra(nodes[0])

    benchmark(run)


def test_benchmark_fast_digraph(benchmark, graph_data):
    n, edges = graph_data
    g = FastDiGraph()
    nodes = [g.add_node(i) for i in range(n)]
    for u, v, w in edges:
        g.add_edge(nodes[u], nodes[v], w)

    def run():
        return g.dijkstra(nodes[0])

    benchmark(run)
