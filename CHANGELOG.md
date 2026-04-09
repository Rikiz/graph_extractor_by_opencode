# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project structure
- Core parsers for Java, TypeScript, YAML, JSON
- Neo4j graph builder with MERGE support
- Cross-repo call analyzer
- URL matching strategies
- CLI interface
- Python API
- Unit tests
- Documentation

## [1.0.0] - 2024-01-XX

### Added
- **Core Features**
  - Two-phase architecture: single-repo graph building + cross-repo analysis
  - Multi-language support: Java (Spring Boot), TypeScript, YAML (OpenAPI/Swagger), JSON
  - Intelligent matching with confidence scoring
  - Repo isolation in single Neo4j database

- **Parsers**
  - `JavaParser`: Extract REST APIs from Spring Boot controllers
  - `YamlParser`: Parse OpenAPI 3.x and Swagger 2.x specifications
  - `TsParser`: Extract URLs from TypeScript code (string literals, template literals, HTTP calls)
  - `JsonParser`: Extract mapping rules from JSON configuration files

- **Graph Builder**
  - `GraphBuilder`: Build single-repo graphs with file scanning
  - Support for batch processing (configurable batch size)
  - Automatic constraint and index creation
  - MERGE-based writing for uniqueness

- **Cross-Repo Analyzer**
  - `CrossAnalyzer`: Analyze cross-repo relationships
  - `RepoGroup`: Manage repo groups for analysis
  - Multiple matching strategies:
    - Mapping rules (confidence=1.0)
    - Exact match (confidence=1.0)
    - Normalized match (confidence=0.8)
    - Candidate match (confidence=0.4-0.7)

- **CLI Commands**
  - `build`: Build single-repo graph
  - `group`: Manage repo groups (create, analyze, stats, list)
  - `analyze`: Execute cross-repo analysis
  - `query`: Query results (chain, unmatched-fe, unmatched-gw)

- **Node Types**
  - `BackendApi`: Java Controller methods
  - `GatewayRoute`: OpenAPI/Swagger routes
  - `FrontendUrl`: TypeScript URL references
  - `MappingRule`: JSON mapping configurations

- **Relationship Types**
  - `CALLS`: FrontendUrl -> GatewayRoute
  - `ROUTES_TO`: GatewayRoute -> BackendApi
  - `USES_MAPPING`: FrontendUrl -> MappingRule
  - `MAPS_TO`: MappingRule -> GatewayRoute

- **Documentation**
  - Comprehensive README with examples
  - API reference
  - Contributing guide
  - Code of conduct

- **Development**
  - pyproject.toml for modern Python packaging
  - Makefile for common tasks
  - Unit tests with pytest
  - Type checking with mypy
  - Code formatting with Black and Ruff
  - .gitignore for Python projects

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| 1.0.0 | 2024-01-XX | Initial release |

---

[Unreleased]: https://github.com/Rikiz/graph_extractor_by_opencode/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/Rikiz/graph_extractor_by_opencode/releases/tag/v1.0.0
