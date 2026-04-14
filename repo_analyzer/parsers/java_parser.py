"""
Java Controller 解析器

提取 Spring Boot REST Controller 及 API 接口定义中的端点。
支持：
- @RestController/@Controller 注解的类
- @RequestMapping/@FeignClient 注解的接口
"""

import re
import logging
from typing import List, Optional
from .base_parser import BaseParser
from ..models.entities import BackendApi

logger = logging.getLogger(__name__)


class JavaParser(BaseParser):
    """解析 Java Spring Boot Controller 及 API 接口"""

    HTTP_METHOD_ANNOTATIONS = {
        "GetMapping": "GET",
        "PostMapping": "POST",
        "PutMapping": "PUT",
        "DeleteMapping": "DELETE",
        "PatchMapping": "PATCH",
        "RequestMapping": None,
    }

    REST_ANNOTATIONS = ["RestController", "Controller", "RestControllerAdvice"]

    INTERFACE_ANNOTATIONS = ["RequestMapping", "FeignClient"]

    def parse(self, file_path: str, repo: str) -> List[BackendApi]:
        """解析 Java 文件，提取 API 端点"""
        try:
            content = self.get_file_content(file_path)
            if not content.strip():
                logger.debug(f"Empty file: {file_path}")
                return []

            apis = self._extract_apis(content, file_path, repo)

            if apis:
                logger.info(f"Extracted {len(apis)} APIs from {file_path}")

            return apis
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}", exc_info=True)
            return []

    def _extract_apis(self, content: str, file_path: str, repo: str) -> List[BackendApi]:
        """提取所有 API"""
        apis = []

        # 找到所有 RestController 类
        classes = self._find_rest_controller_classes(content)
        logger.debug(f"Found {len(classes)} controller classes in {file_path}")

        for class_info in classes:
            class_name = class_info["name"]
            class_base_path = class_info["base_path"]
            class_content = class_info["content"]

            logger.debug(f"Processing class: {class_name}, base_path: {class_base_path or '/'}")

            methods = self._find_controller_methods(class_content)
            logger.debug(f"Found {len(methods)} methods in class {class_name}")

            for method_info in methods:
                api = self._create_api(method_info, class_base_path, class_name, file_path, repo)
                if api:
                    apis.append(api)

        # 找到所有 API 接口定义
        interfaces = self._find_api_interfaces(content)
        logger.debug(f"Found {len(interfaces)} API interfaces in {file_path}")

        for interface_info in interfaces:
            interface_name = interface_info["name"]
            interface_base_path = interface_info["base_path"]
            interface_content = interface_info["content"]

            logger.debug(
                f"Processing interface: {interface_name}, base_path: {interface_base_path or '/'}"
            )

            methods = self._find_controller_methods(interface_content)
            logger.debug(f"Found {len(methods)} methods in interface {interface_name}")

            for method_info in methods:
                api = self._create_api(
                    method_info, interface_base_path, interface_name, file_path, repo
                )
                if api:
                    apis.append(api)

        return apis

    def _find_rest_controller_classes(self, content: str) -> List[dict]:
        """找到所有带有 @RestController 或 @Controller 注解的类"""
        classes = []

        # 方法1: 使用正则找到注解和类
        # 放宽要求：注解和类声明可以在不同行
        for annotation in self.REST_ANNOTATIONS:
            # 匹配 @Controller 注解后的类定义
            # 支持：
            # @Controller
            # public class MyController {
            #
            # @Controller("name")
            # class MyController {
            #
            # @Controller @RequestMapping("/api")
            # public class MyController {

            pattern = rf"@{annotation}\s*(?:\([^)]*\))?\s*(?:(?!@{annotation})[\s\S])*?(?:public\s+)?class\s+(\w+)\s*(?:extends\s+\w+)?\s*(?:implements\s+[\w,\s]+)?\s*\{{"

            for match in re.finditer(pattern, content):
                class_name = match.group(1)
                class_start = match.end() - 1  # 指向 {

                # 找到类的结束位置
                class_end = self._find_class_end(content, class_start)
                class_content = content[class_start:class_end]

                # 提取类级别的 @RequestMapping 路径
                # 从匹配的整个文本中查找
                annotation_block = match.group(0)
                base_path = self._extract_class_base_path(content[: match.end()])

                classes.append(
                    {"name": class_name, "base_path": base_path, "content": class_content}
                )

        # 去重（可能被多个注解匹配）
        seen = set()
        unique_classes = []
        for cls in classes:
            if cls["name"] not in seen:
                seen.add(cls["name"])
                unique_classes.append(cls)

        return unique_classes

    def _find_api_interfaces(self, content: str) -> List[dict]:
        """找到所有带有 @RequestMapping 或 @FeignClient 注解的接口"""
        interfaces = []

        for annotation in self.INTERFACE_ANNOTATIONS:
            # 匹配带注解的接口定义
            # 支持：
            # @RequestMapping("/api")
            # public interface MyApi {
            #
            # @FeignClient(name = "service", path = "/api")
            # public interface MyApi {
            #
            # @RequestMapping(value = "/v1/checkers-version", method = RequestMethod.GET)
            # interface CheckersVersionApi {

            pattern = rf"@{annotation}\s*(?:\([^)]*\))?\s*(?:(?!@{annotation})[\s\S])*?(?:public\s+)?interface\s+(\w+)\s*(?:extends\s+[\w,\s]+)?\s*\{{"

            for match in re.finditer(pattern, content):
                interface_name = match.group(1)
                interface_start = match.end() - 1

                interface_end = self._find_class_end(content, interface_start)
                interface_content = content[interface_start:interface_end]

                # 提取接口级别的路径
                # 对于 @RequestMapping，直接提取 value/path
                # 对于 @FeignClient，提取 path 属性
                base_path = self._extract_interface_base_path(content[: match.end()], annotation)

                interfaces.append(
                    {"name": interface_name, "base_path": base_path, "content": interface_content}
                )

        # 去重
        seen = set()
        unique_interfaces = []
        for iface in interfaces:
            if iface["name"] not in seen:
                seen.add(iface["name"])
                unique_interfaces.append(iface)

        return unique_interfaces

    def _extract_interface_base_path(self, content_before_interface: str, annotation: str) -> str:
        """从接口声明之前的内容中提取基础路径"""
        if annotation == "FeignClient":
            # @FeignClient(path = "/api") 或 @FeignClient(name = "service", path = "/api")
            patterns = [
                r'path\s*=\s*["\']([^"\']+)["\']',
            ]
        else:
            # @RequestMapping("/api") 或 @RequestMapping(value = "/api")
            patterns = [
                r'@RequestMapping\s*\(\s*(?:value\s*=\s*)?["\']([^"\']+)["\']',
                r'@RequestMapping\s*\(\s*path\s*=\s*["\']([^"\']+)["\']',
                r'@RequestMapping\s*\(\s*["\']([^"\']+)["\']',
            ]

        for pattern in patterns:
            match = re.search(pattern, content_before_interface)
            if match:
                return match.group(1)

        return ""

    def _find_class_end(self, content: str, start: int) -> int:
        """找到类的结束括号位置"""
        brace_count = 0
        i = start
        in_string = False
        in_comment = False
        string_char = None

        while i < len(content):
            char = content[i]

            # 处理注释
            if not in_string:
                if i + 1 < len(content):
                    two_chars = content[i : i + 2]
                    if two_chars == "/*" and not in_comment:
                        in_comment = True
                        i += 2
                        continue
                    elif two_chars == "*/" and in_comment:
                        in_comment = False
                        i += 2
                        continue
                    elif two_chars == "//" and not in_comment:
                        # 跳过单行注释
                        while i < len(content) and content[i] != "\n":
                            i += 1
                        continue

            if in_comment:
                i += 1
                continue

            # 处理字符串
            if char in ('"', "'") and not in_string:
                in_string = True
                string_char = char
            elif char == string_char and in_string:
                # 检查是否是转义的引号
                if i > 0 and content[i - 1] != "\\":
                    in_string = False
                    string_char = None

            # 统计括号
            if not in_string:
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        return i

            i += 1

        return len(content)

    def _extract_class_base_path(self, content_before_class: str) -> str:
        """从类声明之前的内容中提取 @RequestMapping 的路径"""
        # 支持多种格式：
        # @RequestMapping("/api")
        # @RequestMapping(value = "/api")
        # @RequestMapping(path = "/api")

        patterns = [
            r'@RequestMapping\s*\(\s*(?:value\s*=\s*)?["\']([^"\']+)["\']',
            r'@RequestMapping\s*\(\s*path\s*=\s*["\']([^"\']+)["\']',
            r'@RequestMapping\s*\(\s*["\']([^"\']+)["\']',
        ]

        for pattern in patterns:
            match = re.search(pattern, content_before_class)
            if match:
                return match.group(1)

        return ""

    def _find_controller_methods(self, class_content: str) -> List[dict]:
        """找到类中所有带有 HTTP 方法注解的方法"""
        methods = []

        for annotation, default_method in self.HTTP_METHOD_ANNOTATIONS.items():
            # 匹配方法定义
            # 支持多种格式：
            # @GetMapping("/users")
            # @GetMapping(value = "/users")
            # @GetMapping(path = "/users")
            # @RequestMapping(value = "/users", method = RequestMethod.GET)

            # 先找到所有注解位置
            annotation_pattern = rf"@{annotation}\s*(\([^)]*\))?\s*"

            for ann_match in re.finditer(annotation_pattern, class_content):
                annotation_params = ann_match.group(1) or ""

                # 从注解位置向后找方法名
                # 匹配: public ReturnType methodName(
                # 或: ReturnType methodName(
                method_pattern = r"(?:public\s+)?(?:[\w<>?,\s\[\]]+\s+)?(\w+)\s*\("

                # 从注解结束位置开始搜索
                search_start = ann_match.end()
                remaining = class_content[search_start:]

                method_match = re.search(method_pattern, remaining)
                if method_match:
                    method_name = method_match.group(1)

                    # 跳过常见的非方法名
                    if method_name in (
                        "class",
                        "interface",
                        "if",
                        "while",
                        "for",
                        "switch",
                        "catch",
                    ):
                        continue

                    path = self._extract_path_from_annotation(annotation_params)
                    http_method = default_method or self._extract_method_from_annotation(
                        annotation_params
                    )

                    if http_method is None:
                        http_method = "GET"

                    methods.append(
                        {
                            "path": path,
                            "http_method": http_method,
                            "method_name": method_name,
                        }
                    )

                    logger.debug(f"Found method: {http_method} {path or '/'} -> {method_name}")

        return methods

    def _extract_path_from_annotation(self, params: str) -> str:
        """从注解参数中提取路径"""
        if not params or not params.strip():
            return ""

        # 移除括号
        params = params.strip()
        if params.startswith("(") and params.endswith(")"):
            params = params[1:-1]

        if not params.strip():
            return ""

        # 尝试多种格式
        patterns = [
            r'(?:value|path)\s*=\s*["\']([^"\']+)["\']',  # value = "/path" 或 path = "/path"
            r'^\s*["\']([^"\']+)["\']',  # 直接是字符串 "/path"
        ]

        for pattern in patterns:
            match = re.search(pattern, params)
            if match:
                return match.group(1)

        # 如果都没有，但参数中有引号包裹的内容，取第一个
        simple_pattern = r'["\']([^"\']+)["\']'
        match = re.search(simple_pattern, params)
        if match:
            return match.group(1)

        return ""

    def _extract_method_from_annotation(self, params: str) -> Optional[str]:
        """从 @RequestMapping 注解中提取 HTTP 方法"""
        if not params:
            return None

        # 移除括号
        params = params.strip()
        if params.startswith("(") and params.endswith(")"):
            params = params[1:-1]

        # 支持多种格式：
        # method = RequestMethod.GET
        # method = GET
        # method = {RequestMethod.GET, RequestMethod.POST}

        patterns = [
            r"method\s*=\s*RequestMethod\.(\w+)",
            r"method\s*=\s*(\w+)(?!\.)",
            r"method\s*=\s*\{?\s*RequestMethod\.(\w+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, params)
            if match:
                return match.group(1).upper()

        return None

    def _create_api(
        self,
        method_info: dict,
        class_base_path: str,
        class_name: str,
        file_path: str,
        repo: str,
    ) -> Optional[BackendApi]:
        """创建 API 实体"""
        full_path = self._normalize_path(class_base_path + method_info["path"])
        parameters = self._extract_path_parameters(full_path)

        return BackendApi(
            method=method_info["http_method"],
            full_path=full_path,
            repo=repo,
            class_name=class_name,
            method_name=method_info["method_name"],
            file_path=file_path,
            parameters=parameters,
        )

    def _normalize_path(self, path: str) -> str:
        """标准化路径"""
        # 移除重复斜杠
        path = re.sub(r"/+", "/", path)
        # 确保以 / 开头
        if not path.startswith("/"):
            path = "/" + path
        # 移除尾部斜杠（除非是根路径）
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")
        return path

    def _extract_path_parameters(self, path: str) -> List[str]:
        """提取路径参数"""
        # 支持 {id} 和 ${id} 格式
        params = re.findall(r"\{(\w+)\}", path)
        params.extend(re.findall(r"\$\{(\w+)\}", path))
        return list(set(params))  # 去重
