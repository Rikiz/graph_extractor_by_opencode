from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class BackendApi:
    method: str
    full_path: str
    repo: str
    class_name: str
    method_name: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    parameters: List[str] = field(default_factory=list)
    deprecated: bool = False

    def to_neo4j_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "full_path": self.full_path,
            "repo": self.repo,
            "class_name": self.class_name,
            "method_name": self.method_name,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "parameters": self.parameters,
            "deprecated": self.deprecated,
        }

    @classmethod
    def unique_keys(cls) -> List[str]:
        return ["method", "full_path", "repo"]


@dataclass
class GatewayRoute:
    method: str
    full_path: str
    repo: str
    operation_id: Optional[str] = None
    file_path: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    summary: Optional[str] = None
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    deprecated: bool = False

    def to_neo4j_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "full_path": self.full_path,
            "repo": self.repo,
            "operation_id": self.operation_id,
            "file_path": self.file_path,
            "tags": self.tags,
            "summary": self.summary,
            "parameters": self.parameters,
            "deprecated": self.deprecated,
        }

    @classmethod
    def unique_keys(cls) -> List[str]:
        return ["method", "full_path", "repo"]


@dataclass
class FrontendUrl:
    raw_url: str
    file_path: str
    repo: str
    line_number: int
    normalized_url: Optional[str] = None
    http_method: Optional[str] = None
    function_name: Optional[str] = None
    is_template: bool = False
    variables: List[str] = field(default_factory=list)

    def to_neo4j_dict(self) -> Dict[str, Any]:
        return {
            "raw_url": self.raw_url,
            "file_path": self.file_path,
            "repo": self.repo,
            "line_number": self.line_number,
            "normalized_url": self.normalized_url,
            "http_method": self.http_method,
            "function_name": self.function_name,
            "is_template": self.is_template,
            "variables": self.variables,
        }

    @classmethod
    def unique_keys(cls) -> List[str]:
        return ["raw_url", "file_path", "repo"]


@dataclass
class MappingRule:
    uri: str
    method: str
    repo: str
    file_path: str
    target_uri: Optional[str] = None
    target_service: Optional[str] = None
    priority: int = 0

    def to_neo4j_dict(self) -> Dict[str, Any]:
        return {
            "uri": self.uri,
            "method": self.method,
            "repo": self.repo,
            "file_path": self.file_path,
            "target_uri": self.target_uri,
            "target_service": self.target_service,
            "priority": self.priority,
        }

    @classmethod
    def unique_keys(cls) -> List[str]:
        return ["uri", "method", "repo"]


@dataclass
class File:
    path: str
    repo: str
    language: Optional[str] = None
    lines: Optional[int] = None

    def to_neo4j_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "repo": self.repo,
            "language": self.language,
            "lines": self.lines,
        }

    @classmethod
    def unique_keys(cls) -> List[str]:
        return ["path", "repo"]


@dataclass
class Repo:
    name: str
    type: str
    path: str
    last_analyzed: Optional[str] = None

    def to_neo4j_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "path": self.path,
            "last_analyzed": self.last_analyzed,
        }

    @classmethod
    def unique_keys(cls) -> List[str]:
        return ["name"]
