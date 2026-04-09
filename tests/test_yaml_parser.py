import pytest
from repo_analyzer.parsers.yaml_parser import YamlParser


class TestYamlParser:
    def setup_method(self):
        self.parser = YamlParser()

    def test_extract_openapi_3_routes(self):
        yaml_content = """
openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
servers:
  - url: https://api.example.com/v1
paths:
  /users/{id}:
    get:
      operationId: getUserById
      tags:
        - users
      summary: Get user by ID
      parameters:
        - name: id
          in: path
          required: true
    delete:
      operationId: deleteUser
      summary: Delete a user
  /users:
    post:
      operationId: createUser
      summary: Create a user
"""
        routes = self.parser._parse_openapi(
            __import__("yaml").safe_load(yaml_content), "openapi.yaml", "gateway"
        )

        assert len(routes) == 3

        get_route = next(r for r in routes if r.method == "GET")
        assert get_route.full_path == "/v1/users/{id}"
        assert get_route.operation_id == "getUserById"
        assert "users" in get_route.tags

    def test_extract_swagger_2_routes(self):
        yaml_content = """
swagger: "2.0"
basePath: /api/v2
paths:
  /products:
    get:
      operationId: listProducts
"""
        routes = self.parser._parse_openapi(
            __import__("yaml").safe_load(yaml_content), "swagger.yaml", "gateway"
        )

        assert len(routes) == 1
        assert routes[0].full_path == "/api/v2/products"

    def test_empty_paths(self):
        yaml_content = """
openapi: 3.0.0
paths: {}
"""
        routes = self.parser._parse_openapi(
            __import__("yaml").safe_load(yaml_content), "empty.yaml", "gateway"
        )

        assert len(routes) == 0
