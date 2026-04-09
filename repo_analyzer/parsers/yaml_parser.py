import yaml
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from .base_parser import BaseParser
from ..models.entities import GatewayRoute

logger = logging.getLogger(__name__)


class YamlParser(BaseParser):
    def parse(self, file_path: str, repo: str) -> List[GatewayRoute]:
        try:
            content = self.get_file_content(file_path)
            spec = yaml.safe_load(content)

            if not spec:
                return []

            if "openapi" in spec or "swagger" in spec:
                return self._parse_openapi(spec, file_path, repo)
            else:
                return []
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
            return []

    def _parse_openapi(
        self, spec: Dict[str, Any], file_path: str, repo: str
    ) -> List[GatewayRoute]:
        routes = []

        base_path = self._extract_base_path(spec)

        paths = spec.get("paths", {})

        for path, path_item in paths.items():
            for method in ["get", "post", "put", "delete", "patch", "options", "head"]:
                if method in path_item:
                    operation = path_item[method]

                    route = self._create_route(
                        operation=operation,
                        method=method,
                        path=path,
                        base_path=base_path,
                        file_path=file_path,
                        repo=repo,
                        path_item=path_item,
                    )

                    if route:
                        routes.append(route)

        return routes

    def _extract_base_path(self, spec: Dict[str, Any]) -> str:
        if "basePath" in spec:
            return spec["basePath"]

        if "servers" in spec and spec["servers"]:
            server_url = spec["servers"][0].get("url", "")
            parsed = urlparse(server_url)
            return parsed.path if parsed.path else ""

        return ""

    def _create_route(
        self,
        operation: Dict[str, Any],
        method: str,
        path: str,
        base_path: str,
        file_path: str,
        repo: str,
        path_item: Dict[str, Any],
    ) -> Optional[GatewayRoute]:
        full_path = self._normalize_path(base_path + path)

        operation_id = operation.get("operationId")
        tags = operation.get("tags", [])
        summary = operation.get("summary")
        deprecated = operation.get("deprecated", False)

        parameters = self._extract_parameters(operation, path_item)

        return GatewayRoute(
            method=method.upper(),
            full_path=full_path,
            repo=repo,
            operation_id=operation_id,
            file_path=file_path,
            tags=tags,
            summary=summary,
            parameters=parameters,
            deprecated=deprecated,
        )

    def _extract_parameters(
        self, operation: Dict[str, Any], path_item: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        params = []

        all_params = operation.get("parameters", []) + path_item.get("parameters", [])

        for param in all_params:
            if isinstance(param, dict):
                params.append(
                    {
                        "name": param.get("name"),
                        "in": param.get("in"),
                        "required": param.get("required", False),
                        "schema": param.get("schema", {}),
                    }
                )

        return params

    def _normalize_path(self, path: str) -> str:
        import re

        path = re.sub(r"/+", "/", path)
        if not path.startswith("/"):
            path = "/" + path
        return path
