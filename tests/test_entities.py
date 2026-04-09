import pytest
from repo_analyzer.models.entities import BackendApi, GatewayRoute, FrontendUrl, MappingRule


class TestBackendApi:
    def test_create_backend_api(self):
        api = BackendApi(
            method="GET",
            full_path="/api/v1/users/{id}",
            repo="backend",
            class_name="UserController",
            method_name="getUser",
        )

        assert api.method == "GET"
        assert api.full_path == "/api/v1/users/{id}"
        assert api.repo == "backend"
        assert api.parameters == []

    def test_to_neo4j_dict(self):
        api = BackendApi(
            method="POST",
            full_path="/api/users",
            repo="backend",
            class_name="UserController",
            method_name="createUser",
            parameters=["name", "email"],
        )

        result = api.to_neo4j_dict()

        assert result["method"] == "POST"
        assert result["full_path"] == "/api/users"
        assert result["repo"] == "backend"
        assert result["class_name"] == "UserController"
        assert result["method_name"] == "createUser"
        assert result["parameters"] == ["name", "email"]

    def test_unique_keys(self):
        assert BackendApi.unique_keys() == ["method", "full_path", "repo"]


class TestGatewayRoute:
    def test_create_gateway_route(self):
        route = GatewayRoute(
            method="GET",
            full_path="/v1/users/{id}",
            repo="gateway",
            operation_id="getUserById",
            tags=["users"],
        )

        assert route.method == "GET"
        assert route.full_path == "/v1/users/{id}"
        assert route.operation_id == "getUserById"
        assert route.tags == ["users"]

    def test_to_neo4j_dict(self):
        route = GatewayRoute(
            method="DELETE",
            full_path="/v1/users/{id}",
            repo="gateway",
            operation_id="deleteUser",
            summary="Delete a user",
        )

        result = route.to_neo4j_dict()

        assert result["method"] == "DELETE"
        assert result["summary"] == "Delete a user"


class TestFrontendUrl:
    def test_create_frontend_url(self):
        url = FrontendUrl(
            raw_url="/api/v1/users/${userId}",
            file_path="src/services/userService.ts",
            repo="frontend",
            line_number=23,
            is_template=True,
            variables=["userId"],
        )

        assert url.raw_url == "/api/v1/users/${userId}"
        assert url.is_template is True
        assert url.variables == ["userId"]

    def test_unique_keys(self):
        assert FrontendUrl.unique_keys() == ["raw_url", "file_path", "repo"]


class TestMappingRule:
    def test_create_mapping_rule(self):
        mapping = MappingRule(
            uri="/api/v1/users/{id}",
            method="GET",
            repo="frontend",
            file_path="config/routeMapping.json",
            target_uri="/v2/users/{id}",
        )

        assert mapping.uri == "/api/v1/users/{id}"
        assert mapping.target_uri == "/v2/users/{id}"
