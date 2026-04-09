import os
import glob
import logging
from typing import List, Dict, Optional
from collections import defaultdict

from ..writer.neo4j_writer import Neo4jWriter
from ..models.entities import BackendApi, GatewayRoute, FrontendUrl, MappingRule, Repo
from ..parsers.java_parser import JavaParser
from ..parsers.yaml_parser import YamlParser
from ..parsers.ts_parser import TsParser
from ..parsers.json_parser import JsonParser

logger = logging.getLogger(__name__)


class GraphBuilder:
    FILE_PATTERNS = {
        "backend": ["**/*.java"],
        "gateway": ["**/*.yaml", "**/*.yml"],
        "frontend": ["**/*.ts", "**/*.tsx", "**/*.json"],
    }

    def __init__(self, writer: Neo4jWriter):
        self.writer = writer

        self.parsers = {
            "backend": JavaParser(),
            "gateway": YamlParser(),
            "frontend": None,
        }

    def build_repo_graph(
        self, repo_name: str, repo_path: str, repo_type: str
    ) -> Dict[str, int]:
        if repo_type not in self.FILE_PATTERNS:
            raise ValueError(f"Invalid repo_type: {repo_type}")

        if not os.path.exists(repo_path):
            raise ValueError(f"Repo path not found: {repo_path}")

        logger.info(
            f"Building graph for repo '{repo_name}' ({repo_type}) from {repo_path}"
        )

        files = self._scan_files(repo_path, repo_type)
        logger.info(f"Found {len(files)} files to process")

        entities = self._parse_files(files, repo_name, repo_type)
        logger.info(f"Extracted {len(entities)} entities")

        stats = self.writer.write_entities(entities)
        logger.info(f"Written to Neo4j: {stats}")

        repo = Repo(name=repo_name, type=repo_type, path=repo_path)
        self.writer.create_repo_node(repo)

        return stats

    def _scan_files(self, repo_path: str, repo_type: str) -> List[str]:
        files = []
        patterns = self.FILE_PATTERNS[repo_type]

        for pattern in patterns:
            matched = glob.glob(os.path.join(repo_path, pattern), recursive=True)
            files.extend(matched)

        return list(set(files))

    def _parse_files(self, files: List[str], repo_name: str, repo_type: str) -> List:
        entities = []

        if repo_type == "frontend":
            ts_parser = TsParser()
            json_parser = JsonParser()

            for file_path in files:
                if file_path.endswith((".ts", ".tsx")):
                    parsed = ts_parser.parse(file_path, repo_name)
                    entities.extend(parsed)
                elif file_path.endswith(".json"):
                    parsed = json_parser.parse(file_path, repo_name)
                    entities.extend(parsed)
        else:
            parser = self.parsers[repo_type]

            for file_path in files:
                parsed = parser.parse(file_path, repo_name)
                entities.extend(parsed)

        return entities

    def rebuild_repo(
        self, repo_name: str, repo_path: str, repo_type: str
    ) -> Dict[str, int]:
        logger.info(f"Clearing existing data for repo '{repo_name}'")
        deleted = self.writer.clear_repo(repo_name)
        logger.info(f"Deleted {deleted} nodes")

        return self.build_repo_graph(repo_name, repo_path, repo_type)

    def get_repo_stats(self, repo_name: str) -> Dict[str, int]:
        stats = {}

        for label in ["BackendApi", "GatewayRoute", "FrontendUrl", "MappingRule"]:
            entities = self.writer.get_entities(label, repo_name)
            if entities:
                stats[label] = len(entities)

        return stats
