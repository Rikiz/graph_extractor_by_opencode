# Multi-Repo Code Graph Builder

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**多仓代码图构建 + 跨仓调用分析系统**

基于 Neo4j 的代码知识图谱构建工具，支持自动分析多仓库间的 API 调用关系。

---

## 核心特性

- **两阶段架构**: 单仓独立构建，跨仓联合分析
- **多语言支持**: Java (Spring Boot), TypeScript, YAML (OpenAPI/Swagger), JSON
- **智能匹配**: 精确匹配、归一化匹配、Mapping 规则、候选推荐
- **置信度评分**: 每个关联关系都有匹配置信度
- **Repo 隔离**: 单数据库支持多仓库，通过 `repo` 属性隔离

---

## 目录

- [快速开始](#快速开始)
- [安装](#安装)
- [配置](#配置)
- [使用指南](#使用指南)
- [架构设计](#架构设计)
- [API 参考](#api-参考)
- [最佳实践](#最佳实践)
- [常见问题](#常见问题)
- [贡献指南](#贡献指南)
- [许可证](#许可证)

---

## 快速开始

### 1. 安装

```bash
# 使用 pip
pip install repo-analyzer

# 或从源码安装
git clone https://github.com/Rikiz/graph_extractor_by_opencode.git
cd graph_extractor_by_opencode
pip install -e ".[dev]"
```

### 2. 配置 Neo4j

```bash
# 方式一：环境变量
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="your_password"

# 方式二：配置文件 (neo4j_config.json)
{
  "uri": "bolt://localhost:7687",
  "user": "neo4j",
  "password": "your_password"
}
```

### 3. 构建图并分析

```bash
# 阶段1：构建各仓库图
repo-analyzer build --name backend --path ./backend --type backend
repo-analyzer build --name gateway --path ./gateway --type gateway
repo-analyzer build --name frontend --path ./frontend --type frontend

# 阶段2：跨仓分析
repo-analyzer group create --name full_stack --repos frontend gateway backend
repo-analyzer analyze --group full_stack

# 查询结果
repo-analyzer query chain --limit 10
```

---

## 安装

### 系统要求

- Python 3.9+
- Neo4j 5.0+

### 依赖项

```
neo4j>=5.0.0    # Neo4j Python Driver
pyyaml>=6.0     # YAML 解析
```

### 开发依赖

```bash
pip install -e ".[dev]"
```

包含：pytest, black, ruff, mypy

---

## 配置

### Neo4j 连接配置

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|---------|--------|------|
| URI | `NEO4J_URI` | `bolt://localhost:7687` | 连接地址 |
| User | `NEO4J_USER` | `neo4j` | 用户名 |
| Password | `NEO4J_PASSWORD` | `password` | 密码 |
| Database | `NEO4J_DATABASE` | `neo4j` | 数据库名 |

### 项目配置示例

```python
from repo_analyzer import Neo4jWriter, Neo4jConfig

# 方式一：环境变量
writer = Neo4jWriter.from_config()

# 方式二：配置文件
writer = Neo4jWriter.from_file("config/neo4j_config.json")

# 方式三：直接配置
config = Neo4jConfig(
    uri="bolt://localhost:7687",
    user="neo4j",
    password="password",
    database="neo4j"
)
writer = Neo4jWriter(config)
```

---

## 使用指南

### 命令行工具 (CLI)

#### 构建单仓图

```bash
repo-analyzer build --name <repo_name> --path <repo_path> --type <repo_type>

# 参数说明：
# --name     仓库名称标识 (如: backend, gateway, frontend)
# --path     仓库本地路径
# --type     仓库类型: backend | gateway | frontend
# --rebuild  强制重建 (清除已有数据)
```

**示例：**

```bash
# Java 后端仓库
repo-analyzer build --name backend --path ~/projects/my-backend --type backend

# Gateway (OpenAPI/Swagger)
repo-analyzer build --name gateway --path ~/projects/my-gateway --type gateway

# TypeScript 前端
repo-analyzer build --name frontend --path ~/projects/my-frontend --type frontend
```

#### 管理仓库组

```bash
# 创建仓库组
repo-analyzer group create --name full_stack --repos frontend gateway backend

# 查看所有组
repo-analyzer group list

# 查看组统计
repo-analyzer group stats --name full_stack
```

#### 执行跨仓分析

```bash
repo-analyzer analyze --group <group_name>
```

#### 查询结果

```bash
# 查看调用链 (Frontend -> Gateway -> Backend)
repo-analyzer query chain --limit 20

# 查看未匹配的前端 URL
repo-analyzer query unmatched-fe

# 查看未匹配的 Gateway 路由
repo-analyzer query unmatched-gw
```

---

### Python API

#### 完整示例

```python
from repo_analyzer import GraphBuilder, RepoGroup, Neo4jWriter

# 初始化
writer = Neo4jWriter.from_config()
writer.create_unique_constraints()
writer.create_indexes()

builder = GraphBuilder(writer)
manager = RepoGroup(writer)

# ==================== 阶段1：构建单仓图 ====================

# 构建 Backend
backend_stats = builder.build_repo_graph(
    repo_name="backend",
    repo_path="/path/to/backend",
    repo_type="backend"
)
print(f"Backend: {backend_stats}")

# 构建 Gateway
gateway_stats = builder.build_repo_graph(
    repo_name="gateway",
    repo_path="/path/to/gateway",
    repo_type="gateway"
)
print(f"Gateway: {gateway_stats}")

# 构建 Frontend
frontend_stats = builder.build_repo_graph(
    repo_name="frontend",
    repo_path="/path/to/frontend",
    repo_type="frontend"
)
print(f"Frontend: {frontend_stats}")

# ==================== 阶段2：跨仓分析 ====================

# 创建组
manager.create_group("full_stack", ["frontend", "gateway", "backend"])

# 执行分析
results = manager.analyze_group("full_stack")

print(f"""
分析结果:
  Frontend -> Gateway: {results['frontend_to_gateway']} 条
  Gateway -> Backend: {results['gateway_to_backend']} 条
  Mapping 关联: {results['mapping_relations']} 条
""")

# 查询调用链
chains = manager.get_call_chain(limit=10)
for chain in chains:
    print(f"{chain['frontend_url']}")
    print(f"  -> {chain['gateway_path']} (confidence: {chain['frontend_confidence']})")
    print(f"  -> {chain['backend_class']}.{chain['backend_method']}")

# 关闭连接
writer.close()
```

#### 高级用法

```python
# 重建仓库 (清除旧数据)
builder.rebuild_repo("backend", "/path/to/backend", "backend")

# 查看仓库统计
stats = builder.get_repo_stats("backend")

# 清除仓库数据
deleted_count = writer.clear_repo("backend")

# 直接执行 Cypher 查询
results = writer.execute("""
    MATCH (url:FrontendUrl)-[:CALLS]->(route:GatewayRoute)
    WHERE route.repo = 'gateway'
    RETURN url.raw_url, route.full_path
    LIMIT 10
""")
```

---

## 架构设计

### 两阶段架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Phase 1: 单仓图构建                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Backend Repo    Gateway Repo    Frontend Repo             │
│        │              │                │                     │
│        ▼              ▼                ▼                     │
│   JavaParser     YamlParser    TsParser+JsonParser           │
│        │              │                │                     │
│        └──────────────┼────────────────┘                     │
│                       ▼                                      │
│                  Neo4j Writer                                │
│                  (MERGE 写入)                                │
│                       │                                      │
│                       ▼                                      │
│              ┌─────────────────┐                             │
│              │    Neo4j DB     │                             │
│              │  (repo 隔离)    │                             │
│              └─────────────────┘                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Phase 2: 跨仓调用分析                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│              ┌─────────────────┐                             │
│              │    Neo4j DB     │                             │
│              │  (已有节点)     │                             │
│              └────────┬────────┘                             │
│                       │                                      │
│                       ▼                                      │
│                 CrossAnalyzer                                │
│                       │                                      │
│            ┌──────────┼──────────┐                           │
│            ▼          ▼          ▼                           │
│      FrontendUrl  GatewayRoute  MappingRule                  │
│            │          │          │                           │
│            └──────────┼──────────┘                           │
│                       ▼                                      │
│                  UrlMatcher                                  │
│            (匹配策略 + 置信度)                               │
│                       │                                      │
│                       ▼                                      │
│              关系创建 (不创建节点)                           │
│                       │                                      │
│                       ▼                                      │
│              CALLS / ROUTES_TO / MAPS_TO                     │
└─────────────────────────────────────────────────────────────┘
```

### 图模型

#### 节点类型

| 节点 | 标签 | 唯一键 | 说明 |
|------|------|--------|------|
| BackendApi | `:BackendApi` | (method, full_path, repo) | Java Controller 方法 |
| GatewayRoute | `:GatewayRoute` | (method, full_path, repo) | OpenAPI/Swagger 路由 |
| FrontendUrl | `:FrontendUrl` | (raw_url, file_path, repo) | TypeScript URL 引用 |
| MappingRule | `:MappingRule` | (uri, method, repo) | JSON 映射配置 |

#### 关系类型

| 关系 | 起点 | 终点 | 属性 | 阶段 |
|------|------|------|------|------|
| CALLS | FrontendUrl | GatewayRoute | match_type, confidence | 2 |
| ROUTES_TO | GatewayRoute | BackendApi | match_type, confidence | 2 |
| USES_MAPPING | FrontendUrl | MappingRule | match_type=1.0 | 2 |
| MAPS_TO | MappingRule | GatewayRoute | match_type=1.0 | 2 |

### 匹配策略

#### 优先级排序

```
1. Mapping 规则匹配 (confidence = 1.0)
   └── 通过 JSON mapping 配置直接关联

2. 精确匹配 (confidence = 1.0)
   └── method + full_path 完全一致

3. 归一化匹配 (confidence = 0.8)
   └── 去版本前缀 + 统一参数名后匹配

4. 候选匹配 (confidence = 0.4 - 0.7)
   └── 相似路径的潜在关联
```

#### 归一化规则

```python
# 1. URL 格式统一
"/api/v1/users/${userId}" → "/api/v1/users/{userId}"

# 2. 版本前缀去除
"/v1/users/{id}" → "/users/{id}"
"/api/v2/users" → "/api/users"

# 3. 参数名统一
"/users/{userId}/posts/{postId}" → "/users/{param1}/posts/{param2}"
```

---

## API 参考

### GraphBuilder

```python
class GraphBuilder:
    def build_repo_graph(
        self,
        repo_name: str,
        repo_path: str,
        repo_type: str
    ) -> Dict[str, int]:
        """
        构建单仓图
        
        Args:
            repo_name: 仓库名称标识
            repo_path: 仓库本地路径
            repo_type: 仓库类型 (backend/gateway/frontend)
        
        Returns:
            统计信息 {"BackendApi": 45, ...}
        """
    
    def rebuild_repo(
        self,
        repo_name: str,
        repo_path: str,
        repo_type: str
    ) -> Dict[str, int]:
        """重建仓库图（清除旧数据）"""
    
    def get_repo_stats(self, repo_name: str) -> Dict[str, int]:
        """获取仓库统计信息"""
```

### RepoGroup

```python
class RepoGroup:
    def create_group(self, name: str, repos: List[str]) -> None:
        """创建仓库组"""
    
    def analyze_group(self, name: str) -> Dict[str, int]:
        """执行跨仓分析"""
    
    def get_group_stats(self, name: str) -> Dict[str, Any]:
        """获取组统计信息"""
    
    def get_call_chain(self, limit: int = 100) -> List[Dict]:
        """获取调用链"""
    
    def get_unmatched_frontend_urls(self) -> List[Dict]:
        """获取未匹配的前端 URL"""
    
    def get_unmatched_gateway_routes(self) -> List[Dict]:
        """获取未匹配的 Gateway 路由"""
```

### Neo4jWriter

```python
class Neo4jWriter:
    @classmethod
    def from_config(cls) -> "Neo4jWriter":
        """从环境变量创建"""
    
    @classmethod
    def from_file(cls, config_path: str) -> "Neo4jWriter":
        """从配置文件创建"""
    
    def create_unique_constraints(self) -> None:
        """创建唯一约束"""
    
    def write_entities(
        self,
        entities: List,
        batch_size: int = 500
    ) -> Dict[str, int]:
        """批量写入实体"""
    
    def clear_repo(self, repo_name: str) -> int:
        """清除仓库数据"""
    
    def execute(self, query: str, params: Dict = None) -> List[Dict]:
        """执行 Cypher 查询"""
```

---

## 最佳实践

### 1. 分阶段执行

```python
# ✅ 推荐：先完成所有单仓构建，再执行跨仓分析
builder.build_repo_graph("backend", ..., "backend")
builder.build_repo_graph("gateway", ..., "gateway")
builder.build_repo_graph("frontend", ..., "frontend")

manager.create_group("app", ["frontend", "gateway", "backend"])
manager.analyze_group("app")

# ❌ 不推荐：混在一起执行
builder.build_repo_graph("backend", ..., "backend")
manager.analyze_group("app")  # 其他仓库还没构建
```

### 2. 使用唯一约束

```python
# ✅ 首次运行时创建约束
writer.create_unique_constraints()

# ✅ 约束确保数据唯一性
# MERGE 会自动处理重复节点
```

### 3. 批量处理

```python
# ✅ 使用批量写入
writer.write_entities(entities, batch_size=500)

# ❌ 避免逐条写入
for entity in entities:
    writer.write_entity(entity)  # 性能差
```

### 4. 检查匹配置信度

```cypher
-- 查看高置信度匹配
MATCH ()-[r:CALLS|ROUTES_TO]->()
WHERE r.confidence >= 0.8
RETURN r.match_type, count(*)

-- 查看需要人工确认的候选
MATCH ()-[r:CALLS|ROUTES_TO]->()
WHERE r.match_type = 'candidate'
RETURN r
```

### 5. 定期重建

```python
# 代码变更后重建
builder.rebuild_repo("backend", "/path/to/backend", "backend")

# 重新分析
manager.analyze_group("full_stack")
```

---

## 常见问题

### Q: 为什么有些 URL 没有匹配上？

**A:** 可能原因：
1. URL 格式差异过大，置信度低于阈值 (0.4)
2. HTTP Method 不一致
3. 前端使用了未在 Gateway 定义的路径

解决方法：
```cypher
-- 查看未匹配项
repo-analyzer query unmatched-fe

-- 手动创建 mapping.json 配置
```

### Q: 如何处理多版本的 API？

**A:** 使用 Mapping 规则：
```json
{
  "mappings": [
    {
      "uri": "/api/v1/users/{id}",
      "method": "GET",
      "targetUri": "/v2/users/{id}"
    }
  ]
}
```

### Q: 如何删除错误的关系？

```cypher
-- 删除特定关系
MATCH ()-[r:CALLS {match_type: 'candidate'}]->()
DELETE r

-- 删除某个组的所有关系
MATCH ()-[r]->()
WHERE startNode(r).repo IN ['frontend', 'gateway']
DELETE r
```

### Q: 支持其他语言吗？

**A:** 当前支持：
- Java (Spring Boot)
- TypeScript/JavaScript
- YAML (OpenAPI/Swagger)
- JSON (Mapping 配置)

扩展其他语言：继承 `BaseParser` 并实现 `parse()` 方法。

---

## 贡献指南

参见 [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 许可证

[MIT License](LICENSE)

---

## 联系方式

- GitHub Issues: https://github.com/Rikiz/graph_extractor_by_opencode/issues
- Repository: https://github.com/Rikiz/graph_extractor_by_opencode
