import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from ..models.entities import FrontendUrl, GatewayRoute, BackendApi, MappingRule


@dataclass
class MatchResult:
    target: object
    match_type: str
    confidence: float
    match_details: str = None


class UrlMatcher:
    def __init__(self):
        pass

    def match_frontend_to_gateway(
        self, url: FrontendUrl, routes: List[GatewayRoute], mappings: List[MappingRule]
    ) -> List[MatchResult]:
        results = []

        mapping_result = self._match_via_mapping(url, mappings)
        if mapping_result:
            target_route = self._find_route_for_mapping(mapping_result, routes)
            if target_route:
                results.append(
                    MatchResult(
                        target=target_route,
                        match_type="mapping",
                        confidence=1.0,
                        match_details=f"via mapping: {mapping_result.uri} -> {mapping_result.target_uri}",
                    )
                )
                return results

        exact_results = self._exact_match(url, routes)
        if exact_results:
            return exact_results

        normalized_results = self._normalized_match(url, routes)
        if normalized_results:
            return normalized_results

        candidate_results = self._candidate_match(url, routes)
        return candidate_results

    def match_gateway_to_backend(
        self, route: GatewayRoute, apis: List[BackendApi]
    ) -> List[MatchResult]:
        results = []

        for api in apis:
            if route.method != api.method:
                continue

            if route.full_path == api.full_path:
                return [MatchResult(target=api, match_type="exact", confidence=1.0)]

        for api in apis:
            if route.method != api.method:
                continue

            score = self._path_similarity_score(route.full_path, api.full_path)
            if score >= 0.8:
                results.append(
                    MatchResult(
                        target=api,
                        match_type="normalized",
                        confidence=score,
                        match_details=f"normalized path similarity: {score:.2f}",
                    )
                )

        if results:
            return sorted(results, key=lambda x: -x.confidence)

        for api in apis:
            if route.method == api.method:
                score = self._path_similarity_score(route.full_path, api.full_path)
                if score >= 0.4:
                    results.append(
                        MatchResult(
                            target=api, match_type="candidate", confidence=score
                        )
                    )

        return sorted(results, key=lambda x: -x.confidence)[:5]

    def build_mapping_relations(
        self,
        urls: List[FrontendUrl],
        mappings: List[MappingRule],
        routes: List[GatewayRoute],
    ) -> List[Dict]:
        relations = []

        for mapping in mappings:
            for url in urls:
                if self._urls_match(url.raw_url, mapping.uri):
                    relations.append(
                        {
                            "start_node": url,
                            "end_node": mapping,
                            "relation_type": "USES_MAPPING",
                            "properties": {"match_type": "mapping", "confidence": 1.0},
                        }
                    )

            target_url = mapping.target_uri or mapping.uri
            for route in routes:
                if route.method == mapping.method:
                    if self._urls_match(route.full_path, target_url):
                        relations.append(
                            {
                                "start_node": mapping,
                                "end_node": route,
                                "relation_type": "MAPS_TO",
                                "properties": {
                                    "match_type": "mapping",
                                    "confidence": 1.0,
                                },
                            }
                        )

        return relations

    def _match_via_mapping(
        self, url: FrontendUrl, mappings: List[MappingRule]
    ) -> Optional[MappingRule]:
        for mapping in mappings:
            if self._urls_match(url.raw_url, mapping.uri):
                return mapping
        return None

    def _find_route_for_mapping(
        self, mapping: MappingRule, routes: List[GatewayRoute]
    ) -> Optional[GatewayRoute]:
        target_url = mapping.target_uri or mapping.uri
        for route in routes:
            if route.method == mapping.method:
                if self._urls_match(route.full_path, target_url):
                    return route
        return None

    def _exact_match(
        self, url: FrontendUrl, routes: List[GatewayRoute]
    ) -> List[MatchResult]:
        results = []
        url_normalized = self._normalize_url(url.normalized_url or url.raw_url)

        for route in routes:
            route_normalized = self._normalize_url(route.full_path)

            if url_normalized == route_normalized:
                if url.http_method and url.http_method != route.method:
                    continue

                results.append(
                    MatchResult(target=route, match_type="exact", confidence=1.0)
                )

        return results

    def _normalized_match(
        self, url: FrontendUrl, routes: List[GatewayRoute]
    ) -> List[MatchResult]:
        results = []

        for route in routes:
            score = self._url_similarity_score(url, route)
            if score >= 0.8:
                results.append(
                    MatchResult(
                        target=route,
                        match_type="normalized",
                        confidence=score,
                        match_details=self._get_normalization_details(url, route),
                    )
                )

        return sorted(results, key=lambda x: -x.confidence)

    def _candidate_match(
        self, url: FrontendUrl, routes: List[GatewayRoute]
    ) -> List[MatchResult]:
        results = []

        for route in routes:
            if url.http_method and url.http_method != route.method:
                continue

            score = self._url_similarity_score(url, route)
            if score >= 0.4:
                results.append(
                    MatchResult(target=route, match_type="candidate", confidence=score)
                )

        return sorted(results, key=lambda x: -x.confidence)[:5]

    def _normalize_url(self, url: str) -> str:
        if not url:
            return ""

        url = url.split("?")[0]
        url = re.sub(r"\$\{(\w+)\}", r"{\1}", url)
        url = re.sub(r":(\w+)", r"{\1}", url)
        url = re.sub(r"/+", "/", url)
        url = url.rstrip("/")

        if not url.startswith("/"):
            url = "/" + url

        return url

    def _remove_version_prefix(self, url: str) -> str:
        return re.sub(r"/v\d+", "", url)

    def _unify_param_names(self, url: str) -> str:
        count = [0]

        def replacer(match):
            count[0] += 1
            return f"{{param{count[0]}}}"

        return re.sub(r"\{(\w+)\}", replacer, url)

    def _urls_match(self, url1: str, url2: str) -> bool:
        n1 = self._normalize_url(url1)
        n2 = self._normalize_url(url2)
        return n1 == n2

    def _url_similarity_score(self, url: FrontendUrl, route: GatewayRoute) -> float:
        url_normalized = self._normalize_url(url.normalized_url or url.raw_url)
        route_normalized = self._normalize_url(route.full_path)

        url_no_version = self._remove_version_prefix(url_normalized)
        route_no_version = self._remove_version_prefix(route_normalized)

        url_unified = self._unify_param_names(url_no_version)
        route_unified = self._unify_param_names(route_no_version)

        if url_unified == route_unified:
            return 1.0

        segments1 = url_unified.split("/")
        segments2 = route_unified.split("/")

        if len(segments1) != len(segments2):
            return 0.0

        match_count = sum(1 for s1, s2 in zip(segments1, segments2) if s1 == s2)
        return match_count / len(segments1)

    def _path_similarity_score(self, path1: str, path2: str) -> float:
        n1 = self._unify_param_names(
            self._remove_version_prefix(self._normalize_url(path1))
        )
        n2 = self._unify_param_names(
            self._remove_version_prefix(self._normalize_url(path2))
        )

        if n1 == n2:
            return 1.0

        segments1 = n1.split("/")
        segments2 = n2.split("/")

        if len(segments1) != len(segments2):
            return 0.0

        match_count = 0
        for s1, s2 in zip(segments1, segments2):
            if s1 == s2:
                match_count += 1
            elif s1.startswith("{") and s2.startswith("{"):
                match_count += 1

        return match_count / len(segments1)

    def _get_normalization_details(self, url: FrontendUrl, route: GatewayRoute) -> str:
        url_norm = self._normalize_url(url.raw_url)
        route_norm = self._normalize_url(route.full_path)

        details = []
        if url_norm != url.raw_url:
            details.append(f"normalized url: {url.raw_url} -> {url_norm}")
        if route_norm != route.full_path:
            details.append(f"normalized route: {route.full_path} -> {route_norm}")

        return "; ".join(details) if details else "path normalized"
