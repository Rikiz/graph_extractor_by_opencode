import pytest
from repo_analyzer.parsers.java_parser import JavaParser


class TestJavaParser:
    def setup_method(self):
        self.parser = JavaParser()

    def test_extract_simple_get_mapping(self):
        java_code = """
@RestController
@RequestMapping("/api/v1")
public class UserController {
    
    @GetMapping("/users/{id}")
    public User getUser(@PathVariable String id) {
        return userService.findById(id);
    }
}
"""
        apis = self.parser._extract_apis(java_code, "test.java", "backend")

        assert len(apis) == 1
        assert apis[0].method == "GET"
        assert apis[0].full_path == "/api/v1/users/{id}"
        assert apis[0].class_name == "UserController"
        assert apis[0].method_name == "getUser"
        assert apis[0].parameters == ["id"]

    def test_extract_multiple_mappings(self):
        java_code = """
@RestController
public class ProductController {
    
    @PostMapping("/products")
    public Product create(@RequestBody Product p) { return p; }
    
    @GetMapping("/products/{id}")
    public Product get(@PathVariable Long id) { return null; }
    
    @DeleteMapping("/products/{id}")
    public void delete(@PathVariable Long id) {}
}
"""
        apis = self.parser._extract_apis(java_code, "test.java", "backend")

        assert len(apis) == 3
        methods = [api.method for api in apis]
        assert "POST" in methods
        assert "GET" in methods
        assert "DELETE" in methods

    def test_extract_request_mapping_with_method(self):
        java_code = """
@Controller
public class OrderController {
    
    @RequestMapping(value = "/orders", method = RequestMethod.POST)
    public Order create() { return null; }
}
"""
        apis = self.parser._extract_apis(java_code, "test.java", "backend")

        assert len(apis) == 1
        assert apis[0].method == "POST"
        assert apis[0].full_path == "/orders"

    def test_no_rest_controller(self):
        java_code = """
public class ServiceClass {
    public void doSomething() {}
}
"""
        apis = self.parser._extract_apis(java_code, "test.java", "backend")

        assert len(apis) == 0

    def test_normalize_path(self):
        assert self.parser._normalize_path("//api//users") == "/api/users"
        assert self.parser._normalize_path("api/users") == "/api/users"
        assert self.parser._normalize_path("/api/users/") == "/api/users/"
