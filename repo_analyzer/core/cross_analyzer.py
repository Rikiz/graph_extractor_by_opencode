import logging
from typing import List, Dict
from collections import defaultdict

from ..writer.neo4j_writer import Neo4jWriter
from ..models.entities import FrontendUrl, GatewayRoute, BackendApi, MappingRule
from ..matcher.url_matcher import UrlMatcher, MatchResult

logger = logging.getLogger(__name__)


class CrossAnalyzer:
    def __init__(self, writer: Neo4jWriter):
        self.writer = writer
        self.matcher = UrlMatcher()

    def analyze(self, repos: List[str]) -> Dict[str, int]:
        if not self._validate_repos(repos):
            raise ValueError("Not all repos have been built. Run build_repo_graph first.")

        logger.info(f"Starting cross-repo analysis for repos: {repos}")

        results = {
            "frontend_to_gateway": 0,
            "gateway_to_backend": 0,
            "mapping_relations": 0,
        }

        results["frontend_to_gateway"] = self._analyze_frontend_to_gateway()
        logger.info(f"Frontend -> Gateway relations: {results['frontend_to_gateway']}")

        results["gateway_to_backend"] = self._analyze_gateway_to_backend()
        logger.info(f"Gateway -> Backend relations: {results['gateway_to_backend']}")

        results["mapping_relations"] = self._analyze_mapping_relations()
        logger.info(f"Mapping relations: {results['mapping_relations']}")

        logger.info(f"Cross-repo analysis complete: {results}")
        return results

    def _validate_repos(self, repos: List[str]) -> bool:
        for repo in repos:
            if not self.writer.repo_exists(repo):
                logger.error(f"Repo '{repo}' does not exist in Neo4j")
                return False
        return True

    def _analyze_frontend_to_gateway(self) -> int:
        frontend_urls = self._load_frontend_urls()
        gateway_routes = self._load_gateway_routes()
        mappings = self._load_mappings()

        if not frontend_urls:
            logger.warning("No FrontendUrl entities found")
            return 0

        if not gateway_routes:
            logger.warning("No GatewayRoute entities found")
            return 0

        logger.info(
            f"Matching {len(frontend_urls)} frontend URLs to {len(gateway_routes)} gateway routes"
        )

        relation_count = 0

        for url in frontend_urls:
            matches = self.matcher.match_frontend_to_gateway(url, gateway_routes, mappings)

            for match in matches:
                self.writer.write_calls_relation(
                    url=url,
                    route=match.target,
                    match_type=match.match_type,
                    confidence=match.confidence,
                    match_details=match.match_details,
                )
                relation_count += 1

        return relation_count

    def _analyze_gateway_to_backend(self) -> int:
        gateway_routes = self._load_gateway_routes()
        backend_apis = self._load_backend_apis()

        if not gateway_routes:
            logger.warning("No GatewayRoute entities found")
            return 0

        if not backend_apis:
            logger.warning("No BackendApi entities found")
            return 0

        logger.info(
            f"Matching {len(gateway_routes)} gateway routes to {len(backend_apis)} backend APIs"
        )

        relation_count = 0

        for route in gateway_routes:
            matches = self.matcher.match_gateway_to_backend(route, backend_apis)

            for match in matches:
                self.writer.write_routes_to_relation(
                    route=route,
                    api=match.target,
                    match_type=match.match_type,
                    confidence=match.confidence,
                )
                relation_count += 1

        return relation_count

    def _analyze_mapping_relations(self) -> int:
        frontend_urls = self._load_frontend_urls()
        mappings = self._load_mappings()
        gateway_routes = self._load_gateway_routes()

        if not mappings:
            return 0

        logger.info(f"Building mapping relations for {len(mappings)} mappings")

        relations = self.matcher.build_mapping_relations(frontend_urls, mappings, gateway_routes)

        count = self.writer.write_relations_batch(relations)

        return count

    def _load_frontend_urls(self) -> List[FrontendUrl]:
        entities = self.writer.get_entities("FrontendUrl", "frontend")
        return [self._dict_to_frontend_url(e) for e in entities]

    def _load_gateway_routes(self) -> List[GatewayRoute]:
        entities = self.writer.get_entities("GatewayRoute", "gateway")
        return [self._dict_to_gateway_route(e) for e in entities]

    def _load_backend_apis(self) -> List[BackendApi]:
        entities = self.writer.get_entities("BackendApi", "backend")
        return [self._dict_to_backend_api(e) for e in entities]

    def _load_mappings(self) -> List[MappingRule]:
        entities = self.writer.get_entities("MappingRule", "frontend")
        return [self._dict_to_mapping_rule(e) for e in entities]

    def _dict_to_frontend_url(self, d: Dict) -> FrontendUrl:
        return FrontendUrl(
            raw_url=d["raw_url"],
            file_path=d["file_path"],
            repo=d["repo"],
            line_number=d.get("line_number", 0),
            normalized_url=d.get("normalized_url"),
            http_method=d.get("http_method"),
            function_name=d.get("function_name"),
            is_template=d.get("is_template", False),
            variables=d.get("variables", []),
        )

    def _dict_to_gateway_route(self, d: Dict) -> GatewayRoute:
        import json

        parameters = d.get("parameters", [])
        if isinstance(parameters, str):
            try:
                parameters = json.loads(parameters)
            except json.JSONDecodeError:
                parameters = []

        return GatewayRoute(
            method=d["method"],
            full_path=d["full_path"],
            repo=d["repo"],
            operation_id=d.get("operation_id"),
            file_path=d.get("file_path"),
            tags=d.get("tags", []),
            summary=d.get("summary"),
            parameters=parameters,
            deprecated=d.get("deprecated", False),
        )

    def _dict_to_backend_api(self, d: Dict) -> BackendApi:
        return BackendApi(
            method=d["method"],
            full_path=d["full_path"],
            repo=d["repo"],
            class_name=d["class_name"],
            method_name=d["method_name"],
            file_path=d.get("file_path"),
            line_number=d.get("line_number"),
            parameters=d.get("parameters", []),
            deprecated=d.get("deprecated", False),
        )

    def _dict_to_mapping_rule(self, d: Dict) -> MappingRule:
        return MappingRule(
            uri=d["uri"],
            method=d["method"],
            repo=d["repo"],
            file_path=d["file_path"],
            target_uri=d.get("target_uri"),
            target_service=d.get("target_service"),
            priority=d.get("priority", 0),
        )
