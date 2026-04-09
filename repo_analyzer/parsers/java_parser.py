import re
import logging
from typing import List, Optional
from .base_parser import BaseParser
from ..models.entities import BackendApi

logger = logging.getLogger(__name__)


class JavaParser(BaseParser):
    HTTP_METHOD_ANNOTATIONS = {
        "GetMapping": "GET",
        "PostMapping": "POST",
        "PutMapping": "PUT",
        "DeleteMapping": "DELETE",
        "PatchMapping": "PATCH",
        "RequestMapping": None,
    }

    REST_ANNOTATIONS = ["RestController", "Controller", "RestControllerAdvice"]

    def parse(self, file_path: str, repo: str) -> List[BackendApi]:
        try:
            content = self.get_file_content(file_path)
            return self._extract_apis(content, file_path, repo)
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
            return []

    def _extract_apis(
        self, content: str, file_path: str, repo: str
    ) -> List[BackendApi]:
        apis = []

        classes = self._find_rest_controller_classes(content)

        for class_info in classes:
            class_name = class_info["name"]
            class_base_path = class_info["base_path"]

            methods = self._find_controller_methods(class_info["content"])

            for method_info in methods:
                api = self._create_api(
                    method_info, class_base_path, class_name, file_path, repo
                )
                if api:
                    apis.append(api)

        return apis

    def _find_rest_controller_classes(self, content: str) -> List[dict]:
        classes = []

        pattern = (
            r"@(?:"
            + "|".join(self.REST_ANNOTATIONS)
            + r")\s*(?:\([^)]*\))?\s*public\s+class\s+(\w+)[^{]*\{"
        )

        for match in re.finditer(pattern, content, re.MULTILINE):
            class_name = match.group(1)
            class_start = match.end() - 1

            class_end = self._find_class_end(content, class_start)
            class_content = content[class_start:class_end]

            base_path = self._extract_class_base_path(match.group(0))

            classes.append(
                {"name": class_name, "base_path": base_path, "content": class_content}
            )

        return classes

    def _find_class_end(self, content: str, start: int) -> int:
        brace_count = 0
        i = start

        while i < len(content):
            if content[i] == "{":
                brace_count += 1
            elif content[i] == "}":
                brace_count -= 1
                if brace_count == 0:
                    return i
            i += 1

        return len(content)

    def _extract_class_base_path(self, annotation_block: str) -> str:
        request_mapping_pattern = (
            r'@RequestMapping\s*\(\s*(?:value\s*=\s*)?["\']([^"\']+)["\']'
        )

        match = re.search(request_mapping_pattern, annotation_block)
        if match:
            return match.group(1)

        return ""

    def _find_controller_methods(self, class_content: str) -> List[dict]:
        methods = []

        for annotation, default_method in self.HTTP_METHOD_ANNOTATIONS.items():
            pattern = rf"@{annotation}\s*\(([^)]*)\)\s*(?:public\s+)?(?:[\w<>?,\s]+\s+)?(\w+)\s*\("

            for match in re.finditer(pattern, class_content, re.MULTILINE):
                annotation_params = match.group(1)
                method_name = match.group(2)

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

        return methods

    def _extract_path_from_annotation(self, params: str) -> str:
        if not params.strip():
            return ""

        value_pattern = r'(?:value|path)\s*=\s*["\']([^"\']+)["\']'
        match = re.search(value_pattern, params)
        if match:
            return match.group(1)

        simple_pattern = r'["\']([^"\']+)["\']'
        match = re.search(simple_pattern, params)
        if match:
            return match.group(1)

        return ""

    def _extract_method_from_annotation(self, params: str) -> Optional[str]:
        method_pattern = r"method\s*=\s*(?:RequestMethod\.)?(\w+)"
        match = re.search(method_pattern, params)
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
        path = re.sub(r"/+", "/", path)
        if not path.startswith("/"):
            path = "/" + path
        return path

    def _extract_path_parameters(self, path: str) -> List[str]:
        return re.findall(r"\{(\w+)\}", path)
