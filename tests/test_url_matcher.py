import pytest
from repo_analyzer.matcher.url_matcher import UrlMatcher
from repo_analyzer.models.entities import FrontendUrl, GatewayRoute, BackendApi, MappingRule


class TestUrlMatcher:
    def setup_method(self):
        self.matcher = UrlMatcher()

    def test_exact_match(self):
        url = FrontendUrl(
            raw_url="/api/v1/users/{id}",
            file_path="test.ts",
            repo="frontend",
            line_number=1,
            normalized_url="/api/v1/users/{id}",
            http_method="GET",
        )

        route = GatewayRoute(method="GET", full_path="/api/v1/users/{id}", repo="gateway")

        results = self.matcher.match_frontend_to_gateway(url, [route], [])

        assert len(results) == 1
        assert results[0].match_type == "exact"
        assert results[0].confidence == 1.0

    def test_normalized_match_with_version_prefix(self):
        url = FrontendUrl(
            raw_url="/v1/users/{id}",
            file_path="test.ts",
            repo="frontend",
            line_number=1,
            normalized_url="/v1/users/{id}",
            http_method="GET",
        )

        route = GatewayRoute(method="GET", full_path="/v2/users/{id}", repo="gateway")

        results = self.matcher.match_frontend_to_gateway(url, [route], [])

        assert len(results) == 1
        assert results[0].match_type == "normalized"
        assert results[0].confidence >= 0.8

    def test_mapping_match(self):
        url = FrontendUrl(
            raw_url="/api/users/{id}",
            file_path="test.ts",
            repo="frontend",
            line_number=1,
            http_method="GET",
        )

        mapping = MappingRule(
            uri="/api/users/{id}",
            method="GET",
            repo="frontend",
            file_path="mapping.json",
            target_uri="/v2/users/{id}",
        )

        route = GatewayRoute(method="GET", full_path="/v2/users/{id}", repo="gateway")

        results = self.matcher.match_frontend_to_gateway(url, [route], [mapping])

        assert len(results) == 1
        assert results[0].match_type == "mapping"
        assert results[0].confidence == 1.0

    def test_gateway_to_backend_exact_match(self):
        route = GatewayRoute(method="GET", full_path="/api/v1/users/{id}", repo="gateway")

        api = BackendApi(
            method="GET",
            full_path="/api/v1/users/{id}",
            repo="backend",
            class_name="UserController",
            method_name="getUser",
        )

        results = self.matcher.match_gateway_to_backend(route, [api])

        assert len(results) == 1
        assert results[0].match_type == "exact"

    def test_no_match(self):
        url = FrontendUrl(
            raw_url="/completely/different/path",
            file_path="test.ts",
            repo="frontend",
            line_number=1,
            http_method="GET",
        )

        route = GatewayRoute(method="POST", full_path="/api/v1/users", repo="gateway")

        results = self.matcher.match_frontend_to_gateway(url, [route], [])

        assert len(results) == 0 or all(r.match_type == "candidate" for r in results)

    def test_normalize_url(self):
        assert self.matcher._normalize_url("/api/v1/users/${id}") == "/api/v1/users/{id}"
        assert self.matcher._normalize_url("/api/users?foo=bar") == "/api/users"

    def test_remove_version_prefix(self):
        assert self.matcher._remove_version_prefix("/v1/users") == "/users"
        assert self.matcher._remove_version_prefix("/api/v2/users") == "/api/users"
