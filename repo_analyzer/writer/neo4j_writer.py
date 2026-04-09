from neo4j import GraphDatabase
from typing import List, Dict, Any, Optional
from collections import defaultdict
import logging

from ..config.neo4j_config import Neo4jConfig
from ..models.entities import BackendApi, GatewayRoute, FrontendUrl, MappingRule, File, Repo


logger = logging.getLogger(__name__)


class Neo4jWriter:
    def __init__(self, config: Neo4jConfig):
        self.config = config
        logger.info(f"Connecting to Neo4j at {config.uri}")
        self.driver = GraphDatabase.driver(config.uri, auth=(config.user, config.password))

    @classmethod
    def from_config(cls) -> "Neo4jWriter":
        """自动检测配置（环境变量 > 配置文件 > 默认值）"""
        config = Neo4jConfig.auto_detect()
        return cls(config)

    @classmethod
    def from_file(cls, config_path: str) -> "Neo4jWriter":
        config = Neo4jConfig.from_file(config_path)
        return cls(config)

    def close(self):
        self.driver.close()

    def create_unique_constraints(self) -> None:
        constraints = [
            ("BackendApi", ["method", "full_path", "repo"]),
            ("GatewayRoute", ["method", "full_path", "repo"]),
            ("FrontendUrl", ["raw_url", "file_path", "repo"]),
            ("MappingRule", ["uri", "method", "repo"]),
            ("File", ["path", "repo"]),
            ("Repo", ["name"]),
        ]

        with self.driver.session(database=self.config.database) as session:
            for label, keys in constraints:
                constraint_name = f"{label.lower()}_unique"
                key_props = " AND ".join([f"n.{k} IS NOT NULL" for k in keys])

                try:
                    key_list = ", ".join([f"n.{k}" for k in keys])
                    query = (
                        f"CREATE CONSTRAINT {constraint_name} IF NOT EXISTS "
                        f"FOR (n:{label}) "
                        f"REQUIRE ({key_list}) IS NODE KEY"
                    )
                    session.run(query)
                    logger.info(f"Created constraint: {constraint_name}")
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        logger.warning(f"Constraint {constraint_name}: {e}")

    def create_indexes(self) -> None:
        indexes = [
            ("BackendApi", "repo"),
            ("GatewayRoute", "repo"),
            ("FrontendUrl", "repo"),
            ("MappingRule", "repo"),
            ("BackendApi", "method"),
            ("BackendApi", "full_path"),
        ]

        with self.driver.session(database=self.config.database) as session:
            for label, prop in indexes:
                index_name = f"{label.lower()}_{prop}_idx"
                try:
                    query = f"CREATE INDEX {index_name} IF NOT EXISTS FOR (n:{label}) ON (n.{prop})"
                    session.run(query)
                    logger.debug(f"Created index: {index_name}")
                except Exception as e:
                    logger.debug(f"Index {index_name}: {e}")

    def write_entities(self, entities: List, batch_size: int = 500) -> Dict[str, int]:
        stats = defaultdict(int)

        if not entities:
            return dict(stats)

        with self.driver.session(database=self.config.database) as session:
            for i in range(0, len(entities), batch_size):
                batch = entities[i : i + batch_size]

                for entity in batch:
                    label = entity.__class__.__name__
                    self._write_entity(session, entity)
                    stats[label] += 1

        return dict(stats)

    def _write_entity(self, session, entity) -> None:
        label = entity.__class__.__name__
        unique_keys = entity.unique_keys()
        props = entity.to_neo4j_dict()

        merge_keys = ", ".join([f"{k}: ${k}" for k in unique_keys])

        query = f"MERGE (n:{label} {{{merge_keys}}}) SET n += $props"

        params = {k: props[k] for k in unique_keys}
        params["props"] = props

        session.run(query, params)

    def write_backend_api(self, api: BackendApi) -> None:
        with self.driver.session(database=self.config.database) as session:
            self._write_backend_api(session, api)

    def _write_backend_api(self, session, api: BackendApi) -> None:
        query = """
        MERGE (api:BackendApi {
            method: $method,
            full_path: $full_path,
            repo: $repo
        })
        SET api.class_name = $class_name,
            api.method_name = $method_name,
            api.file_path = $file_path,
            api.line_number = $line_number,
            api.parameters = $parameters,
            api.deprecated = $deprecated
        """
        session.run(query, api.to_neo4j_dict())

    def write_gateway_route(self, route: GatewayRoute) -> None:
        with self.driver.session(database=self.config.database) as session:
            self._write_gateway_route(session, route)

    def _write_gateway_route(self, session, route: GatewayRoute) -> None:
        query = """
        MERGE (route:GatewayRoute {
            method: $method,
            full_path: $full_path,
            repo: $repo
        })
        SET route.operation_id = $operation_id,
            route.file_path = $file_path,
            route.tags = $tags,
            route.summary = $summary,
            route.parameters = $parameters,
            route.deprecated = $deprecated
        """
        session.run(query, route.to_neo4j_dict())

    def write_frontend_url(self, url: FrontendUrl) -> None:
        with self.driver.session(database=self.config.database) as session:
            self._write_frontend_url(session, url)

    def _write_frontend_url(self, session, url: FrontendUrl) -> None:
        query = """
        MERGE (url:FrontendUrl {
            raw_url: $raw_url,
            file_path: $file_path,
            repo: $repo
        })
        SET url.normalized_url = $normalized_url,
            url.http_method = $http_method,
            url.function_name = $function_name,
            url.is_template = $is_template,
            url.variables = $variables,
            url.line_number = $line_number
        """
        session.run(query, url.to_neo4j_dict())

    def write_mapping_rule(self, mapping: MappingRule) -> None:
        with self.driver.session(database=self.config.database) as session:
            self._write_mapping_rule(session, mapping)

    def _write_mapping_rule(self, session, mapping: MappingRule) -> None:
        query = """
        MERGE (mapping:MappingRule {
            uri: $uri,
            method: $method,
            repo: $repo
        })
        SET mapping.file_path = $file_path,
            mapping.target_uri = $target_uri,
            mapping.target_service = $target_service,
            mapping.priority = $priority
        """
        session.run(query, mapping.to_neo4j_dict())

    def create_repo_node(self, repo: Repo) -> None:
        with self.driver.session(database=self.config.database) as session:
            query = """
            MERGE (r:Repo {name: $name})
            SET r.type = $type,
                r.path = $path,
                r.last_analyzed = $last_analyzed
            """
            session.run(query, repo.to_neo4j_dict())

    def get_entities(self, label: str, repo: str) -> List[Dict]:
        query = f"MATCH (n:{label} {{repo: $repo}}) RETURN n"
        with self.driver.session(database=self.config.database) as session:
            result = session.run(query, {"repo": repo})
            return [dict(record["n"]) for record in result]

    def get_all_entities(self, repo: str) -> Dict[str, List[Dict]]:
        labels = ["BackendApi", "GatewayRoute", "FrontendUrl", "MappingRule"]
        result = {}

        for label in labels:
            entities = self.get_entities(label, repo)
            if entities:
                result[label] = entities

        return result

    def write_calls_relation(
        self,
        url: FrontendUrl,
        route: GatewayRoute,
        match_type: str,
        confidence: float,
        match_details: str = None,
    ) -> None:
        query = """
        MATCH (url:FrontendUrl {
            raw_url: $url_raw_url,
            file_path: $url_file_path,
            repo: $url_repo
        })
        MATCH (route:GatewayRoute {
            method: $route_method,
            full_path: $route_full_path,
            repo: $route_repo
        })
        MERGE (url)-[r:CALLS]->(route)
        SET r.match_type = $match_type,
            r.confidence = $confidence,
            r.match_details = $match_details
        """

        params = {
            "url_raw_url": url.raw_url,
            "url_file_path": url.file_path,
            "url_repo": url.repo,
            "route_method": route.method,
            "route_full_path": route.full_path,
            "route_repo": route.repo,
            "match_type": match_type,
            "confidence": confidence,
            "match_details": match_details,
        }

        with self.driver.session(database=self.config.database) as session:
            session.run(query, params)

    def write_routes_to_relation(
        self, route: GatewayRoute, api: BackendApi, match_type: str, confidence: float
    ) -> None:
        query = """
        MATCH (route:GatewayRoute {
            method: $route_method,
            full_path: $route_full_path,
            repo: $route_repo
        })
        MATCH (api:BackendApi {
            method: $api_method,
            full_path: $api_full_path,
            repo: $api_repo
        })
        MERGE (route)-[r:ROUTES_TO]->(api)
        SET r.match_type = $match_type,
            r.confidence = $confidence
        """

        params = {
            "route_method": route.method,
            "route_full_path": route.full_path,
            "route_repo": route.repo,
            "api_method": api.method,
            "api_full_path": api.full_path,
            "api_repo": api.repo,
            "match_type": match_type,
            "confidence": confidence,
        }

        with self.driver.session(database=self.config.database) as session:
            session.run(query, params)

    def write_uses_mapping_relation(self, url: FrontendUrl, mapping: MappingRule) -> None:
        query = """
        MATCH (url:FrontendUrl {
            raw_url: $url_raw_url,
            file_path: $url_file_path,
            repo: $url_repo
        })
        MATCH (mapping:MappingRule {
            uri: $mapping_uri,
            method: $mapping_method,
            repo: $mapping_repo
        })
        MERGE (url)-[r:USES_MAPPING]->(mapping)
        SET r.match_type = 'mapping',
            r.confidence = 1.0
        """

        params = {
            "url_raw_url": url.raw_url,
            "url_file_path": url.file_path,
            "url_repo": url.repo,
            "mapping_uri": mapping.uri,
            "mapping_method": mapping.method,
            "mapping_repo": mapping.repo,
        }

        with self.driver.session(database=self.config.database) as session:
            session.run(query, params)

    def write_maps_to_relation(self, mapping: MappingRule, route: GatewayRoute) -> None:
        query = """
        MATCH (mapping:MappingRule {
            uri: $mapping_uri,
            method: $mapping_method,
            repo: $mapping_repo
        })
        MATCH (route:GatewayRoute {
            method: $route_method,
            full_path: $route_full_path,
            repo: $route_repo
        })
        MERGE (mapping)-[r:MAPS_TO]->(route)
        SET r.match_type = 'mapping',
            r.confidence = 1.0
        """

        params = {
            "mapping_uri": mapping.uri,
            "mapping_method": mapping.method,
            "mapping_repo": mapping.repo,
            "route_method": route.method,
            "route_full_path": route.full_path,
            "route_repo": route.repo,
        }

        with self.driver.session(database=self.config.database) as session:
            session.run(query, params)

    def write_relations_batch(self, relations: List[Dict]) -> int:
        count = 0

        with self.driver.session(database=self.config.database) as session:
            for rel in relations:
                rel_type = rel["relation_type"]
                start_node = rel["start_node"]
                end_node = rel["end_node"]
                props = rel.get("properties", {})

                start_label = start_node.__class__.__name__
                end_label = end_node.__class__.__name__

                start_keys = start_node.unique_keys()
                end_keys = end_node.unique_keys()

                start_match = " AND ".join([f"start.{k} = $start_{k}" for k in start_keys])
                end_match = " AND ".join([f"end.{k} = $end_{k}" for k in end_keys])

                query = (
                    f"MATCH (start:{start_label}), (end:{end_label}) "
                    f"WHERE {start_match} AND {end_match} "
                    f"MERGE (start)-[r:{rel_type}]->(end) "
                    f"SET r += $props"
                )

                params = {}
                start_props = start_node.to_neo4j_dict()
                end_props = end_node.to_neo4j_dict()

                for k in start_keys:
                    params[f"start_{k}"] = start_props[k]
                for k in end_keys:
                    params[f"end_{k}"] = end_props[k]
                params["props"] = props

                session.run(query, params)
                count += 1

        return count

    def repo_exists(self, repo_name: str) -> bool:
        query = """
        MATCH (n {repo: $repo_name})
        RETURN count(n) > 0 as exists
        """
        with self.driver.session(database=self.config.database) as session:
            result = session.run(query, {"repo_name": repo_name})
            return result.single()["exists"]

    def get_relation_stats(self, repo: str) -> Dict[str, int]:
        query = """
        MATCH (n {repo: $repo})-[r]->(m)
        RETURN type(r) as rel_type, count(r) as count
        """
        stats = {}
        with self.driver.session(database=self.config.database) as session:
            result = session.run(query, {"repo": repo})
            for record in result:
                stats[record["rel_type"]] = record["count"]
        return stats

    def clear_repo(self, repo_name: str) -> int:
        query = """
        MATCH (n {repo: $repo_name})
        DETACH DELETE n
        RETURN count(n) as deleted
        """
        with self.driver.session(database=self.config.database) as session:
            result = session.run(query, {"repo_name": repo_name})
            return result.single()["deleted"]

    def execute(self, query: str, params: Dict = None) -> List[Dict]:
        with self.driver.session(database=self.config.database) as session:
            result = session.run(query, params or {})
            return [dict(record) for record in result]
