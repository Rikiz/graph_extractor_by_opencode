import pytest
from repo_analyzer.parsers.ts_parser import TsParser


class TestTsParser:
    def setup_method(self):
        self.parser = TsParser()

    def test_extract_string_literal_urls(self):
        ts_code = """
const BASE_URL = "/api/v1/users";
const otherUrl = "/api/posts";
"""
        content = ts_code
        lines = content.split("\n")
        urls = self.parser._extract_string_literal_urls(content, lines, "test.ts", "frontend")

        assert len(urls) >= 2
        raw_urls = [u.raw_url for u in urls]
        assert "/api/v1/users" in raw_urls
        assert "/api/posts" in raw_urls

    def test_extract_template_literal_urls(self):
        ts_code = """
function getUser(userId: string) {
    return axios.get(`/api/v1/users/${userId}`);
}
"""
        content = ts_code
        lines = content.split("\n")
        urls = self.parser._extract_template_literal_urls(content, lines, "test.ts", "frontend")

        assert len(urls) == 1
        assert "/api/v1/users/${userId}" in urls[0].raw_url
        assert urls[0].is_template is True
        assert "userId" in urls[0].variables

    def test_extract_axios_calls(self):
        ts_code = """
axios.get("/api/users");
axios.post("/api/users", data);
http.delete("/api/users/123");
"""
        content = ts_code
        lines = content.split("\n")
        urls = self.parser._extract_http_call_urls(content, lines, "test.ts", "frontend")

        assert len(urls) >= 2
        methods = {u.http_method for u in urls if u.http_method}
        assert "GET" in methods or "POST" in methods

    def test_normalize_url(self):
        assert self.parser._normalize_url("/api/users?foo=bar") == "/api/users"
        assert self.parser._normalize_url("//api//users") == "/api/users"
        assert self.parser._normalize_url("api/users") == "/api/users"

    def test_infer_http_method(self):
        content = "function createUser() { return axios.post"
        method = self.parser._infer_http_method(content, len(content))
        assert method == "POST"

        content2 = "function getUsers() { return axios.get"
        method2 = self.parser._infer_http_method(content2, len(content2))
        assert method2 == "GET"
