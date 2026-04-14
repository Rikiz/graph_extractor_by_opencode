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

    def test_extract_interface_with_request_mapping(self):
        java_code = """
@RequestMapping("/v1/checkers-version")
public interface CheckersVersionApi {
    
    @GetMapping
    CheckersVersionResponse getCheckersVersion();
    
    @PostMapping("/update")
    void updateCheckersVersion(@RequestBody UpdateRequest request);
}
"""
        apis = self.parser._extract_apis(java_code, "test.java", "backend")

        assert len(apis) == 2
        assert apis[0].method == "GET"
        assert apis[0].full_path == "/v1/checkers-version"
        assert apis[0].class_name == "CheckersVersionApi"
        assert apis[0].method_name == "getCheckersVersion"

        assert apis[1].method == "POST"
        assert apis[1].full_path == "/v1/checkers-version/update"
        assert apis[1].method_name == "updateCheckersVersion"

    def test_extract_interface_without_public(self):
        java_code = """
@RequestMapping(value = "/v1/tenant-configs")
interface TenantConfigApi {
    
    @GetMapping
    List<TenantConfig> listConfigs();
    
    @PutMapping("/{id}")
    void updateConfig(@PathVariable String id, @RequestBody Config config);
}
"""
        apis = self.parser._extract_apis(java_code, "test.java", "backend")

        assert len(apis) == 2
        assert apis[0].method == "GET"
        assert apis[0].full_path == "/v1/tenant-configs"
        assert apis[0].class_name == "TenantConfigApi"

        assert apis[1].method == "PUT"
        assert apis[1].full_path == "/v1/tenant-configs/{id}"
        assert apis[1].method_name == "updateConfig"

    def test_extract_feign_client_interface(self):
        java_code = """
@FeignClient(name = "user-service", path = "/api/users")
public interface UserClient {
    
    @GetMapping("/{id}")
    User getUser(@PathVariable Long id);
    
    @PostMapping
    User createUser(@RequestBody User user);
}
"""
        apis = self.parser._extract_apis(java_code, "test.java", "backend")

        assert len(apis) == 2
        assert apis[0].method == "GET"
        assert apis[0].full_path == "/api/users/{id}"
        assert apis[0].class_name == "UserClient"

        assert apis[1].method == "POST"
        assert apis[1].full_path == "/api/users"
