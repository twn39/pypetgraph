import asyncio

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

# --- 异步全局函数 ---


async def is_isomorphic_async(g1, g2):
    """异步判断两个有向图是否同构 (释放 GIL)"""
    return await asyncio.to_thread(_is_isomorphic_sync, g1, g2)


# 重新导出同步版
is_isomorphic = _is_isomorphic_sync


# --- 辅助函数：为类动态添加异步方法 ---


def _add_async_methods(cls, methods):
    for method_name in methods:
        sync_method = getattr(cls, method_name, None)
        if sync_method:

            async def make_async(self, *args, _m=method_name, **kwargs):
                return await asyncio.to_thread(getattr(self, _m), *args, **kwargs)

            # 设置异步方法名，例如 dijkstra -> dijkstra_async
            setattr(cls, f"{method_name}_async", make_async)


# --- 扩展 DiGraph ---
_add_async_methods(
    DiGraph,
    [
        "is_cyclic",
        "toposort",
        "dijkstra",
        "astar",
        "tarjan_scc",
        "kosaraju_scc",
        "all_simple_paths",
        "has_path_connecting",
        "page_rank",
    ],
)

# --- 扩展 FastDiGraph ---
_add_async_methods(
    FastDiGraph,
    [
        "dijkstra",
        "astar",
        "bellman_ford",
        "is_cyclic",
        "toposort",
        "tarjan_scc",
        "all_simple_paths",
        "has_path_connecting",
        "page_rank",
    ],
)

# --- 扩展 MatrixDiGraph ---
_add_async_methods(MatrixDiGraph, ["dijkstra", "bellman_ford"])

# --- 扩展 CsrGraph ---
_add_async_methods(CsrGraph, ["dijkstra", "bellman_ford"])

# --- 扩展 UnGraph ---
_add_async_methods(
    UnGraph,
    ["connected_components", "has_path_connecting", "is_bipartite"],
)

__all__ = [
    "DiGraph",
    "FastDiGraph",
    "UnGraph",
    "StableDiGraph",
    "IntGraphMap",
    "IntDiGraphMap",
    "MatrixDiGraph",
    "CsrGraph",
    "UnionFind",
    "is_isomorphic",
    "is_isomorphic_async",
]
