# Contributing to Multi-Repo Code Graph Builder

感谢您考虑为本项目做出贡献！

---

## 目录

- [行为准则](#行为准则)
- [如何贡献](#如何贡献)
- [开发环境设置](#开发环境设置)
- [代码规范](#代码规范)
- [提交规范](#提交规范)
- [Pull Request 流程](#pull-request-流程)
- [问题报告](#问题报告)

---

## 行为准则

本项目采用贡献者公约作为行为准则。参与此项目即表示您同意遵守其条款。请阅读 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) 了解详情。

---

## 如何贡献

### 报告 Bug

如果您发现了 bug，请创建 [Issue](https://github.com/Rikiz/graph_extractor_by_opencode/issues/new)，包含：

1. **标题**: 简洁描述问题
2. **环境**: Python 版本、Neo4j 版本、操作系统
3. **复现步骤**: 详细的重现过程
4. **期望行为**: 您期望发生什么
5. **实际行为**: 实际发生了什么
6. **日志/截图**: 如有错误日志请附上

### 提出新功能

1. 先创建 Issue 讨论您的想法
2. 等待维护者反馈
3. 获得批准后再开始实现

### 提交代码

1. Fork 仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

---

## 开发环境设置

### 1. 克隆仓库

```bash
git clone https://github.com/Rikiz/graph_extractor_by_opencode.git
cd graph_extractor_by_opencode
```

### 2. 创建虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
.\venv\Scripts\activate  # Windows
```

### 3. 安装开发依赖

```bash
pip install -e ".[dev]"
```

### 4. 安装 pre-commit hooks (可选)

```bash
pip install pre-commit
pre-commit install
```

### 5. 运行测试

```bash
# 运行所有测试
make test

# 或直接使用 pytest
pytest tests/ -v

# 带覆盖率
pytest tests/ -v --cov=repo_analyzer --cov-report=html
```

### 6. 启动 Neo4j (用于集成测试)

```bash
# 使用 Docker
docker run -d \
  --name neo4j \
  -p 7474:7474 \
  -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:5-community
```

---

## 代码规范

### Python 版本

- 最低支持 Python 3.9
- 使用类型注解 (Type Hints)

### 格式化

使用 [Black](https://github.com/psf/black) 和 [Ruff](https://github.com/astral-sh/ruff):

```bash
# 格式化代码
make format

# 或
black repo_analyzer/
ruff check --fix repo_analyzer/
```

### 类型检查

使用 [mypy](https://mypy-lang.org/):

```bash
make lint
# 或
mypy repo_analyzer/
```

### 代码风格

1. **命名规范**
   - 类名: PascalCase (`GraphBuilder`)
   - 函数名: snake_case (`build_repo_graph`)
   - 常量: UPPER_SNAKE_CASE (`HTTP_METHODS`)
   - 私有方法: 前缀下划线 (`_extract_urls`)

2. **文档字符串**
   ```python
   def build_repo_graph(self, repo_name: str, repo_path: str) -> Dict[str, int]:
       """
       构建单仓图.
       
       Args:
           repo_name: 仓库名称标识
           repo_path: 仓库本地路径
       
       Returns:
           统计信息字典
       
       Raises:
           ValueError: 如果路径不存在
       """
   ```

3. **导入顺序**
   ```python
   # 标准库
   import os
   import re
   from typing import List, Dict
   
   # 第三方库
   from neo4j import GraphDatabase
   
   # 本地模块
   from .base_parser import BaseParser
   ```

4. **最大行长度**: 100 字符

### 测试规范

1. **测试文件命名**: `test_<module_name>.py`
2. **测试类命名**: `Test<Feature>`
3. **测试方法命名**: `test_<scenario>`

```python
class TestJavaParser:
    def test_extract_simple_get_mapping(self):
        """测试提取简单的 GET 映射"""
        pass
    
    def test_extract_multiple_mappings(self):
        """测试提取多个映射"""
        pass
```

---

## 提交规范

使用 [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type 类型

- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式 (不影响功能)
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具相关

### 示例

```
feat(parser): add support for Spring WebFlux annotations

- Add @GetMapping support for WebFlux
- Add @PostMapping support for WebFlux
- Update JavaParser tests

Closes #123
```

```
fix(matcher): fix URL normalization for query parameters

URLs with query parameters were not being normalized correctly.
This fix strips query params before matching.

Fixes #456
```

---

## Pull Request 流程

### PR 检查清单

- [ ] 代码遵循项目风格规范
- [ ] 已运行 `make lint` 无错误
- [ ] 已运行 `make test` 全部通过
- [ ] 已添加必要的测试
- [ ] 已更新相关文档
- [ ] 提交信息符合规范

### PR 标题格式

```
<type>(<scope>): <description>
```

示例:
```
feat(cli): add --verbose flag for detailed output
fix(matcher): correct path parameter extraction
docs(readme): add installation guide for Windows
```

### 审查流程

1. 提交 PR
2. 自动 CI 检查运行
3. 至少一位维护者审查
4. 修改反馈意见
5. 批准后合并

---

## 问题报告

### Bug 报告模板

```markdown
## 描述
简要描述 bug

## 复现步骤
1. 运行命令 '...'
2. 查看输出 '...'
3. 发现错误

## 期望行为
应该发生什么

## 实际行为
实际发生了什么

## 环境
- Python: 3.11.0
- Neo4j: 5.10.0
- OS: macOS 13.0
- Package version: 1.0.0

## 日志/截图
```
[粘贴日志]
```

## 附加信息
其他相关信息
```

### 功能请求模板

```markdown
## 功能描述
清晰描述您想要的功能

## 使用场景
描述这个功能解决什么问题

## 建议方案
如果有建议的实现方式，请描述

## 替代方案
考虑过的其他方案

## 附加信息
其他相关信息
```

---

## 获取帮助

- 创建 [Issue](https://github.com/Rikiz/graph_extractor_by_opencode/issues)
- 查看 [文档](README.md)
- 查看 [FAQ](README.md#常见问题)

---

再次感谢您的贡献！
