import asyncio

import pytest

from pypetgraph import FastDiGraph


@pytest.mark.asyncio
async def test_async_parallel_dijkstra():
    # 构建一个简单的图
    g = FastDiGraph()
    n = 1000
    nodes = [g.add_node(i) for i in range(n)]
    for i in range(n - 1):
        g.add_edge(nodes[i], nodes[i + 1], 1.0)

    # 并行执行多个最短路径搜索任务
    # 每个任务都会在 asyncio.to_thread 中运行, 且 Rust 侧会释放 GIL
    tasks = [
        g.dijkstra_async(nodes[0]),
        g.dijkstra_async(nodes[100]),
        g.dijkstra_async(nodes[500]),
    ]

    results = await asyncio.gather(*tasks)

    assert len(results) == 3
    assert results[0][nodes[999]] == 999.0
    assert results[1][nodes[999]] == 899.0


@pytest.mark.asyncio
async def test_async_isomorphic():
    from pypetgraph import DiGraph, is_isomorphic_async

    g1 = DiGraph()
    g1.add_node(1)

    g2 = DiGraph()
    g2.add_node(2)

    res = await is_isomorphic_async(g1, g2)
    assert res is True
