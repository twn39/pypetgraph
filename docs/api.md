# pypetgraph API Reference

> 完整的 API 函数文档，包含签名、参数说明、返回值及示例。

---

## 目录

- [DiGraph](#digraph)
- [UnGraph](#ungraph)
- [FastDiGraph](#fastdigraph)
- [StableDiGraph](#stabledigraph)
- [IntGraphMap](#intgraphmap)
- [IntDiGraphMap](#intdigraphmap)
- [MatrixDiGraph](#matrixdigraph)
- [CsrGraph](#csrgraph)
- [UnionFind](#unionfind)
- [全局函数](#全局函数)

---

## DiGraph

通用有向图。节点和边权重可为任意 Python 对象。底层采用邻接列表存储，支持快速的节点/边增删和常用图算法。

```python
from pypetgraph import DiGraph
```

### 构造方法

---

#### `__init__(nodes=0, edges=0)`

创建一个预分配容量的空有向图。

| 参数 | 类型 | 说明 |
| :--- | :--- | :--- |
| `nodes` | `int` | 预分配节点槽位数（优化内存，不限制上限） |
| `edges` | `int` | 预分配边槽位数 |

**返回值**：`DiGraph`

```python
g = DiGraph()            # 空图
g = DiGraph(100, 500)    # 预分配 100 节点 / 500 边
```

---

#### `from_edges(edges, node_count=None)` *(static)*

从边列表批量构建有向图，节点以整数 0..n-1 作为索引，节点权重自动初始化为其索引值。

| 参数 | 类型 | 说明 |
| :--- | :--- | :--- |
| `edges` | `list[tuple[int, int, Any]]` | 边列表，每个元素为 `(源节点, 目标节点, 权重)` |
| `node_count` | `int \| None` | 节点数量；若为 `None` 则自动从边推断 |

**返回值**：`DiGraph`

```python
g = DiGraph.from_edges([(0, 1, 1.0), (1, 2, 2.0)])
g = DiGraph.from_edges([(0, 1, "ab")], node_count=5)  # 共 5 个节点
```

---

### 节点操作

---

#### `add_node(weight) -> int`

向图中添加一个节点。

| 参数 | 类型 | 说明 |
| :--- | :--- | :--- |
| `weight` | `Any` | 节点权重（可为任意 Python 对象） |

**返回值**：`int` — 新节点的索引

```python
n0 = g.add_node("Start")
n1 = g.add_node({"id": 42})
```

---

#### `remove_node(index) -> Any | None`

删除指定节点及其所有关联边。

> ⚠️ **注意**：`DiGraph` 使用数组存储，删除节点时末节点会**填充被删除位置**（索引发生偏移）。若需稳定索引，请使用 `StableDiGraph`。

| 参数 | 类型 | 说明 |
| :--- | :--- | :--- |
| `index` | `int` | 要删除的节点索引 |

**返回值**：`Any | None` — 被删节点的权重；索引不存在时返回 `None`

```python
weight = g.remove_node(0)  # 删除节点 0，返回其权重
```

---

#### `node_weight(index) -> Any | None`

获取指定节点的权重。

| 参数 | 类型 | 说明 |
| :--- | :--- | :--- |
| `index` | `int` | 节点索引 |

**返回值**：`Any | None` — 节点权重；不存在时返回 `None`

---

#### `node_indices() -> list[int]`

返回图中所有有效节点的索引列表。

**返回值**：`list[int]`

---

#### `node_count` *(property)*

图中当前节点数量。

**返回值**：`int`

---

### 边操作

---

#### `add_edge(u, v, weight) -> int`

在节点 `u` 和 `v` 之间添加一条有向边。

| 参数 | 类型 | 说明 |
| :--- | :--- | :--- |
| `u` | `int` | 源节点索引 |
| `v` | `int` | 目标节点索引 |
| `weight` | `Any` | 边权重 |

**返回值**：`int` — 新边的索引  
**异常**：`IndexError` — 若 `u` 或 `v` 不存在

```python
e = g.add_edge(0, 1, 1.5)
e = g.add_edge(0, 1, {"cost": 10, "label": "road"})
```

---

#### `update_edge(u, v, weight) -> int`

若 `u→v` 边已存在则更新其权重；否则添加新边。

| 参数 | 类型 | 说明 |
| :--- | :--- | :--- |
| `u` | `int` | 源节点索引 |
| `v` | `int` | 目标节点索引 |
| `weight` | `Any` | 新的边权重 |

**返回值**：`int` — 边的索引（新建或已有）

---

#### `remove_edge(index) -> Any | None`

按边索引删除一条边。

| 参数 | 类型 | 说明 |
| :--- | :--- | :--- |
| `index` | `int` | 边的索引 |

**返回值**：`Any | None` — 被删边的权重；不存在时返回 `None`

---

#### `edge_weight(index) -> Any | None`

按边索引获取权重。

| 参数 | 类型 | 说明 |
| :--- | :--- | :--- |
| `index` | `int` | 边的索引 |

**返回值**：`Any | None`

---

#### `find_edge(u, v) -> int | None`

查找从 `u` 到 `v` 的边，返回其索引。

| 参数 | 类型 | 说明 |
| :--- | :--- | :--- |
| `u` | `int` | 源节点索引 |
| `v` | `int` | 目标节点索引 |

**返回值**：`int | None` — 边索引；不存在时返回 `None`

---

#### `edge_indices() -> list[int]`

返回图中所有有效边的索引列表。

**返回值**：`list[int]`

---

#### `edge_count` *(property)*

图中当前边数量。

**返回值**：`int`

---

### 图结构操作

---

#### `clear()`

清空图的所有节点和边。

---

#### `clear_edges()`

仅清空所有边，保留节点。

---

#### `reverse()`

**原地**反转所有边的方向（`u→v` 变为 `v→u`）。

---

### 查询方法

---

#### `neighbors(index) -> list[int]`

返回节点 `index` 的直接后继节点（出边邻居）索引列表。

| 参数 | 类型 | 说明 |
| :--- | :--- | :--- |
| `index` | `int` | 节点索引 |

**返回值**：`list[int]`

---

#### `out_degree(index) -> int`

返回节点的出度（出边数量）。

**返回值**：`int`

---

#### `in_degree(index) -> int`

返回节点的入度（入边数量）。

**返回值**：`int`

---

#### `is_directed` *(property)*

始终返回 `True`。

**返回值**：`bool`

---

### 遍历

---

#### `bfs(start) -> list[int]`

从 `start` 节点出发进行广度优先搜索，返回**可达节点**的访问顺序。

| 参数 | 类型 | 说明 |
| :--- | :--- | :--- |
| `start` | `int` | 起始节点索引 |

**返回值**：`list[int]` — 按访问顺序排列的节点索引列表

```python
order = g.bfs(0)  # [0, 1, 2, ...]
```

---

#### `dfs(start) -> list[int]`

从 `start` 节点出发进行深度优先搜索，返回**可达节点**的访问顺序。

| 参数 | 类型 | 说明 |
| :--- | :--- | :--- |
| `start` | `int` | 起始节点索引 |

**返回值**：`list[int]`

---

### 算法

所有算法在计算期间均**释放 Python GIL**，可与其他线程并发执行。每个方法均提供 `_async` 异步版本。

---

#### `dijkstra(start) -> dict[int, float]`

Dijkstra 单源最短路径算法。边权重须可转换为 `float`，不支持负权边。

| 参数 | 类型 | 说明 |
| :--- | :--- | :--- |
| `start` | `int` | 起始节点索引 |

**返回值**：`dict[int, float]` — `{节点索引: 最短距离}`，仅包含可达节点  
**异常**：
- `IndexError` — 若 `start` 节点不存在
- `ValueError` — 若某条边的权重无法转换为 `float`

```python
distances = g.dijkstra(0)
# {0: 0.0, 1: 1.0, 2: 3.0}
```

---

#### `astar(start, goal, heuristic_fn) -> tuple[float, list[int]] | None`

A* 启发式最短路径算法。边权重须可转换为 `float`。

| 参数 | 类型 | 说明 |
| :--- | :--- | :--- |
| `start` | `int` | 起始节点索引 |
| `goal` | `int` | 目标节点索引 |
| `heuristic_fn` | `Callable[[int], float]` | 启发函数，接受节点索引，返回到终点的估算距离 |

**返回值**：`tuple[float, list[int]] | None` — `(路径总代价, 路径节点列表)`；无路径时返回 `None`  
**异常**：`IndexError` — 若节点不存在

```python
def h(node):
    return abs(node - goal)  # 简单启发

result = g.astar(0, 5, h)
if result:
    cost, path = result
    print(f"Cost: {cost}, Path: {path}")
```

---

#### `is_cyclic() -> bool`

判断有向图中是否存在**环**（使用 DFS）。

**返回值**：`bool` — `True` 表示存在环

---

#### `toposort() -> list[int]`

对 DAG（有向无环图）进行拓扑排序。

**返回值**：`list[int]` — 拓扑序节点索引列表  
**异常**：`ValueError` — 若图中存在环（非 DAG）

```python
order = g.toposort()  # [0, 1, 3, 2, ...]
```

---

#### `tarjan_scc() -> list[list[int]]`

Tarjan 算法求所有**强连通分量**（SCC）。

**返回值**：`list[list[int]]` — SCC 列表，每个 SCC 为节点索引列表；按逆拓扑序排列（有向图的 DAG 缩合顺序）

```python
sccs = g.tarjan_scc()
# [[2, 1, 0], [3]]  各 SCC 内节点集合
```

---

#### `kosaraju_scc() -> list[list[int]]`

Kosaraju 算法求所有**强连通分量**（SCC）。与 `tarjan_scc` 语义相同，可互换使用。

**返回值**：`list[list[int]]`

---

#### `has_path_connecting(from_node, to_node) -> bool`

判断从 `from_node` 是否存在路径可达 `to_node`（DFS 实现）。

| 参数 | 类型 | 说明 |
| :--- | :--- | :--- |
| `from_node` | `int` | 起始节点索引 |
| `to_node` | `int` | 目标节点索引 |

**返回值**：`bool`

---

#### `all_simple_paths(from_node, to_node, min_intermediate_nodes=0, max_intermediate_nodes=None) -> list[list[int]]`

枚举从 `from_node` 到 `to_node` 之间的所有**简单路径**（无重复节点）。

| 参数 | 类型 | 说明 |
| :--- | :--- | :--- |
| `from_node` | `int` | 起始节点索引 |
| `to_node` | `int` | 目标节点索引 |
| `min_intermediate_nodes` | `int` | 路径中间节点最少数量（默认 0） |
| `max_intermediate_nodes` | `int \| None` | 路径中间节点最多数量；`None` 表示无限制 |

**返回值**：`list[list[int]]` — 每条路径为节点索引列表（含起止节点）  
**异常**：`IndexError` — 若节点不存在

> ⚠️ 当图较大时，路径数可能呈指数级增长，建议配合 `max_intermediate_nodes` 限制。

---

#### `page_rank(damping_factor=0.85, iterations=100) -> list[float]`

计算图中所有节点的 **PageRank** 值（归一化，总和为 1.0）。

| 参数 | 类型 | 说明 |
| :--- | :--- | :--- |
| `damping_factor` | `float` | 阻尼系数（通常取 0.85） |
| `iterations` | `int` | 迭代次数（越多越精确） |

**返回值**：`list[float]` — 索引 `i` 对应节点 `i` 的 PageRank 值

```python
ranks = g.page_rank(0.85, 100)
top = sorted(enumerate(ranks), key=lambda x: -x[1])
print("Most important nodes:", top[:5])
```

---

### 输出

---

#### `to_dot() -> str`

将图序列化为 [Graphviz DOT](https://graphviz.org/) 格式字符串。

**返回值**：`str` — DOT 格式文本，可直接传给 Graphviz 渲染

```python
dot_str = g.to_dot()
# digraph {
#     0 [ label = "A" ]
#     1 [ label = "B" ]
#     0 -> 1 [ label = "1.5" ]
# }

# 配合 graphviz 库渲染：
# import graphviz
# graphviz.Source(dot_str).view()
```

---

### Python 协议

---

#### `__repr__() -> str`

返回图的简洁字符串表示。

```python
repr(g)  # "DiGraph(nodes=3, edges=2)"
```

---

#### `__len__() -> int`

等价于 `node_count`。

```python
len(g)  # 3
```

---

#### `__bool__() -> bool`

节点数 > 0 时为 `True`。

```python
if g:
    print("Non-empty graph")
```

---

#### `__contains__(index) -> bool`

判断节点索引是否有效（即节点存在）。

```python
0 in g   # True
99 in g  # False
```

---

## UnGraph

通用无向图。与 `DiGraph` 共享大部分 API，以下仅列出差异。

```python
from pypetgraph import UnGraph
```

---

#### `degree(index) -> int`

返回节点的度数（无向图中入度 = 出度 = 所有邻边数）。

---

#### `connected_components() -> int`

返回图中**连通分量**的数量（使用 Union-Find 实现，GIL 释放）。

**返回值**：`int`

```python
g = UnGraph()
g.add_node(0); g.add_node(1); g.add_node(2)
g.add_edge(0, 1, 1.0)
print(g.connected_components())  # 2（节点 2 孤立）
```

---

#### `is_bipartite(start) -> bool`

从 `start` 节点出发，**二着色法**判断图是否为二分图。

| 参数 | 类型 | 说明 |
| :--- | :--- | :--- |
| `start` | `int` | 起始节点索引 |

**返回值**：`bool` — `True` 表示可二着色（二分图）

```python
# K2,2 是二分图
g.is_bipartite(0)  # True

# 奇数环（三角形）不是二分图
g.is_bipartite(0)  # False
```

---

## FastDiGraph

高性能有向图。边权重固定为 Rust `f64`，所有算法均完全释放 GIL，适合 CPU 密集型计算。

```python
from pypetgraph import FastDiGraph
```

**与 `DiGraph` 的主要区别**：
- `add_edge(u, v, weight: float)` — 边权重必须为数值
- 额外支持 `bellman_ford`（因为边权已是 f64，无需 GIL 提取）
- 所有算法完全 GIL-free，并发效率更高

---

#### `bellman_ford(start) -> dict[int, float]`

Bellman-Ford 单源最短路径算法。支持**负权边**，检测**负权环**。

| 参数 | 类型 | 说明 |
| :--- | :--- | :--- |
| `start` | `int` | 起始节点索引 |

**返回值**：`dict[int, float]` — `{节点索引: 最短距离}` （包含所有节点，不可达时为 `inf`）  
**异常**：
- `IndexError` — 若 `start` 不存在
- `ValueError` — 若图中包含**负权环**（"Negative cycle detected"）

```python
g = FastDiGraph()
g.add_node(0); g.add_node(1)
g.add_edge(0, 1, -5.0)  # 负权边合法
distances = g.bellman_ford(0)
# {0: 0.0, 1: -5.0}
```

---

## StableDiGraph

**稳定索引**有向图。删除节点后，其他节点的索引**不发生偏移**，适合需要长期持有节点引用的场景。

```python
from pypetgraph import StableDiGraph
```

**与 `DiGraph` 的区别**：
- 节点删除后，所有其他节点的索引保持不变（索引空洞用内部标记管理）
- `contains_node(index)` 可用于检查某索引是否仍有效
- 不支持 `from_edges` 静态方法（尚未实现）

---

#### `contains_node(index) -> bool`

判断指定索引的节点是否仍存在（未被删除）。

| 参数 | 类型 | 说明 |
| :--- | :--- | :--- |
| `index` | `int` | 节点索引 |

**返回值**：`bool`

```python
n0 = g.add_node("A")  # 0
n1 = g.add_node("B")  # 1
n2 = g.add_node("C")  # 2
g.remove_node(n1)
g.contains_node(n0)  # True  — 稳定
g.contains_node(n1)  # False — 已删除
g.contains_node(n2)  # True  — 稳定（索引未变！）
```

---

## IntGraphMap

以 **`int` 为节点键**的无向哈希图（底层 `GraphMap`）。节点键即为"地址"，无额外节点权重槽位，适合以整数 ID 作节点的场景。

```python
from pypetgraph import IntGraphMap
```

---

#### `add_node(node)`

添加整数节点。若节点已存在则无操作。

| 参数 | 类型 | 说明 |
| :--- | :--- | :--- |
| `node` | `int` | 节点键（任意 `i32` 范围整数） |

---

#### `remove_node(node) -> bool`

删除整数节点及其所有相邻边。

**返回值**：`bool` — `True` 表示成功删除，`False` 表示节点不存在

---

#### `add_edge(u, v, weight)`

在整数节点 `u` 和 `v` 之间添加无向边（若节点不存在则自动创建）。

| 参数 | 类型 | 说明 |
| :--- | :--- | :--- |
| `u`, `v` | `int` | 节点键 |
| `weight` | `Any` | 边权重 |

---

#### `remove_edge(u, v) -> Any | None`

删除 `u` 和 `v` 之间的边。

**返回值**：`Any | None` — 被删边的权重；不存在时返回 `None`

---

#### `contains_node(node) -> bool` / `contains_edge(u, v) -> bool`

节点/边存在性检查。

---

#### `neighbors(node) -> list[int]`

返回节点的所有邻居节点键列表。

---

#### `degree(node) -> int`

返回节点的度数。

---

#### `all_nodes() -> list[int]`

返回图中所有节点键的列表。

---

#### `all_edges() -> list[tuple[int, int, Any]]`

返回图中所有边的列表，每项为 `(u, v, weight)`。

---

## IntDiGraphMap

以 **`int` 为节点键**的有向哈希图。

```python
from pypetgraph import IntDiGraphMap
```

与 `IntGraphMap` 接口相同，额外提供：

#### `out_degree(node) -> int` / `in_degree(node) -> int`

返回节点的出度 / 入度。

---

#### `dijkstra(start) -> dict[int, float]`

Dijkstra 算法，边权重须可转换为 `float`。

| 参数 | 类型 | 说明 |
| :--- | :--- | :--- |
| `start` | `int` | 起始节点键（`int`，非索引） |

**返回值**：`dict[int, float]` — `{节点键: 最短距离}`  
**异常**：`IndexError` — 若 `start` 节点不存在

---

## MatrixDiGraph

以**邻接矩阵**存储的有向图，查询任意两节点间边的时间复杂度为 O(1)。边权重固定为 `f64`，适合**密集图**。

```python
from pypetgraph import MatrixDiGraph
```

---

#### `has_edge(u, v) -> bool`

O(1) 查询两节点之间是否存在有向边。

**返回值**：`bool`

---

#### `remove_edge(u, v) -> bool`

删除 `u→v` 的有向边。

**返回值**：`bool` — `True` 表示成功，`False` 表示边不存在

---

#### `bellman_ford(start) -> dict[int, float]`

同 `FastDiGraph.bellman_ford`，支持负权边，检测负权环。

---

## CsrGraph

**压缩稀疏行**（Compressed Sparse Row）格式有向图。存储效率极高，适合百万节点的**大型稀疏静态图**。

> ⚠️ CSR 图为**静态图**，一经构建无法增删节点/边。

```python
from pypetgraph import CsrGraph
```

---

#### `from_edges(node_count, edges, sorted=False)` *(static)*

从边列表构建 CSR 图。

| 参数 | 类型 | 说明 |
| :--- | :--- | :--- |
| `node_count` | `int` | 节点总数 |
| `edges` | `list[tuple[int, int, float]]` | 边列表：`(源 u32, 目标 u32, 权重 f64)` |
| `sorted` | `bool` | 若输入边已按源节点排序，设为 `True` 可跳过排序，提升性能 |

**返回值**：`CsrGraph`

```python
g = CsrGraph.from_edges(1_000_000, edges, sorted=True)
```

---

#### `dijkstra(start) -> dict[int, float]`

同 `FastDiGraph.dijkstra`，GIL-free 执行。

---

#### `bellman_ford(start) -> dict[int, float]`

同 `FastDiGraph.bellman_ford`，支持负权边。

---

## UnionFind

**并查集**数据结构，支持高效的集合合并（Union）与查询（Find）操作，路径压缩与按秩合并优化，均摊近 O(1)。

```python
from pypetgraph import UnionFind
```

---

#### `__init__(n)`

创建含 `n` 个独立元素（编号 `0..n-1`）的并查集。

| 参数 | 类型 | 说明 |
| :--- | :--- | :--- |
| `n` | `int` | 元素总数 |

---

#### `find(i) -> int`

查找元素 `i` 所属集合的代表元（根节点），执行路径压缩。

| 参数 | 类型 | 说明 |
| :--- | :--- | :--- |
| `i` | `int` | 元素索引（`0..n-1`） |

**返回值**：`int` — 代表元索引

---

#### `union(i, j) -> bool`

合并元素 `i` 和 `j` 所属的集合。

| 参数 | 类型 | 说明 |
| :--- | :--- | :--- |
| `i`, `j` | `int` | 元素索引 |

**返回值**：`bool` — `True` 表示执行了合并（原本不同组），`False` 表示已在同一组

---

#### `equiv(i, j) -> bool`

判断元素 `i` 和 `j` 是否在同一集合中（即 `find(i) == find(j)`）。

**返回值**：`bool`

```python
uf = UnionFind(5)
uf.union(0, 1)
uf.equiv(0, 1)  # True
uf.equiv(0, 2)  # False
```

---

#### `into_labeling() -> list[int]`

返回所有元素所属集合标签的快照列表（每个元素被标记为其代表元的索引）。

**返回值**：`list[int]` — 长度为 `n`，`result[i]` 为元素 `i` 的代表元

```python
uf = UnionFind(4)
uf.union(0, 1)
uf.union(2, 3)
uf.into_labeling()  # [0, 0, 2, 2]（代表元可不同，但同组相同）
```

---

## 全局函数

---

#### `is_isomorphic(g1, g2) -> bool`

判断两个 `DiGraph` 是否**同构**（节点数和边结构相同，忽略节点/边权重）。

| 参数 | 类型 | 说明 |
| :--- | :--- | :--- |
| `g1` | `DiGraph` | 第一个图 |
| `g2` | `DiGraph` | 第二个图 |

**返回值**：`bool`

```python
from pypetgraph import is_isomorphic, DiGraph

g1 = DiGraph.from_edges([(0, 1, "a"), (1, 2, "b")])
g2 = DiGraph.from_edges([(0, 1, "x"), (1, 2, "y")])
is_isomorphic(g1, g2)  # True（结构相同，权重不同不影响）
```

---

## 异步版本

每个核心算法均提供 `_async` 后缀的协程版本，底层通过 `asyncio.to_thread` 在独立线程中执行，不阻塞事件循环。

```python
import asyncio
from pypetgraph import FastDiGraph, is_isomorphic_async

async def analyze(graph):
    # 同时运行三个算法，不互相阻塞
    dist, sccs, ranks = await asyncio.gather(
        graph.dijkstra_async(0),
        graph.tarjan_scc_async(),
        graph.page_rank_async(0.85, 100),
    )
    return dist, sccs, ranks
```

**可用 async 方法总览**：

| 类 | 异步方法 |
| :--- | :--- |
| `DiGraph` | `is_cyclic_async`, `toposort_async`, `dijkstra_async`, `astar_async`, `tarjan_scc_async`, `kosaraju_scc_async`, `all_simple_paths_async`, `has_path_connecting_async`, `page_rank_async` |
| `FastDiGraph` | `dijkstra_async`, `astar_async`, `bellman_ford_async`, `is_cyclic_async`, `toposort_async`, `tarjan_scc_async`, `has_path_connecting_async`, `page_rank_async`, `all_simple_paths_async` |
| `UnGraph` | `connected_components_async`, `has_path_connecting_async`, `is_bipartite_async` |
| `MatrixDiGraph` | `dijkstra_async`, `bellman_ford_async` |
| `CsrGraph` | `dijkstra_async`, `bellman_ford_async` |
| 全局函数 | `is_isomorphic_async` |
