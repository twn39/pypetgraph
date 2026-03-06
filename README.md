<div align="center">

# 🦀 pypetgraph

`pypetgraph` 是基于 Rust 著名图计算库 [petgraph](https://github.com/petgraph/petgraph) 的 Python 高性能封装。它利用 PyO3 实现了近乎原生的 Rust 计算速度，支持在节点和边上存储任意 Python 对象，并针对多核并发和异步 IO 进行了深度优化。

[![PyPI Version](https://img.shields.io/pypi/v/pypetgraph.svg)](https://pypi.org/project/pypetgraph/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/pypetgraph.svg)](https://pypi.org/project/pypetgraph/)
[![Build Status](https://github.com/twn39/pypetgraph/actions/workflows/build.yml/badge.svg)](https://github.com/twn39/pypetgraph/actions)
[![codecov](https://codecov.io/gh/twn39/pypetgraph/branch/main/graph/badge.svg)](https://codecov.io/gh/twn39/pypetgraph)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Rust](https://img.shields.io/badge/rust-1.70+-orange.svg)](https://www.rust-lang.org/)

📖 **[详细 API 参阅文档 →](docs/api.md)**

</div>

---

## ✨ 核心特性

- **极致性能**：核心逻辑由 Rust 编写，比 NetworkX 等纯 Python 库快 10-100 倍。
- **内存高效**：提供专门的 `FastDiGraph`（固定边权）和 `CsrGraph`（压缩存储）以应对大规模数据。
- **并发友好**：重型算法在执行时会**释放 GIL**，支持真正的 Python 多线程并行计算。
- **异步原生**：所有耗时算法均内置 `_async` 版本，无缝集成 `asyncio`。
- **多种结构**：支持邻接列表、邻接矩阵、CSR 压缩格式以及基于哈希的 `GraphMap`。
- **类型安全**：提供完整的 `.pyi` 类型提示文件，支持现代 IDE 的自动补全与静态检查。

---

## 🛠 安装 (Installation)

### 1. 使用 pip (Standard)
你可以直接通过 PyPI 安装已发布的预编译版本：

```bash
pip install pypetgraph
```

### 2. 使用 uv (Modern)
推荐使用现代高性能工具 [uv](https://github.com/astral-sh/uv)：

```bash
uv add pypetgraph
```

### 3. 从源码构建 (Development)
如果你需要最新的开发版本，可以从源码本地编译：

```bash
git clone https://github.com/twn39/pypetgraph
cd pypetgraph
uv run maturin develop --release
```

---

## 🚀 快速上手

### 1. 通用图 (DiGraph)
支持挂载任何 Python 对象（字典、自定义类、字符串等）。

```python
from pypetgraph import DiGraph

g = DiGraph()
n0 = g.add_node({"name": "Beijing", "type": "city"})
n1 = g.add_node({"name": "Shanghai", "type": "city"})
g.add_edge(n0, n1, {"distance": 1200, "traffic": "heavy"})

# 结构化分析
print(f"Has cycle: {g.is_cyclic()}")
print(f"SCCs: {g.tarjan_scc()}")
```

### 2. 异步计算
利用 `_async` 方法，在不阻塞事件循环的情况下执行复杂图计算：

```python
import asyncio
from pypetgraph import FastDiGraph

async def main():
    g = FastDiGraph.from_edges([(0, 1, 1.0), (1, 2, 2.0), (0, 2, 5.0)])
    
    # 异步计算全源最短路径
    result = await g.floyd_warshall_async()
    print(f"Shortest path 0->2: {result[0][2]}") # 输出 3.0

asyncio.run(main())
```

---

## 🗺 API 概览

### 核心图类

| 类名 | 特性 | 权重类型 | 最佳场景 |
| :--- | :--- | :---: | :--- |
| **`DiGraph`** | 有向邻接列表 | `Any` | 通用有向图，需要存储复杂对象 |
| **`UnGraph`** | 无向邻接列表 | `Any` | 通用无向图 |
| **`FastDiGraph`** | 数值优化图 | `f64` | **最高算法性能**，纯数值计算 |
| **`StableDiGraph`**| 索引稳定图 | `Any` | 频繁删除节点但需保持原有索引不变 |
| **`IntGraphMap`** | 整数哈希图 | `Any` | 节点 ID 为离散整数的极简结构 |
| **`MatrixDiGraph`**| 邻接矩阵 | `f64` | 密集图 (Dense Graph) |
| **`CsrGraph`** | 压缩稀疏行 | `f64` | **海量节点**的只读静态图 |

### 支持算法

| 类别 | 算法 | 特性 |
| :--- | :--- | :--- |
| **最短路径** | `dijkstra`, `astar`, `floyd_warshall`, `k_shortest_path` | 支持 `_async`，完全释放 GIL |
| **负权处理** | `bellman_ford` | 仅限 `FastDiGraph`, `MatrixDiGraph`, `CsrGraph` |
| **遍历** | `bfs`, `dfs` | 高效迭代器实现 |
| **连通性** | `tarjan_scc`, `kosaraju_scc`, `connected_components` | 强连通分量与弱连通分量 |
| **拓扑分析** | `toposort`, `is_cyclic`, `is_bipartite`, `is_isomorphic` | 结构完整性检查 |
| **重要度** | `page_rank` | 用于节点排名与重要性评估 |

---

## 📈 性能表现 (Benchmarks)

在处理大规模图数据时，`pypetgraph` 相比纯 Python 实现（如 NetworkX）具有压倒性优势。

### 1. 内存占用对比
在存储 **10 万节点** 和 **100 万条边** 的随机图时：

| 库 | 内存占用 | 节省 |
| :--- | :--- | :--- |
| **NetworkX** | ~318.5 MB | - |
| **pypetgraph (FastDiGraph)** | **~20.7 MB** | **93.5%** 📉 |

### 2. 算法速度对比
基于 5000 节点、5 万边的中型图测试：

| 算法 | NetworkX | pypetgraph | 提升 |
| :--- | :--- | :--- | :--- |
| **Dijkstra** (最短路径) | ~6.3 ms | **~0.9 ms** | **7x** 🚀 |
| **PageRank** (50次迭代) | ~19.5 ms | **~17.5 ms** | **等同/略快** |
| **SCC** (强连通分量) | 较慢 | **极快** | **10x+** |

---

## 🧪 开发与测试

```bash
uv run pytest                      # 运行所有测试 (包含 sync/async)
uv run pytest tests/test_performance.py -s  # 运行性能基准测试
uv run ruff check .                # 代码风格检查
```

---

## 许可证

本项目采用 [MIT 许可证](LICENSE)。
