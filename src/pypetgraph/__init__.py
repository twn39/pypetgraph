import asyncio

import numpy as np
import scipy.sparse as sp

from ._pypetgraph import (
    CsrGraph,
    DiGraph,
    FastDiGraph,
    IntDiGraphMap,
    IntGraphMap,
    MatrixDiGraph,
    StableDiGraph,
    UnGraph,
    UnionFind,
)
from ._pypetgraph import (
    is_isomorphic as _is_isomorphic_sync,
)

# --- Async Global Functions ---


async def is_isomorphic_async(g1, g2):
    return await asyncio.to_thread(_is_isomorphic_sync, g1, g2)


is_isomorphic = _is_isomorphic_sync


# --- SciPy PageRank Implementation ---

def _scipy_pagerank(graph, damping_factor=0.85, iterations=100, tol=1e-6):
    """
    Leverages SciPy sparse solvers to achieve $O(n|E|)$ complexity and NetworkX parity,
    avoiding the $O(n|V|^2|E|)$ bottleneck in the default petgraph 0.7 implementation.
    """
    n = graph.node_count
    if n == 0:
        return []

    u, v, weights = graph.to_scipy_coo()

    # Transition matrix M where PageRank x = dMx + (1-d)/N
    M = sp.coo_matrix((weights, (v, u)), shape=(n, n)).tocsr()

    out_degree = np.array(M.sum(axis=0)).flatten()
    out_degree[out_degree == 0] = 1.0

    M = M.dot(sp.diags(1.0 / out_degree))

    x = np.ones(n) / n

    for _ in range(iterations):
        x_last = x.copy()
        x = damping_factor * M.dot(x) + (1.0 - damping_factor) / n

        # Compensate for energy loss at dangling nodes to match NetworkX behavior
        error = 1.0 - x.sum()
        if error > 0:
            x += error / n

        if np.linalg.norm(x - x_last, ord=1) < tol:
            break

    return x.tolist()


def _patch_pagerank(cls):
    def page_rank(self, damping_factor=0.85, iterations=100, tol=1e-6):
        return _scipy_pagerank(self, damping_factor, iterations, tol)

    cls.page_rank = page_rank


_patch_pagerank(DiGraph)
_patch_pagerank(FastDiGraph)

# --- Async Extension Helper ---


def _add_async_methods(cls, methods):
    """Automatically adds thread-pool async wrappers for blocking Rust algorithms."""
    for method_name in methods:
        sync_method = getattr(cls, method_name, None)
        if sync_method:

            async def make_async(self, *args, _m=method_name, **kwargs):
                return await asyncio.to_thread(getattr(self, _m), *args, **kwargs)

            setattr(cls, f"{method_name}_async", make_async)


# --- Class Extensions ---

_add_async_methods(
    DiGraph,
    [
        "is_cyclic",
        "toposort",
        "dijkstra",
        "floyd_warshall",
        "k_shortest_path",
        "astar",
        "tarjan_scc",
        "kosaraju_scc",
        "all_simple_paths",
        "has_path_connecting",
        "page_rank",
    ],
)

_add_async_methods(
    FastDiGraph,
    [
        "dijkstra",
        "astar",
        "bellman_ford",
        "floyd_warshall",
        "is_cyclic",
        "toposort",
        "tarjan_scc",
        "all_simple_paths",
        "has_path_connecting",
        "page_rank",
    ],
)

_add_async_methods(MatrixDiGraph, ["dijkstra", "bellman_ford"])

_add_async_methods(CsrGraph, ["dijkstra", "bellman_ford", "floyd_warshall"])

_add_async_methods(
    UnGraph,
    ["connected_components", "has_path_connecting", "is_bipartite"],
)

__all__ = [
    "CsrGraph",
    "DiGraph",
    "FastDiGraph",
    "IntDiGraphMap",
    "IntGraphMap",
    "MatrixDiGraph",
    "StableDiGraph",
    "UnGraph",
    "UnionFind",
    "is_isomorphic",
    "is_isomorphic_async",
]
