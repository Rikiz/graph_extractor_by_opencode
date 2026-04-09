import json
import logging
from typing import List, Dict, Any, Set
from .base_parser import BaseParser
from ..models.entities import MappingRule

logger = logging.getLogger(__name__)


class JsonParser(BaseParser):
    MAPPING_PATTERNS = [
        {"uri", "method"},
        {"uri", "targetUri"},
        {"source", "target"},
        {"from", "to"},
        {"path", "targetPath"},
        {"route", "target"},
    ]

    def parse(self, file_path: str, repo: str) -> List[MappingRule]:
        try:
            content = self.get_file_content(file_path)
            data = json.loads(content)

            mappings = []
            self._search_mappings(data, file_path, repo, mappings)

            return mappings
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {file_path}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
            return []

    def _search_mappings(
        self,
        obj: Any,
        file_path: str,
        repo: str,
        mappings: List[MappingRule],
        depth: int = 0,
    ) -> None:
        if depth > 10:
            return

        if isinstance(obj, dict):
            if self._is_mapping_object(obj):
                mapping = self._create_mapping(obj, file_path, repo)
                if mapping:
                    mappings.append(mapping)

            for value in obj.values():
                self._search_mappings(value, file_path, repo, mappings, depth + 1)

        elif isinstance(obj, list):
            for item in obj:
                self._search_mappings(item, file_path, repo, mappings, depth + 1)

    def _is_mapping_object(self, obj: Dict[str, Any]) -> bool:
        obj_keys = set(obj.keys())

        for pattern in self.MAPPING_PATTERNS:
            if pattern.issubset(obj_keys):
                return True

        url_keys = obj_keys & {"uri", "url", "path", "source", "from", "route"}
        if url_keys and "method" in obj_keys:
            return True

        if url_keys and (
            "targetUri" in obj_keys or "target" in obj_keys or "targetUrl" in obj_keys
        ):
            return True

        return False

    def _create_mapping(
        self, obj: Dict[str, Any], file_path: str, repo: str
    ) -> MappingRule:
        uri = (
            obj.get("uri")
            or obj.get("url")
            or obj.get("path")
            or obj.get("source")
            or obj.get("from")
            or obj.get("route")
        )

        target = (
            obj.get("targetUri")
            or obj.get("target")
            or obj.get("targetUrl")
            or obj.get("targetPath")
            or obj.get("to")
        )

        method = obj.get("method", "GET").upper()

        if not uri:
            return None

        priority = obj.get("priority", obj.get("order", 0))
        target_service = obj.get("targetService") or obj.get("service")

        return MappingRule(
            uri=self._normalize_uri(uri),
            method=method,
            repo=repo,
            file_path=file_path,
            target_uri=self._normalize_uri(target) if target else None,
            target_service=target_service,
            priority=priority,
        )

    def _normalize_uri(self, uri: str) -> str:
        import re

        if not uri:
            return ""
        uri = re.sub(r"/+", "/", uri)
        if not uri.startswith("/"):
            uri = "/" + uri
        return uri
