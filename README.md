# pypetgraph

`pypetgraph` 是 Rust 著名图计算库 [petgraph](https://github.com/petgraph/petgraph) 的 Python 高性能封装。它利用 PyO3 实现了近乎原生的 Rust 计算速度，支持在节点和边上存储任意 Python 对象，并针对多核并发进行了深度优化。

📖 **[完整 API 文档 →](docs/api.md)**

---

## 核心特性

- **极致性能**：比 NetworkX 等纯 Python 库快 10-100 倍。
- **多种图结构**：支持邻接列表、邻接矩阵、CSR 压缩存储及哈希图。
- **并发友好**：结构化算法在执行时会**释放 GIL**，支持真正的多线程并行。
- **异步原生**：每个核心算法均内置 `_async` 版本，基于 `asyncio.to_thread` 实现。
- **类型安全**：提供完善的 `.pyi` 存根文件，支持 IDE 补全与静态检查。

---

## 安装

由于目前处于本地开发阶段，请通过以下方式安装：

```bash
git clone https://github.com/twn39/pypetgraph
cd pypetgraph
uv run maturin develop --release
```

---

## 快速上手

### 1. 通用有向图 (DiGraph)
支持在节点和边上挂载任何 Python 对象（如字典、对象、字符串）。

```python
from pypetgraph import DiGraph

g = DiGraph()
n0 = g.add_node({"id": "A", "label": "Start"})
n1 = g.add_node({"id": "B", "label": "End"})
g.add_edge(n0, n1, "weight_is_any_object")

print(f"Toposort: {g.toposort()}")
print(f"PageRank: {g.page_rank()}")
print(g.to_dot())
```

### 2. 高性能快速图 (FastDiGraph)
边权重固定为 Rust `f64`，计算时完全释放 GIL，适合极致性能需求。

```python
from pypetgraph import FastDiGraph

g = FastDiGraph()
# ... 构建图 ...
# 异步计算最短路径，不阻塞事件循环，且支持多核并行
distances = await g.dijkstra_async(start_node)
# Bellman-Ford 支持负权边
distances = g.bellman_ford(start_node)
```

### 3. 内存优化图 (CsrGraph)
使用压缩稀疏行格式，内存占用极低，适合存储百万级节点的静态稀疏图。

```python
from pypetgraph import CsrGraph

# (node_count, edges_list, sorted=False)
edges = [(0, 1, 1.0), (1, 2, 2.5)]
g = CsrGraph.from_edges(3, edges)
```

### 4. 批量构建

```python
from pypetgraph import DiGraph

# 自动推断节点数量
g = DiGraph.from_edges([(0, 1, 1.0), (1, 2, 2.0), (2, 3, 3.0)])

# 预分配容量构建
g = DiGraph(nodes=1000, edges=5000)
```

---

## API 概览

### 核心图类

| 类名 | 存储模式 | 节点权重 | 边权重 | 适用场景 |
| :--- | :--- | :--- | :--- | :--- |
| `DiGraph` | 邻接列表 | `Any` | `Any` | **通用有向图** |
| `UnGraph` | 邻接列表 | `Any` | `Any` | **通用无向图** |
| `FastDiGraph` | 邻接列表 | `Any` | `f64` | **最高算法性能** |
| `MatrixDiGraph`| 邻接矩阵 | `Any` | `f64` | 密集图 |
| `CsrGraph` | CSR (压缩) | 无 | `f64` | **极低内存占用** |
| `IntGraphMap` | 哈希表 | `int` | `Any` | 整数节点无向图 |
| `IntDiGraphMap` | 哈希表 | `int` | `Any` | 整数节点有向图 |
| `StableDiGraph`| 稳定列表 | `Any` | `Any` | 删除节点后索引不位移 |
| `UnionFind` | 并查集 | — | — | 连通分量/等价类管理 |

### 通用方法

所有图类型均支持以下方法（部分类型因结构限制可能不完全支持）：

| 类别 | 方法 |
| :--- | :--- |
| **构造** | `__init__()`, `from_edges()`, `with_capacity` |
| **节点操作** | `add_node()`, `remove_node()`, `node_weight()`, `node_count`, `node_indices()` |
| **边操作** | `add_edge()`, `remove_edge()`, `update_edge()`, `edge_weight()`, `find_edge()`, `edge_count`, `edge_indices()` |
| **查询** | `neighbors()`, `out_degree()`, `in_degree()`, `is_directed` |
| **图操作** | `clear()`, `clear_edges()`, `reverse()` |
| **Python 协议** | `__repr__()`, `__len__()`, `__bool__()`, `__contains__()` |
| **输出** | `to_dot()` |

### 支持算法

所有 CPU 密集型算法均**释放 GIL**，并提供 `_async` 版本。

| 类别 | 算法 | 可用图类型 |
| :--- | :--- | :--- |
| **最短路径** | `dijkstra` | DiGraph, FastDiGraph, MatrixDiGraph, CsrGraph, IntDiGraphMap |
| | `astar` | DiGraph, FastDiGraph |
| | `bellman_ford` (支持负权) | FastDiGraph, MatrixDiGraph, CsrGraph |
| **遍历** | `bfs`, `dfs` | DiGraph, FastDiGraph, UnGraph |
| **连通性** | `has_path_connecting` | DiGraph, FastDiGraph, UnGraph |
| | `connected_components` | UnGraph |
| | `is_bipartite` | UnGraph |
| **结构分析** | `toposort` | DiGraph, FastDiGraph |
| | `is_cyclic` | DiGraph, FastDiGraph |
| | `tarjan_scc` | DiGraph, FastDiGraph |
| | `kosaraju_scc` | DiGraph |
| | `all_simple_paths` | DiGraph, FastDiGraph |
| **排名** | `page_rank` | DiGraph, FastDiGraph |
| **图同构** | `is_isomorphic` | DiGraph (全局函数) |

### UnionFind (并查集)

```python
from pypetgraph import UnionFind

uf = UnionFind(10)       # 10 个元素
uf.union(0, 1)           # 合并集合
uf.find(0)               # 查找代表元
uf.equiv(0, 1)           # 是否同组 → True
labels = uf.into_labeling()  # 获取所有元素的组标签
```

### 异步支持

每个核心算法都提供 `_async` 版本，基于 `asyncio.to_thread` 实现，适合在异步框架中使用：

```python
import asyncio
from pypetgraph import FastDiGraph

async def main():
    g = FastDiGraph()
    # ... 构建大图 ...

    # 并行计算多个最短路径，完全释放 GIL
    tasks = [
        g.dijkstra_async(0),
        g.dijkstra_async(100),
        g.dijkstra_async(500),
    ]
    results = await asyncio.gather(*tasks)
```

---

## 性能表现 (Benchmark)

在 2000 节点、20,000 边的 Dijkstra 算法基准测试中：
- **`pypetgraph`**: ~0.5ms (均值)
- **内存占用**: 10,000 个节点仅需约 3.6 MB。
- **并发能力**: 支持 10+ 线程同时进行图计算而无 GIL 竞争开销。

---

## 开发与测试

```bash
uv run ruff check .               # Lint 检查
uv run ty check                    # 静态类型检查
uv run pytest                      # 执行单元测试 (161 tests)
uv run pytest --cov=pypetgraph     # 覆盖率测试
uv run pytest tests/test_performance.py -s  # 运行性能基准测试
```

---

## 许可证

本项目采用 [MIT 许可证](LICENSE)。
