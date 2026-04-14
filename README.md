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
- **智能匹配**: 基于主资源名的精确匹配 + 置信度评分，杜绝误匹配
- **Repo 隔离**: 单数据库支持多仓库，通过 `repo` 属性隔离
- **灵活配置**: 支持 .env 文件、环境变量、JSON 配置文件多种方式

---

## 目录

- [快速开始](#快速开始)
- [安装](#安装)
- [配置](#配置)
- [使用指南](#使用指南)
- [实体提取规则](#实体提取规则)
- [匹配策略详解](#匹配策略详解)
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
# 从源码安装
git clone https://github.com/Rikiz/graph_extractor_by_opencode.git
cd graph_extractor_by_opencode
pip install -e ".[dev]"
```

### 2. 配置 Neo4j

```bash
# 方式一：.env 文件（推荐）
cp .env.example .env
# 编辑 .env，填入实际密码
```

`.env` 内容：
```ini
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=neo4j
```

```bash
# 方式二：环境变量
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="your_password"

# 方式三：JSON 配置文件
# 在项目根目录创建 neo4j_config.json
```

`neo4j_config.json` 内容：
```json
{
  "uri": "bolt://localhost:7687",
  "user": "neo4j",
  "password": "your_password",
  "database": "neo4j"
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
repo-analyzer query stats
```

---

## 安装

### 系统要求

- Python 3.9+
- Neo4j 5.0+

### 依赖项

```
neo4j>=5.0.0            # Neo4j Python Driver
pyyaml>=6.0             # YAML 解析
pydantic>=2.0.0         # 配置模型
pydantic-settings>=2.0  # BaseSettings 支持
python-dotenv>=1.0.0    # .env 文件支持
```

### 开发依赖

```bash
pip install -e ".[dev]"
```

包含：pytest, black, ruff, mypy

---

## 配置

### 配置优先级（从高到低）

| 优先级 | 配置方式 | 说明 |
|--------|---------|------|
| 1 | 环境变量 | `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `NEO4J_DATABASE` |
| 2 | `.env` 文件 | 项目根目录，通过 python-dotenv 自动加载 |
| 3 | `neo4j_config.json` | JSON 格式配置文件 |
| 4 | 默认值 | `bolt://localhost:7687`, `neo4j/password` |

### 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `NEO4J_URI` | `bolt://localhost:7687` | 连接地址 |
| `NEO4J_USER` | `neo4j` | 用户名 |
| `NEO4J_PASSWORD` | `password` | 密码 |
| `NEO4J_DATABASE` | `neo4j` | 数据库名 |

### 代码配置

```python
from repo_analyzer import Neo4jWriter, Neo4jConfig

# 方式一：自动检测（推荐）
# 按优先级：环境变量 > .env > neo4j_config.json > 默认值
writer = Neo4jWriter.from_config()

# 方式二：指定配置文件
writer = Neo4jWriter.from_file("neo4j_config.json")

# 方式三：直接构造
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

# 查看各仓库节点统计
repo-analyzer query stats
```

#### 调用链输出解读

```
/api/v1/users/${userId}                              ← FrontendUrl (前端 URL)
  -> /v1/users/{id} (match: mapping, 1.0)            ← GatewayRoute (网关路由)
  -> UserController.getUser (match: exact, 1.0)      ← BackendApi (后端方法)
```

| 字段 | 含义 |
|------|------|
| `mapping` | 通过 JSON mapping 规则匹配，置信度 1.0 |
| `exact` | method + path 完全一致，置信度 1.0 |
| `normalized` | 归一化后匹配（去版本/统一参数名），置信度 0.8+ |
| `candidate` | 路径相似，低置信度，需人工确认 |

---

### Python API

#### 完整示例

```python
from repo_analyzer import GraphBuilder, RepoGroup, Neo4jWriter

# 初始化（自动检测配置）
writer = Neo4jWriter.from_config()
writer.create_unique_constraints()
writer.create_indexes()

builder = GraphBuilder(writer)
manager = RepoGroup(writer)

# ==================== 阶段1：构建单仓图 ====================

backend_stats = builder.build_repo_graph("backend", "/path/to/backend", "backend")
gateway_stats = builder.build_repo_graph("gateway", "/path/to/gateway", "gateway")
frontend_stats = builder.build_repo_graph("frontend", "/path/to/frontend", "frontend")

# ==================== 阶段2：跨仓分析 ====================

manager.create_group("full_stack", ["frontend", "gateway", "backend"])
results = manager.analyze_group("full_stack")

print(f"Frontend -> Gateway: {results['frontend_to_gateway']} 条")
print(f"Gateway -> Backend: {results['gateway_to_backend']} 条")
print(f"Mapping 关联: {results['mapping_relations']} 条")

# 查询调用链
chains = manager.get_call_chain(limit=10)
for chain in chains:
    print(f"{chain['frontend_url']}")
    print(f"  -> {chain['gateway_path']} (confidence: {chain['frontend_confidence']})")
    print(f"  -> {chain['backend_class']}.{chain['backend_method']}")

writer.close()
```

#### 高级用法

```python
# 重建仓库 (清除旧数据)
builder.rebuild_repo("backend", "/path/to/backend", "backend")

# 查看仓库统计
stats = builder.get_repo_stats("backend")

# 直接执行 Cypher 查询
results = writer.execute("""
    MATCH (url:FrontendUrl)-[:CALLS]->(route:GatewayRoute)
    WHERE route.repo = 'gateway'
    RETURN url.raw_url, route.full_path
    LIMIT 10
""")
```

---

## 实体提取规则

### Java Backend 提取

从 Spring Boot `@RestController` / `@Controller` 类中提取 API 端点。

**识别规则：**
1. 找到带有 `@RestController` 或 `@Controller` 注解的类
2. 提取类级别的 `@RequestMapping` 作为 base_path
3. 扫描类中所有 HTTP 方法注解：`@GetMapping`, `@PostMapping`, `@PutMapping`, `@DeleteMapping`, `@PatchMapping`, `@RequestMapping`
4. 拼接完整路径：`full_path = base_path + method_path`

**支持的注解格式：**

```java
@RestController
@RequestMapping("/api/v1")
public class UserController {

    @GetMapping("/users")                        // GET /api/v1/users
    @PostMapping(value = "/users")               // POST /api/v1/users
    @PutMapping(path = "/users/{id}")            // PUT /api/v1/users/{id}
    @DeleteMapping("/users/{id}")                // DELETE /api/v1/users/{id}
    @RequestMapping(value = "/users",            // POST /api/v1/users
                    method = RequestMethod.POST)
    @GetMapping                                  // GET /api/v1 (继承类路径)
    public ... method() { }
}
```

**提取结果示例：**

| method | full_path | class_name | method_name |
|--------|-----------|------------|-------------|
| GET | /api/v1/users | UserController | getAllUsers |
| POST | /api/v1/users | UserController | createUser |
| GET | /api/v1/users/{id} | UserController | getUser |

### YAML Gateway 提取

从 OpenAPI 3.x 和 Swagger 2.x 规范中提取路由。

**识别规则：**
1. 检测 `openapi` 或 `swagger` 字段识别规范版本
2. 提取 `basePath`（Swagger 2.x）或 `servers[0].url` 的路径部分（OpenAPI 3.x）
3. 遍历 `paths` 下所有路径和方法

```yaml
openapi: 3.0.0
servers:
  - url: https://api.example.com/v1    # base_path = /v1
paths:
  /users/{id}:
    get:
      operationId: getUserById          # 提取为 GatewayRoute
      tags: [users]
```

### TypeScript Frontend 提取

从 TypeScript 代码中提取 URL 调用，支持 4 种模式：

**模式1：字符串字面量**
```typescript
const url = "/api/v1/users";           // 提取: /api/v1/users
```

**模式2：模板字符串**
```typescript
const url = `/api/v1/users/${userId}`; // 提取: /api/v1/users/${userId}
                                       // 归一化: /api/v1/users/{userId}
```

**模式3：HTTP 调用**
```typescript
axios.get("/api/users");               // 提取: GET /api/users
fetch("/api/data");                    // 提取: /api/data
http.post("/api/items", data);         // 提取: POST /api/items
```

**模式4：函数返回值**
```typescript
function getUserUrl(id: string) {
  return `/api/v1/users/${id}`;        // 提取: /api/v1/users/${id}
}
```

### JSON Mapping 提取

从 JSON 配置文件中提取 URL 映射规则。

**识别规则：** 递归搜索包含 `uri`/`source`/`from` + `method` 或 `targetUri`/`target` 字段的对象。

```json
{
  "routes": [
    {
      "uri": "/api/v1/users/{id}",
      "method": "GET",
      "targetUri": "/v2/users/{id}",
      "targetService": "backend"
    }
  ]
}
```

---

## 匹配策略详解

### 核心原则

**主资源名必须匹配，否则拒绝关联。**

这避免了不同服务因路径结构相似而被错误关联的问题。例如：
- `/data/v1/tenant-configs/{id}` vs `/rest/v2/system-configs/{config_id}` → **拒绝**（tenant-configs ≠ system-configs）
- `/data/v1/tenant-configs/{id}` vs `/rest/v1/tenant-configs/{id}` → **匹配**（主资源相同）

### 匹配流程

```
1. 主资源检查（硬性规则，不通过直接返回 0.0）
   ├── 主资源完全相同      → 继续
   ├── 严格包含关系        → 继续（如 user 包含在 user-profile 中）
   ├── 共享非通用核心词    → 继续（如 user-profile 和 user-detail 共享 user）
   └── 主资源不匹配        → 返回 confidence = 0.0

2. 置信度计算（加权评分）
   ├── 资源段匹配分（权重 0.5~0.8）
   ├── 结构相似度（权重 0.15~0.3）
   └── 参数位置匹配（权重 0.05~0.1）
```

### 主资源名提取

取路径中**最后一个非停用词段**，停用词包括：版本号（v1/v2/v3）、通用前缀（api/rest/data/portal/report）。

```
/data/v1/tenant-configs/{id}    → 主资源: tenant-configs
/rest/v2/system-configs/{id}    → 主资源: system-configs
/api/v1/users/{id}              → 主资源: users
/report/v1/defects/next-status  → 主资源: next-status
```

### 通用词排除

以下词过于通用，不能作为资源匹配依据：

```
status, config, info, detail, list, id, profile, setting, type, name,
code, item, data, value, result, response, count, search, query, ...
```

**示例：**
- `user-profile` vs `system-profile` → profile 是通用词，无共享非通用词 → **拒绝**
- `tenant-configs` vs `system-configs` → configs 是通用词，tenant ≠ system → **拒绝**

### 包含关系严格检查

只有当较短名称的**非通用词**全部出现在较长名称中时，才算包含：

| 短名称 | 长名称 | 非通用词 | 结果 |
|--------|--------|---------|------|
| user | user-profile | user | ✅ user 在 user-profile 中 |
| tenant | tenant-configs | tenant | ✅ tenant 在 tenant-configs 中 |
| status | next-status | (无) | ❌ status 是通用词 |
| configs | system-configs | (无) | ❌ configs 是通用词 |

### 匹配类型与置信度

| match_type | confidence 范围 | 条件 | 建议 |
|------------|----------------|------|------|
| `mapping` | 1.0 | JSON mapping 规则匹配 | 可信 |
| `exact` | 1.0 | method + full_path 完全一致 | 可信 |
| `normalized` | 0.8+ | 主资源匹配 + 归一化后路径相似 | 基本可信 |
| `candidate` | 0.3~0.7 | 主资源有弱关联（包含/共享词） | 需人工确认 |
| (不创建) | <0.3 | 主资源不匹配 | 不关联 |

### URL 归一化规则

```python
# 1. 模板语法统一
"/api/v1/users/${userId}"  →  "/api/v1/users/{userId}"

# 2. 查询参数去除
"/api/users?foo=bar"       →  "/api/users"

# 3. 版本前缀去除
"/v1/users/{id}"           →  "/users/{id}"
"/api/v2/users"            →  "/api/users"

# 4. 参数名统一
"/users/{userId}"          →  "/users/{param1}"
"/users/{id}"              →  "/users/{param1}"

# 5. 路径标准化
"//api//users"             →  "/api/users"
```

### 实际案例对比

| 路径1 | 路径2 | 旧算法 | 新算法 | 原因 |
|-------|-------|--------|--------|------|
| `/data/v1/tenant-configs/{id}` | `/rest/v2/system-configs/{config_id}` | 0.773 | **0.0** | tenant-configs ≠ system-configs |
| `/portal/v4/tenant/tenant-package-status` | `/v2/inner-cron/status` | 0.761 | **0.0** | tenant-package-status ≠ status |
| `/data/v1/tenant-configs/{id}` | `/rest/v1/tenant-configs/{id}` | 失败 | **1.0** | 主资源相同 |
| `/api/v1/users/{id}` | `/api/v2/users/{id}` | 0.5 | **1.0** | 主资源相同，仅版本不同 |

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
│         (主资源检查 + 置信度计算)                             │
│                       │                                      │
│                       ▼                                      │
│              关系创建 (不创建节点)                           │
│                       │                                      │
│                       ▼                                      │
│         CALLS / ROUTES_TO / MAPS_TO                          │
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

---

## API 参考

### GraphBuilder

```python
class GraphBuilder:
    def build_repo_graph(
        self, repo_name: str, repo_path: str, repo_type: str
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
        self, repo_name: str, repo_path: str, repo_type: str
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
        """获取调用链 (Frontend -> Gateway -> Backend)"""
    
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
        """自动检测配置（环境变量 > .env > json > 默认值）"""
    
    @classmethod
    def from_file(cls, config_path: str) -> "Neo4jWriter":
        """从 JSON 配置文件创建"""
    
    def create_unique_constraints(self) -> None:
        """创建唯一约束"""
    
    def create_indexes(self) -> None:
        """创建索引"""
    
    def write_entities(self, entities: List, batch_size: int = 500) -> Dict[str, int]:
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

### 2. 使用 .env 文件管理配置

```bash
# ✅ 推荐：使用 .env 文件
cp .env.example .env
# 编辑 .env 填入实际值
# .env 已在 .gitignore 中，不会泄露密码

# ❌ 不推荐：密码写在代码里
config = Neo4jConfig(password="my_secret_password")
```

### 3. 批量处理

```python
# ✅ 使用批量写入
writer.write_entities(entities, batch_size=500)

# ❌ 避免逐条写入
for entity in entities:
    writer.write_entity(entity)
```

### 4. 检查匹配置信度

```cypher
-- 高置信度匹配（可信）
MATCH ()-[r:CALLS|ROUTES_TO]->()
WHERE r.confidence >= 0.8
RETURN r.match_type, count(*)

-- 需人工确认的候选
MATCH ()-[r:CALLS|ROUTES_TO]->()
WHERE r.match_type = 'candidate'
RETURN r

-- 查看匹配详情
MATCH ()-[r:CALLS|ROUTES_TO]->()
RETURN r.match_type, r.confidence, r.match_details
LIMIT 20
```

### 5. 使用 Mapping 规则处理复杂映射

当路径差异较大时，创建 mapping.json 明确指定映射关系：

```json
{
  "mappings": [
    {
      "uri": "/data/v1/tenant-configs/{id}",
      "method": "PUT",
      "targetUri": "/rest/v1/tenant-configs/{id}"
    }
  ]
}
```

### 6. 定期重建

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
1. 主资源名不同（如 `tenant-configs` vs `system-configs`）
2. HTTP Method 不一致
3. 前端使用了未在 Gateway 定义的路径

解决方法：
```bash
# 查看未匹配项
repo-analyzer query unmatched-fe

# 创建 mapping.json 配置手动指定映射
```

### Q: 为什么 tenant-configs 和 system-configs 不会匹配？

**A:** 新的匹配算法要求**主资源名必须匹配**。`tenant-configs` 和 `system-configs` 的主资源名不同（tenant vs system），`configs` 是通用词不能作为匹配依据。

如果它们确实应该映射，请使用 Mapping 规则：
```json
{
  "uri": "/data/v1/tenant-configs/{id}",
  "method": "GET",
  "targetUri": "/rest/v2/system-configs/{config_id}"
}
```

### Q: 如何处理多版本的 API？

**A:** 版本号差异（v1 vs v2）在归一化时会被自动去除。如果同一资源的不同版本需要映射，使用 Mapping 规则：
```json
{
  "uri": "/api/v1/users/{id}",
  "method": "GET",
  "targetUri": "/v2/users/{id}"
}
```

### Q: 如何删除错误的关系？

```cypher
-- 删除候选关系
MATCH ()-[r:CALLS {match_type: 'candidate'}]->()
DELETE r

-- 删除特定置信度以下的关系
MATCH ()-[r:CALLS|ROUTES_TO]->()
WHERE r.confidence < 0.8
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

### Q: 如何调试 Java 解析问题？

**A:** 查看日志输出，会显示每个文件提取了多少 API：

```
2024-01-15 - repo_analyzer.parsers.java_parser - INFO - [java_parser.py:41] - Extracted 5 APIs from UserController.java
```

也可以手动测试：
```python
from repo_analyzer.parsers.java_parser import JavaParser

parser = JavaParser()
apis = parser.parse("path/to/YourController.java", "backend")
for api in apis:
    print(f"  {api.method} {api.full_path} -> {api.class_name}.{api.method_name}")
```

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
