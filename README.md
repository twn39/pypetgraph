# pypetgraph

`pypetgraph` 是 Rust 著名图计算库 [petgraph](https://github.com/petgraph/petgraph) 的 Python 高性能封装。它利用 PyO3 实现了近乎原生的 Rust 计算速度，支持在节点和边上存储任意 Python 对象，并针对多核并发进行了深度优化。

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
```

### 2. 高性能快速图 (FastDiGraph)
边权重固定为 Rust `f64`，计算时完全释放 GIL，适合极致性能需求。

```python
from pypetgraph import FastDiGraph

g = FastDiGraph()
# ... 构建图 ...
# 异步计算最短路径，不阻塞事件循环，且支持多核并行
distances = await g.dijkstra_async(start_node)
```

### 3. 内存优化图 (CsrGraph)
使用压缩稀疏行格式，内存占用极低，适合存储百万级节点的静态稀疏图。

```python
from pypetgraph import CsrGraph

# (node_count, edges_list)
edges = [(0, 1, 1.0), (1, 2, 2.5)]
g = CsrGraph.from_edges(3, edges)
```

---

## API 概览

### 核心图类

| 类名 | 存储模式 | 节点权重 | 边权重 | 适用场景 |
| :--- | :--- | :--- | :--- | :--- |
| `DiGraph` | 邻接列表 | `Any` | `Any` | 通用有向图 |
| `UnGraph` | 邻接列表 | `Any` | `Any` | 通用无向图 |
| `FastDiGraph` | 邻接列表 | `Any` | `f64` | **最高算法性能** |
| `MatrixDiGraph`| 邻接矩阵 | `Any` | `f64` | 密集图 |
| `CsrGraph` | CSR (压缩) | 无 | `f64` | **极低内存占用** |
| `IntGraphMap` | 哈希表 | `int` | `Any` | 整数节点，高效增删 |
| `StableDiGraph`| 稳定列表 | `Any` | `Any` | 支持删除节点且索引不位移 |

### 支持算法 (均提供 `_async` 版本)

- **路径规划**: `dijkstra`, `astar`, `all_simple_paths`
- **结构分析**: `toposort`, `is_cyclic`, `tarjan_scc`, `connected_components`
- **图同构**: `is_isomorphic` (全局函数)
- **可视化**: `to_dot()`

---

## 性能表现 (Benchmark)

在 2000 节点、20,000 边的 Dijkstra 算法基准测试中：
- **`pypetgraph`**: ~0.5ms (均值)
- **内存占用**: 10,000 个节点仅需约 3.6 MB。
- **并发能力**: 支持 10+ 线程同时进行图计算而无 GIL 竞争开销。

---

## 开发与测试

```bash
uv run ruff check .        # Lint 检查
uv run ty check           # 静态类型检查
uv run pytest             # 执行单元测试
uv run pytest tests/test_performance.py -s  # 运行性能基准测试
```

---

## 许可证

本项目采用 [MIT 许可证](LICENSE)。
