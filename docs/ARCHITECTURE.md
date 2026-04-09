# Architecture Design

This document describes the architecture and design decisions of the Multi-Repo Code Graph Builder.

---

## Table of Contents

- [Overview](#overview)
- [Design Principles](#design-principles)
- [Two-Phase Architecture](#two-phase-architecture)
- [Component Architecture](#component-architecture)
- [Data Model](#data-model)
- [Matching Strategies](#matching-strategies)
- [Performance Considerations](#performance-considerations)
- [Extensibility](#extensibility)

---

## Overview

The Multi-Repo Code Graph Builder is a system for analyzing API call relationships across multiple code repositories. It builds a knowledge graph in Neo4j that represents:

1. **Code entities**: REST APIs, routes, URL references
2. **Relationships**: How frontend calls gateway, how gateway routes to backend

### Goals

- **Separation of Concerns**: Single-repo analysis is independent
- **Incremental Updates**: Rebuild individual repos without affecting others
- **Flexible Matching**: Multiple matching strategies with confidence scores
- **Scalability**: Handle large codebases efficiently

---

## Design Principles

### 1. Two-Phase Processing

The system strictly separates:
- **Phase 1**: Single-repo graph building (no cross-repo dependencies)
- **Phase 2**: Cross-repo relationship analysis (depends on Phase 1)

This allows:
- Independent execution of Phase 1 for each repo
- Re-running Phase 2 without rebuilding graphs
- Parallel processing in Phase 1

### 2. Repo Isolation

All nodes include a `repo` property for isolation:
- Single Neo4j database supports multiple repos
- Queries filter by `repo` when needed
- Clear data ownership

### 3. Idempotent Operations

Using Neo4j `MERGE` ensures:
- No duplicate nodes on re-runs
- Safe to rebuild without manual cleanup
- Consistent state

### 4. Confidence-Based Matching

All relationships have:
- `match_type`: Strategy used
- `confidence`: 0.0 - 1.0 score
- Optional `match_details`: Human-readable explanation

---

## Two-Phase Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    PHASE 1: Single-Repo Building                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ Backend Repo │  │ Gateway Repo │  │Frontend Repo │           │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘           │
│         │                 │                 │                    │
│         ▼                 ▼                 ▼                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ JavaParser   │  │ YamlParser   │  │ TsParser     │           │
│  │              │  │              │  │ JsonParser   │           │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘           │
│         │                 │                 │                    │
│         └─────────────────┼─────────────────┘                    │
│                           ▼                                      │
│                   ┌──────────────┐                               │
│                   │ Neo4jWriter  │                               │
│                   │ (MERGE)      │                               │
│                   └──────┬───────┘                               │
│                          │                                       │
│                          ▼                                       │
│                   ┌──────────────┐                               │
│                   │   Neo4j DB   │                               │
│                   │  (repo 隔离) │                               │
│                   └──────────────┘                               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   PHASE 2: Cross-Repo Analysis                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                   ┌──────────────┐                               │
│                   │   Neo4j DB   │                               │
│                   │  (已有节点)  │                               │
│                   └──────┬───────┘                               │
│                          │                                       │
│                          ▼                                       │
│                   ┌──────────────┐                               │
│                   │ RepoGroup    │                               │
│                   │ Manager      │                               │
│                   └──────┬───────┘                               │
│                          │                                       │
│                          ▼                                       │
│                   ┌──────────────┐                               │
│                   │CrossAnalyzer │                               │
│                   └──────┬───────┘                               │
│                          │                                       │
│                          ▼                                       │
│                   ┌──────────────┐                               │
│                   │ UrlMatcher   │                               │
│                   │              │                               │
│                   │ - Mapping    │                               │
│                   │ - Exact      │                               │
│                   │ - Normalized │                               │
│                   │ - Candidate  │                               │
│                   └──────┬───────┘                               │
│                          │                                       │
│                          ▼                                       │
│                   ┌──────────────┐                               │
│                   │  Relations   │                               │
│                   │  (No nodes)  │                               │
│                   └──────────────┘                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Architecture

### Core Components

```
repo_analyzer/
├── core/
│   ├── graph_builder.py      # Phase 1 orchestrator
│   ├── cross_analyzer.py     # Phase 2 orchestrator
│   └── repo_manager.py       # RepoGroup management
├── parsers/
│   ├── base_parser.py        # Abstract base
│   ├── java_parser.py        # Java/Spring Boot
│   ├── yaml_parser.py        # OpenAPI/Swagger
│   ├── ts_parser.py          # TypeScript
│   └── json_parser.py        # Mapping config
├── matcher/
│   ├── url_matcher.py        # URL matching strategies
│   └── candidate_ranker.py   # Candidate ranking
├── writer/
│   └── neo4j_writer.py       # Neo4j operations
└── models/
    └── entities.py           # Data classes
```

### Component Responsibilities

| Component | Responsibility | Dependencies |
|-----------|---------------|--------------|
| GraphBuilder | Orchestrate single-repo building | Parsers, Neo4jWriter |
| CrossAnalyzer | Orchestrate cross-repo analysis | UrlMatcher, Neo4jWriter |
| RepoGroup | Manage repo groups | CrossAnalyzer, Neo4jWriter |
| Parsers | Extract entities from code files | BaseParser |
| UrlMatcher | Match URLs across repos | Entities |
| Neo4jWriter | All Neo4j operations | Neo4j driver, Config |

---

## Data Model

### Node Types

```
┌─────────────────────────────────────────────────────────────┐
│ BackendApi                                                   │
├─────────────────────────────────────────────────────────────┤
│ Unique Key: (method, full_path, repo)                       │
│ Properties:                                                 │
│   - method: String           "GET", "POST", ...            │
│   - full_path: String        "/api/v1/users/{id}"          │
│   - repo: String             "backend"                     │
│   - class_name: String       "UserController"              │
│   - method_name: String      "getUser"                     │
│   - parameters: [String]     ["id"]                        │
│   - file_path: String        "src/.../UserController.java" │
│   - line_number: Int         45                            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ GatewayRoute                                                 │
├─────────────────────────────────────────────────────────────┤
│ Unique Key: (method, full_path, repo)                       │
│ Properties:                                                 │
│   - method: String           "GET"                         │
│   - full_path: String        "/v1/users/{id}"              │
│   - repo: String             "gateway"                     │
│   - operation_id: String     "getUserById"                 │
│   - tags: [String]           ["users"]                     │
│   - summary: String          "Get user by ID"              │
│   - parameters: [Map]        [{name: "id", in: "path"}]    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ FrontendUrl                                                  │
├─────────────────────────────────────────────────────────────┤
│ Unique Key: (raw_url, file_path, repo)                      │
│ Properties:                                                 │
│   - raw_url: String          "/api/v1/users/${userId}"     │
│   - file_path: String        "src/services/userService.ts" │
│   - repo: String             "frontend"                    │
│   - normalized_url: String   "/api/v1/users/{userId}"      │
│   - http_method: String      "GET"                         │
│   - is_template: Bool        true                          │
│   - variables: [String]      ["userId"]                    │
│   - line_number: Int         23                            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ MappingRule                                                  │
├─────────────────────────────────────────────────────────────┤
│ Unique Key: (uri, method, repo)                              │
│ Properties:                                                 │
│   - uri: String              "/api/v1/users/{id}"          │
│   - method: String           "GET"                         │
│   - repo: String             "frontend"                    │
│   - target_uri: String       "/v2/users/{id}"              │
│   - target_service: String   "backend"                     │
└─────────────────────────────────────────────────────────────┘
```

### Relationships

```
┌─────────────┐                 ┌───────────────┐
│ FrontendUrl │──── CALLS ────▶│ GatewayRoute  │
└─────────────┘                 └───────┬───────┘
                                        │
                                        │ ROUTES_TO
                                        │
                                        ▼
                                ┌───────────────┐
                                │  BackendApi   │
                                └───────────────┘

┌─────────────┐   USES_MAPPING  ┌───────────────┐
│ FrontendUrl │───────────────▶│ MappingRule   │
└─────────────┘                 └───────┬───────┘
                                        │
                                        │ MAPS_TO
                                        │
                                        ▼
                                ┌───────────────┐
                                │ GatewayRoute  │
                                └───────────────┘
```

---

## Matching Strategies

### Strategy Pipeline

```
Input: FrontendUrl + [GatewayRoute] + [MappingRule]
                    │
                    ▼
          ┌─────────────────────┐
          │ 1. Mapping Match    │──▶ Match? ──▶ Return (conf=1.0)
          └─────────────────────┘      │
                    │                  │ No
                    ▼                  │
          ┌─────────────────────┐      │
          │ 2. Exact Match      │◀─────┘
          └─────────────────────┘
                    │
                    │ No match
                    ▼
          ┌─────────────────────┐
          │ 3. Normalized Match │──▶ Score >= 0.8?
          └─────────────────────┘      │
                    │                  │ Yes
                    │                  ▼
                    │            Return top matches
                    │
                    │ No
                    ▼
          ┌─────────────────────┐
          │ 4. Candidate Match  │──▶ Score >= 0.4?
          └─────────────────────┘      │
                    │                  │ Yes
                    │                  ▼
                    │            Return top 5 candidates
                    │
                    ▼
              No match found
```

### Confidence Scoring

| Strategy | Confidence | Criteria |
|----------|------------|----------|
| Mapping | 1.0 | JSON mapping rule found |
| Exact | 1.0 | method + full_path identical |
| Normalized | 0.8-1.0 | After normalization, path segments match |
| Candidate | 0.4-0.7 | Partial similarity |

### URL Normalization

```python
def normalize_url(url: str) -> str:
    """
    URL normalization pipeline:
    
    1. Strip query parameters:  /users?id=1 → /users
    2. Unify template syntax:   /users/${id} → /users/{id}
    3. Remove duplicate slashes: //users → /users
    4. Ensure leading slash:    users → /users
    """
    pass

def remove_version_prefix(url: str) -> str:
    """
    Remove version prefix for matching:
    
    /v1/users → /users
    /api/v2/users → /api/users
    """
    pass

def unify_param_names(url: str) -> str:
    """
    Unify parameter names for comparison:
    
    /users/{userId} → /users/{param1}
    /users/{id} → /users/{param1}
    
    Both become the same for matching.
    """
    pass
```

---

## Performance Considerations

### Batch Processing

```python
# Batch size for Neo4j writes
BATCH_SIZE = 500

# Avoid N+1 queries
# Bad: One query per entity
for entity in entities:
    writer.write_entity(entity)

# Good: Batch write
writer.write_entities(entities, batch_size=500)
```

### Indexing Strategy

```cypher
// Node key constraints (unique + index)
CREATE CONSTRAINT backendapi_unique
FOR (n:BackendApi)
REQUIRE (n.method, n.full_path, n.repo) IS NODE KEY

// Additional indexes for common queries
CREATE INDEX backendapi_repo_idx
FOR (n:BackendApi)
ON (n.repo)
```

### Memory Management

```python
# Process files one at a time (not all in memory)
for file_path in scan_files(repo_path):
    entities = parser.parse(file_path)
    writer.write_entities(entities)
```

### Query Optimization

```cypher
// Use indexes effectively
MATCH (n:BackendApi {repo: $repo, method: $method})
WHERE n.full_path CONTAINS '/users'
RETURN n

// Avoid full scans
// Bad:
MATCH (n:BackendApi)
WHERE n.repo = 'backend'  // Filter after scan
RETURN n

// Good:
MATCH (n:BackendApi {repo: 'backend'})  // Uses index
RETURN n
```

---

## Extensibility

### Adding a New Parser

```python
from repo_analyzer.parsers.base_parser import BaseParser
from repo_analyzer.models.entities import BackendApi

class GoParser(BaseParser):
    """Parser for Go/Gin framework."""
    
    def parse(self, file_path: str, repo: str) -> List[BackendApi]:
        content = self.get_file_content(file_path)
        # Extract APIs from Go code
        # ...
        return apis
```

### Adding a New Entity Type

```python
from dataclasses import dataclass

@dataclass
class GraphQLQuery:
    query_name: str
    repo: str
    file_path: str
    # ...
    
    def to_neo4j_dict(self):
        return {...}
    
    @classmethod
    def unique_keys(cls):
        return ["query_name", "repo"]
```

### Custom Matching Strategy

```python
from repo_analyzer.matcher.url_matcher import UrlMatcher

class CustomMatcher(UrlMatcher):
    def match_frontend_to_gateway(self, url, routes, mappings):
        # Custom logic
        results = super().match_frontend_to_gateway(url, routes, mappings)
        
        # Add custom matching
        # ...
        
        return results
```

---

## References

- [Neo4j Best Practices](https://neo4j.com/developer/best-practices/)
- [Python Project Structure](https://docs.python-guide.org/writing/structure/)
- [Semantic Versioning](https://semver.org/)
