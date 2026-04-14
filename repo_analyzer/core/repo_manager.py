import logging
from typing import List, Dict, Optional
from datetime import datetime

from ..writer.neo4j_writer import Neo4jWriter
from ..models.entities import Repo
from .cross_analyzer import CrossAnalyzer

logger = logging.getLogger(__name__)


class RepoGroup:
    def __init__(self, writer: Neo4jWriter):
        self.writer = writer
        self.cross_analyzer = CrossAnalyzer(writer)

    def create_group(self, name: str, repos: List[str]) -> None:
        query = """
        MERGE (group:RepoGroup {name: $name})
        SET group.repos = $repos,
            group.created_at = datetime(),
            group.status = 'created'
        """

        self.writer.execute(query, {"name": name, "repos": repos})
        logger.info(f"Created RepoGroup '{name}' with repos: {repos}")

    def get_group(self, name: str) -> Optional[Dict]:
        query = """
        MATCH (g:RepoGroup {name: $name})
        RETURN g
        """

        result = self.writer.execute(query, {"name": name})

        if result:
            return dict(result[0]["g"])
        return None

    def list_groups(self) -> List[Dict]:
        query = """
        MATCH (g:RepoGroup)
        RETURN g.name as name, g.repos as repos, g.status as status
        ORDER BY g.created_at DESC
        """

        return self.writer.execute(query)

    def analyze_group(self, name: str) -> Dict:
        group = self.get_group(name)

        if not group:
            raise ValueError(f"RepoGroup '{name}' not found")

        repos = group.get("repos", [])

        if not repos:
            raise ValueError(f"RepoGroup '{name}' has no repos defined")

        for repo in repos:
            if not self.writer.repo_exists(repo):
                raise ValueError(f"Repo '{repo}' not found. Run build_repo_graph first.")

        logger.info(f"Analyzing RepoGroup '{name}' with repos: {repos}")

        results = self.cross_analyzer.analyze(repos)

        self._update_group_status(name, "analyzed", results)

        return results

    def get_group_stats(self, name: str) -> Dict:
        group = self.get_group(name)

        if not group:
            raise ValueError(f"RepoGroup '{name}' not found")

        stats = {
            "name": name,
            "repos": group.get("repos", []),
            "status": group.get("status"),
            "relations": {},
        }

        query = """
        MATCH ()-[r:CALLS|ROUTES_TO|USES_MAPPING|MAPS_TO]->()
        WHERE startNode(r).repo IN $repos OR endNode(r).repo IN $repos
        RETURN type(r) as rel_type, count(r) as count
        """

        result = self.writer.execute(query, {"repos": stats["repos"]})

        for row in result:
            stats["relations"][row["rel_type"]] = row["count"]

        stats["total_relations"] = sum(stats["relations"].values())

        return stats

    def get_call_chain(self, group_name: str, limit: int = 100) -> List[Dict]:
        query = """
        // 路径1: 直接 CALLS 关系
        MATCH (url:FrontendUrl)-[c:CALLS]->(route:GatewayRoute)-[r:ROUTES_TO]->(api:BackendApi)
        RETURN url.raw_url as frontend_url,
               route.full_path as gateway_path,
               api.class_name as backend_class,
               api.method_name as backend_method,
               c.match_type as frontend_match_type,
               c.confidence as frontend_confidence,
               r.match_type as gateway_match_type,
               r.confidence as gateway_confidence
        
        UNION
        
        // 路径2: 通过 MappingRule 间接连接
        MATCH (url:FrontendUrl)-[um:USES_MAPPING]->(mapping:MappingRule)-[mt:MAPS_TO]->(route:GatewayRoute)-[r:ROUTES_TO]->(api:BackendApi)
        RETURN url.raw_url as frontend_url,
               route.full_path as gateway_path,
               api.class_name as backend_class,
               api.method_name as backend_method,
               um.match_type as frontend_match_type,
               um.confidence as frontend_confidence,
               r.match_type as gateway_match_type,
               r.confidence as gateway_confidence
        
        LIMIT $limit
        """

        return self.writer.execute(query, {"limit": limit})

    def get_unmatched_frontend_urls(self) -> List[Dict]:
        query = """
        MATCH (url:FrontendUrl)
        WHERE NOT (url)-[:CALLS]->(:GatewayRoute) AND NOT (url)-[:USES_MAPPING]->(:MappingRule)
        RETURN url.raw_url as url, url.file_path as file_path, url.line_number as line
        """

        return self.writer.execute(query)

    def get_unmatched_gateway_routes(self) -> List[Dict]:
        query = """
        MATCH (route:GatewayRoute)
        WHERE NOT (route)-[:ROUTES_TO]->(:BackendApi)
        RETURN route.full_path as path, route.method as method, route.operation_id as operation_id
        """

        return self.writer.execute(query)

    def delete_group(self, name: str) -> bool:
        group = self.get_group(name)

        if not group:
            return False

        query = """
        MATCH (g:RepoGroup {name: $name})
        DETACH DELETE g
        """

        self.writer.execute(query, {"name": name})
        logger.info(f"Deleted RepoGroup '{name}'")

        return True

    def _update_group_status(self, name: str, status: str, results: Dict = None) -> None:
        query = """
        MATCH (g:RepoGroup {name: $name})
        SET g.status = $status,
            g.last_analyzed = datetime(),
            g.analysis_results = $results
        """

        self.writer.execute(query, {"name": name, "status": status, "results": results or {}})
