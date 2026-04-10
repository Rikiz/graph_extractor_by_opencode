"""
测试 Java 解析器

验证各种 Java Controller 格式的解析。
"""

import pytest
from repo_analyzer.parsers.java_parser import JavaParser


class TestJavaParserExtended:
    def setup_method(self):
        self.parser = JavaParser()

    def test_simple_rest_controller(self):
        """测试简单的 @RestController"""
        java_code = """
@RestController
public class UserController {
    
    @GetMapping("/users")
    public List<User> getAllUsers() {
        return userService.findAll();
    }
    
    @GetMapping("/users/{id}")
    public User getUser(@PathVariable Long id) {
        return userService.findById(id);
    }
    
    @PostMapping("/users")
    public User createUser(@RequestBody User user) {
        return userService.save(user);
    }
}
"""
        apis = self.parser._extract_apis(java_code, "test.java", "backend")

        assert len(apis) == 3

        # 检查第一个 API
        assert apis[0].method == "GET"
        assert apis[0].full_path == "/users"
        assert apis[0].class_name == "UserController"

        # 检查带路径参数的 API
        assert apis[1].method == "GET"
        assert apis[1].full_path == "/users/{id}"
        assert apis[1].parameters == ["id"]

        # 检查 POST
        assert apis[2].method == "POST"

    def test_controller_with_request_mapping(self):
        """测试带有 @RequestMapping 的类"""
        java_code = """
@Controller
@RequestMapping("/api/v1")
public class ProductController {
    
    @GetMapping("/products")
    public List<Product> getProducts() { return null; }
    
    @PostMapping(value = "/products")
    public Product createProduct() { return null; }
}
"""
        apis = self.parser._extract_apis(java_code, "test.java", "backend")

        assert len(apis) == 2
        assert apis[0].full_path == "/api/v1/products"
        assert apis[1].method == "POST"

    def test_request_mapping_with_method(self):
        """测试 @RequestMapping 带有 method 属性"""
        java_code = """
@RestController
public class OrderController {
    
    @RequestMapping(value = "/orders", method = RequestMethod.GET)
    public List<Order> getOrders() { return null; }
    
    @RequestMapping(value = "/orders", method = RequestMethod.POST)
    public Order createOrder() { return null; }
    
    @RequestMapping("/orders/{id}")
    public Order getOrder(@PathVariable Long id) { return null; }
}
"""
        apis = self.parser._extract_apis(java_code, "test.java", "backend")

        assert len(apis) >= 2

        get_orders = next((a for a in apis if a.method == "GET" and "orders" in a.full_path), None)
        post_orders = next((a for a in apis if a.method == "POST"), None)

        assert get_orders is not None
        assert post_orders is not None

    def test_multiple_annotations_on_class(self):
        """测试类上有多个注解"""
        java_code = """
@RestController
@RequestMapping("/api")
@CrossOrigin
@Slf4j
public class ServiceController {
    
    @GetMapping("/health")
    public String health() { return "OK"; }
}
"""
        apis = self.parser._extract_apis(java_code, "test.java", "backend")

        assert len(apis) == 1
        assert apis[0].full_path == "/api/health"

    def test_delete_and_put_mappings(self):
        """测试 DELETE 和 PUT"""
        java_code = """
@RestController
public class ItemController {
    
    @PutMapping("/items/{id}")
    public Item updateItem(@PathVariable Long id) { return null; }
    
    @DeleteMapping("/items/{id}")
    public void deleteItem(@PathVariable Long id) {}
    
    @PatchMapping("/items/{id}")
    public Item patchItem(@PathVariable Long id) { return null; }
}
"""
        apis = self.parser._extract_apis(java_code, "test.java", "backend")

        assert len(apis) == 3

        methods = {api.method for api in apis}
        assert "PUT" in methods
        assert "DELETE" in methods
        assert "PATCH" in methods

    def test_path_attribute(self):
        """测试使用 path 属性"""
        java_code = """
@RestController
public class CategoryController {
    
    @GetMapping(path = "/categories")
    public List<Category> getCategories() { return null; }
    
    @PostMapping(path = "/categories", consumes = "application/json")
    public Category createCategory() { return null; }
}
"""
        apis = self.parser._extract_apis(java_code, "test.java", "backend")

        assert len(apis) == 2
        assert apis[0].full_path == "/categories"

    def test_no_controller_annotation(self):
        """测试没有 Controller 注解的类"""
        java_code = """
public class ServiceClass {
    
    @GetMapping("/users")
    public List<User> getUsers() { return null; }
}
"""
        apis = self.parser._extract_apis(java_code, "test.java", "backend")

        # 没有 @Controller 或 @RestController，不应该提取
        assert len(apis) == 0

    def test_nested_classes(self):
        """测试嵌套类"""
        java_code = """
@RestController
public class OuterController {
    
    @GetMapping("/outer")
    public String outer() { return "outer"; }
    
    public class InnerController {
        @GetMapping("/inner")
        public String inner() { return "inner"; }
    }
}
"""
        apis = self.parser._extract_apis(java_code, "test.java", "backend")

        # 应该至少找到外层类的方法
        assert len(apis) >= 1
        assert any(api.full_path == "/outer" for api in apis)

    def test_empty_mapping(self):
        """测试空的 @GetMapping"""
        java_code = """
@RestController
@RequestMapping("/api")
public class RootController {
    
    @GetMapping
    public String root() { return "root"; }
    
    @GetMapping("")
    public String empty() { return "empty"; }
}
"""
        apis = self.parser._extract_apis(java_code, "test.java", "backend")

        assert len(apis) == 2
        # 都应该是 /api
        for api in apis:
            assert api.full_path == "/api"

    def test_complex_generics(self):
        """测试复杂泛型返回类型"""
        java_code = """
@RestController
public class ComplexController {
    
    @GetMapping("/complex")
    public ResponseEntity<Page<UserDTO>> getComplex() { return null; }
    
    @GetMapping("/list")
    public List<Map<String, Object>> getList() { return null; }
}
"""
        apis = self.parser._extract_apis(java_code, "test.java", "backend")

        assert len(apis) == 2

    def test_annotation_with_multiple_attributes(self):
        """测试带有多个属性的注解"""
        java_code = """
@RestController
public class MultiAttrController {
    
    @GetMapping(value = "/search", produces = "application/json", headers = "X-Custom=value")
    public SearchResult search() { return null; }
    
    @PostMapping(path = "/create", consumes = "application/json", produces = "application/json")
    public Result create() { return null; }
}
"""
        apis = self.parser._extract_apis(java_code, "test.java", "backend")

        assert len(apis) == 2
        assert apis[0].full_path == "/search"
        assert apis[1].full_path == "/create"
