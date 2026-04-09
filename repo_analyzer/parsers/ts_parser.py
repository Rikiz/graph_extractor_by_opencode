import re
import logging
from typing import List, Set
from .base_parser import BaseParser
from ..models.entities import FrontendUrl

logger = logging.getLogger(__name__)


class TsParser(BaseParser):
    HTTP_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"}

    def parse(self, file_path: str, repo: str) -> List[FrontendUrl]:
        try:
            content = self.get_file_content(file_path)
            lines = self.get_file_lines(file_path)
            return self._extract_urls(content, lines, file_path, repo)
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
            return []

    def _extract_urls(
        self, content: str, lines: List[str], file_path: str, repo: str
    ) -> List[FrontendUrl]:
        urls = []
        seen_urls = set()

        string_literal_urls = self._extract_string_literal_urls(
            content, lines, file_path, repo
        )
        for url_info in string_literal_urls:
            key = (url_info.raw_url, url_info.line_number)
            if key not in seen_urls:
                urls.append(url_info)
                seen_urls.add(key)

        template_urls = self._extract_template_literal_urls(
            content, lines, file_path, repo
        )
        for url_info in template_urls:
            key = (url_info.raw_url, url_info.line_number)
            if key not in seen_urls:
                urls.append(url_info)
                seen_urls.add(key)

        http_call_urls = self._extract_http_call_urls(content, lines, file_path, repo)
        for url_info in http_call_urls:
            key = (url_info.raw_url, url_info.line_number)
            if key not in seen_urls:
                urls.append(url_info)
                seen_urls.add(key)

        return urls

    def _extract_string_literal_urls(
        self, content: str, lines: List[str], file_path: str, repo: str
    ) -> List[FrontendUrl]:
        urls = []

        patterns = [
            r'["\'](/api/[^"\']*)["\']',
            r'["\'](/v\d+/[^"\']*)["\']',
            r'["\'](/[a-z]+/[a-zA-Z][^"\']*)["\']',
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, content):
                url = match.group(1)
                line_num = self._get_line_number(content, match.start(), lines)

                http_method = self._infer_http_method(content, match.start())

                urls.append(
                    FrontendUrl(
                        raw_url=url,
                        file_path=file_path,
                        repo=repo,
                        line_number=line_num,
                        normalized_url=self._normalize_url(url),
                        http_method=http_method,
                        is_template=False,
                    )
                )

        return urls

    def _extract_template_literal_urls(
        self, content: str, lines: List[str], file_path: str, repo: str
    ) -> List[FrontendUrl]:
        urls = []

        template_pattern = r"`([^`]*\$\{[^}]+\}[^`]*)`"

        for match in re.finditer(template_pattern, content):
            template = match.group(1)

            if not self._looks_like_url(template):
                continue

            line_num = self._get_line_number(content, match.start(), lines)

            variables = re.findall(r"\$\{(\w+)\}", template)

            normalized = re.sub(r"\$\{(\w+)\}", r"{\1}", template)

            urls.append(
                FrontendUrl(
                    raw_url=template,
                    file_path=file_path,
                    repo=repo,
                    line_number=line_num,
                    normalized_url=self._normalize_url(normalized),
                    http_method=self._infer_http_method(content, match.start()),
                    is_template=True,
                    variables=variables,
                )
            )

        return urls

    def _extract_http_call_urls(
        self, content: str, lines: List[str], file_path: str, repo: str
    ) -> List[FrontendUrl]:
        urls = []

        call_patterns = [
            (
                r'(?:axios|http|fetch)\.(?:get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
                None,
            ),
            (r'(?:axios|http|fetch)\s*\(\s*["\']([^"\']+)["\']', None),
            (r"(?:axios|http)\.(get|post|put|delete|patch)\s*\(\s*`([^`]+)`", 2),
        ]

        for pattern_info in call_patterns:
            pattern = pattern_info[0]
            url_group = pattern_info[1] if len(pattern_info) > 1 else 1

            for match in re.finditer(pattern, content, re.IGNORECASE):
                if len(match.groups()) > 1:
                    method = (
                        match.group(1).upper()
                        if pattern_info[1] is None
                        else match.group(1).upper()
                    )
                    url = match.group(url_group)
                else:
                    url = match.group(1)
                    method = self._infer_http_method(content, match.start())

                if not self._is_valid_url(url):
                    continue

                line_num = self._get_line_number(content, match.start(), lines)

                is_template = "${" in url
                variables = re.findall(r"\$\{(\w+)\}", url) if is_template else []
                normalized = (
                    re.sub(r"\$\{(\w+)\}", r"{\1}", url) if is_template else url
                )

                urls.append(
                    FrontendUrl(
                        raw_url=url,
                        file_path=file_path,
                        repo=repo,
                        line_number=line_num,
                        normalized_url=self._normalize_url(normalized),
                        http_method=method,
                        is_template=is_template,
                        variables=variables,
                    )
                )

        return urls

    def _looks_like_url(self, text: str) -> bool:
        url_indicators = ["/api", "/v1", "/v2", "/users", "/posts", "/items", "/data"]
        return any(indicator in text.lower() for indicator in url_indicators)

    def _is_valid_url(self, url: str) -> bool:
        if not url:
            return False
        if url.startswith("http"):
            return True
        if url.startswith("/"):
            return True
        return False

    def _normalize_url(self, url: str) -> str:
        url = url.split("?")[0]
        url = re.sub(r"/+", "/", url)
        if not url.startswith("/"):
            url = "/" + url
        return url

    def _infer_http_method(self, content: str, position: int) -> str:
        context_start = max(0, position - 200)
        context = content[context_start:position].lower()

        if "post" in context or "create" in context or "add" in context:
            return "POST"
        if "put" in context or "update" in context:
            return "PUT"
        if "delete" in context or "remove" in context:
            return "DELETE"
        if "patch" in context:
            return "PATCH"

        return "GET"

    def _get_line_number(self, content: str, position: int, lines: List[str]) -> int:
        return content[:position].count("\n") + 1
