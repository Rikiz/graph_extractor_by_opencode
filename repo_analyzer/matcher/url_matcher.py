"""
URL 匹配策略

核心原则：
1. 主资源路径必须匹配，否则直接拒绝
2. 区分"结构相似"和"语义相同"
3. 置信度要反映真实匹配质量，不允许虚高
"""

import re
import logging
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
from ..models.entities import FrontendUrl, GatewayRoute, BackendApi, MappingRule

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    target: object
    match_type: str
    confidence: float
    match_details: str = None


# 常见停用词：版本前缀和通用词，不参与资源匹配
STOP_SEGMENTS = {"", "v1", "v2", "v3", "v4", "v5", "api", "rest", "data", "portal", "report"}

# 路径参数占位符
PARAM_PATTERN = re.compile(r"^\{param\d+\}$")


class UrlMatcher:
    def __init__(self):
        pass

    # ========== 公开接口 ==========

    def match_frontend_to_gateway(
        self, url: FrontendUrl, routes: List[GatewayRoute], mappings: List[MappingRule]
    ) -> List[MatchResult]:
        mapping_result = self._match_via_mapping(url, mappings)
        if mapping_result:
            target_route = self._find_route_for_mapping(mapping_result, routes)
            if target_route:
                return [
                    MatchResult(
                        target=target_route,
                        match_type="mapping",
                        confidence=1.0,
                        match_details=f"via mapping: {mapping_result.uri} -> {mapping_result.target_uri}",
                    )
                ]

        exact_results = self._exact_match(url, routes)
        if exact_results:
            return exact_results

        normalized_results = self._normalized_match_fe(url, routes)
        if normalized_results:
            return normalized_results

        candidate_results = self._candidate_match_fe(url, routes)
        return candidate_results

    def match_gateway_to_backend(
        self, route: GatewayRoute, apis: List[BackendApi]
    ) -> List[MatchResult]:
        for api in apis:
            if route.method != api.method:
                continue
            if route.full_path == api.full_path:
                return [MatchResult(target=api, match_type="exact", confidence=1.0)]

        results = []
        for api in apis:
            if route.method != api.method:
                continue
            score, details = self._compute_confidence(route.full_path, api.full_path)
            if score >= 0.8:
                results.append(
                    MatchResult(
                        target=api,
                        match_type="normalized",
                        confidence=score,
                        match_details=details,
                    )
                )

        if results:
            return sorted(results, key=lambda x: -x.confidence)

        for api in apis:
            if route.method != api.method:
                continue
            score, details = self._compute_confidence(route.full_path, api.full_path)
            if score >= 0.3:
                results.append(
                    MatchResult(
                        target=api,
                        match_type="candidate",
                        confidence=score,
                        match_details=details,
                    )
                )

        return sorted(results, key=lambda x: -x.confidence)[:5]

    def build_mapping_relations(
        self,
        urls: List[FrontendUrl],
        mappings: List[MappingRule],
        routes: List[GatewayRoute],
    ) -> List[Dict]:
        relations = []
        for mapping in mappings:
            for url in urls:
                if self._urls_match(url.raw_url, mapping.uri):
                    relations.append(
                        {
                            "start_node": url,
                            "end_node": mapping,
                            "relation_type": "USES_MAPPING",
                            "properties": {"match_type": "mapping", "confidence": 1.0},
                        }
                    )
            target_url = mapping.target_uri or mapping.uri
            for route in routes:
                if route.method == mapping.method and self._urls_match(route.full_path, target_url):
                    relations.append(
                        {
                            "start_node": mapping,
                            "end_node": route,
                            "relation_type": "MAPS_TO",
                            "properties": {"match_type": "mapping", "confidence": 1.0},
                        }
                    )
        return relations

    # ========== 核心置信度计算 ==========

    def _compute_confidence(self, path1: str, path2: str) -> tuple:
        """
        计算两个路径的匹配置信度。

        核心原则：主资源路径段必须匹配，否则大幅惩罚。

        Returns:
            (confidence: float, details: str)
        """
        n1 = self._normalize_url(path1)
        n2 = self._normalize_url(path2)

        if n1 == n2:
            return 1.0, "exact match"

        segs1 = self._split_path(n1)
        segs2 = self._split_path(n2)

        # 分离：资源段 vs 参数段 vs 停用段
        res1, param_indices1 = self._extract_resource_segments(segs1)
        res2, param_indices2 = self._extract_resource_segments(segs2)

        # 1. 主资源匹配检查（关键）
        resource_match, resource_details = self._check_resource_match(res1, res2)

        if not resource_match:
            return 0.0, f"resource mismatch: {resource_details}"

        # 2. 结构匹配度
        structure_score, structure_details = self._structure_similarity(segs1, segs2)

        # 3. 资源段逐段精确匹配
        resource_score = self._resource_segment_score(res1, res2)

        # 4. 参数位置匹配
        param_score = self._param_position_score(segs1, segs2)

        # 5. 综合计算
        if resource_score >= 1.0 and structure_score >= 1.0:
            confidence = 1.0
        elif resource_score >= 0.8:
            confidence = 0.8 * resource_score + 0.15 * structure_score + 0.05 * param_score
        elif resource_score >= 0.5:
            confidence = 0.5 * resource_score + 0.3 * structure_score + 0.1 * param_score
        else:
            confidence = 0.2 * resource_score + 0.2 * structure_score + 0.1 * param_score

        details = (
            f"resource={resource_score:.2f} structure={structure_score:.2f} param={param_score:.2f}"
        )
        if resource_details:
            details += f" ({resource_details})"

        return round(confidence, 3), details

    # 常见通用词：这些词单独出现不能证明资源相同
    GENERIC_WORDS = {
        "status",
        "config",
        "info",
        "detail",
        "list",
        "id",
        "configs",
        "details",
        "lists",
        "ids",
        "count",
        "search",
        "query",
        "batch",
        "export",
        "import",
        "next",
        "prev",
        "history",
        "log",
        "audit",
        "profile",
        "setting",
        "settings",
        "type",
        "name",
        "code",
        "item",
        "items",
        "data",
        "value",
        "result",
        "response",
    }

    def _check_resource_match(self, res1: List[str], res2: List[str]) -> tuple:
        """
        检查两个路径的核心资源是否匹配。

        规则：
        - 主资源名必须实质相同
        - 包含关系只在较长的名称真正包含较短名称时成立
        - 共享词排除通用词，且要求非通用词匹配

        Returns:
            (match: bool, details: str)
        """
        if not res1 or not res2:
            return False, "empty resource segments"

        main1 = self._main_resource_name(res1)
        main2 = self._main_resource_name(res2)

        if not main1 or not main2:
            return False, f"cannot determine main resource: {main1} vs {main2}"

        # 主资源完全相同
        if main1 == main2:
            return True, f"main resource match: {main1}"

        # 主资源有包含关系（严格检查）
        # 只有当一个名称是另一个名称加连字符前缀/后缀时才成立
        # 例如: user-profile 包含 user ✓
        # 但: next-status 包含 status ✗ (status 是通用词)
        containment, cont_details = self._check_containment(main1, main2)
        if containment:
            return True, cont_details

        # 共享核心词（排除通用词，且要求非通用词数量 >= 1）
        words1 = set(main1.replace("-", "_").split("_"))
        words2 = set(main2.replace("-", "_").split("_"))
        non_generic1 = words1 - self.GENERIC_WORDS
        non_generic2 = words2 - self.GENERIC_WORDS
        common_non_generic = non_generic1 & non_generic2

        if common_non_generic:
            return True, f"shared resource words: {common_non_generic}"

        # 主资源完全不匹配
        return False, f"main resource mismatch: {main1} vs {main2}"

    def _check_containment(self, name1: str, name2: str) -> tuple:
        """
        严格检查包含关系。

        规则：只有当较短名称是较长名称的"核心前缀"时才成立。
        用连字符分割后，较短名称的所有词都必须出现在较长名称中。

        例如:
        - "user" vs "user-profile" → True (user 是前缀)
        - "status" vs "next-status" → False (status 是通用后缀)
        - "tenant" vs "tenant-configs" → True (tenant 是前缀)
        """
        shorter, longer = (name1, name2) if len(name1) <= len(name2) else (name2, name1)

        # 先检查字符串包含
        if shorter not in longer:
            return False, ""

        # 分词检查
        shorter_words = shorter.replace("-", "_").split("_")
        longer_words = longer.replace("-", "_").split("_")

        # 短名称中是否全是通用词
        shorter_non_generic = [w for w in shorter_words if w not in self.GENERIC_WORDS]

        if not shorter_non_generic:
            # 短名称全是通用词（如 status），不算包含
            return False, ""

        # 短名称的非通用词必须全部出现在长名称中
        longer_set = set(longer_words)
        all_present = all(w in longer_set for w in shorter_non_generic)

        if all_present:
            return True, f"resource containment: {shorter} in {longer}"

        return False, ""

    def _main_resource_name(self, resource_segments: List[str]) -> str:
        """
        提取路径的主资源名。

        规则：取最后一个非停用词段，忽略版本号前缀。
        例如：
        - ["api", "users"] → "users"
        - ["data", "tenant-configs"] → "tenant-configs"
        - ["rest", "v2", "system-configs"] → "system-configs"
        - ["report", "defects", "next-status"] → "next-status"
        """
        non_stop = [s for s in resource_segments if s.lower() not in STOP_SEGMENTS]

        if not non_stop:
            # 全是停用词，返回原始最后一个
            return resource_segments[-1] if resource_segments else ""

        return non_stop[-1]

    def _resource_segment_score(self, res1: List[str], res2: List[str]) -> float:
        """
        计算资源段的逐段匹配得分。

        只比较非停用词段，忽略版本号差异。
        """
        filtered1 = [s for s in res1 if s.lower() not in STOP_SEGMENTS]
        filtered2 = [s for s in res2 if s.lower() not in STOP_SEGMENTS]

        if not filtered1 or not filtered2:
            return 0.0

        # 长度不同时，对齐比较
        if len(filtered1) != len(filtered2):
            # 尝试最长公共子序列匹配
            lcs_len = self._lcs_length(filtered1, filtered2)
            max_len = max(len(filtered1), len(filtered2))
            return lcs_len / max_len

        match_count = 0
        for s1, s2 in zip(filtered1, filtered2):
            if s1.lower() == s2.lower():
                match_count += 1
            elif self._fuzzy_segment_match(s1, s2):
                match_count += 0.7

        return match_count / len(filtered1)

    def _structure_similarity(self, segs1: List[str], segs2: List[str]) -> tuple:
        """
        计算路径结构相似度。

        考虑：
        - 段数是否相同
        - 参数位置是否一致
        - 整体路径深度

        Returns:
            (score, details)
        """
        len1 = len(segs1)
        len2 = len(segs2)

        if len1 == 0 or len2 == 0:
            return 0.0, "empty path"

        # 段数差异惩罚
        len_diff = abs(len1 - len2)
        max_len = max(len1, len2)

        if len_diff == 0:
            len_score = 1.0
        elif len_diff == 1:
            len_score = 0.7
        elif len_diff == 2:
            len_score = 0.4
        else:
            len_score = 0.1

        # 参数位置匹配
        param_positions1 = {i for i, s in enumerate(segs1) if PARAM_PATTERN.match(s)}
        param_positions2 = {i for i, s in enumerate(segs2) if PARAM_PATTERN.match(s)}

        if param_positions1 and param_positions2:
            pos_match = len(param_positions1 & param_positions2) / max(
                len(param_positions1), len(param_positions2)
            )
        elif not param_positions1 and not param_positions2:
            pos_match = 1.0
        else:
            pos_match = 0.0

        score = 0.6 * len_score + 0.4 * pos_match

        details = f"len_diff={len_diff} param_pos_match={pos_match:.2f}"
        return round(score, 3), details

    def _param_position_score(self, segs1: List[str], segs2: List[str]) -> float:
        """参数位置匹配得分"""
        params1 = [i for i, s in enumerate(segs1) if PARAM_PATTERN.match(s)]
        params2 = [i for i, s in enumerate(segs2) if PARAM_PATTERN.match(s)]

        if not params1 and not params2:
            return 1.0
        if not params1 or not params2:
            return 0.0
        if params1 == params2:
            return 1.0

        common = len(set(params1) & set(params2))
        total = max(len(params1), len(params2))
        return common / total

    # ========== Frontend → Gateway 匹配 ==========

    def _exact_match(self, url: FrontendUrl, routes: List[GatewayRoute]) -> List[MatchResult]:
        results = []
        url_normalized = self._normalize_url(url.normalized_url or url.raw_url)

        for route in routes:
            route_normalized = self._normalize_url(route.full_path)
            if url_normalized == route_normalized:
                if url.http_method and url.http_method != route.method:
                    continue
                results.append(MatchResult(target=route, match_type="exact", confidence=1.0))

        return results

    def _normalized_match_fe(
        self, url: FrontendUrl, routes: List[GatewayRoute]
    ) -> List[MatchResult]:
        results = []
        for route in routes:
            if url.http_method and url.http_method != route.method:
                continue
            score, details = self._compute_confidence(
                url.normalized_url or url.raw_url, route.full_path
            )
            if score >= 0.8:
                results.append(
                    MatchResult(
                        target=route,
                        match_type="normalized",
                        confidence=score,
                        match_details=details,
                    )
                )
        return sorted(results, key=lambda x: -x.confidence)

    def _candidate_match_fe(
        self, url: FrontendUrl, routes: List[GatewayRoute]
    ) -> List[MatchResult]:
        results = []
        for route in routes:
            if url.http_method and url.http_method != route.method:
                continue
            score, details = self._compute_confidence(
                url.normalized_url or url.raw_url, route.full_path
            )
            if score >= 0.3:
                results.append(
                    MatchResult(
                        target=route,
                        match_type="candidate",
                        confidence=score,
                        match_details=details,
                    )
                )
        return sorted(results, key=lambda x: -x.confidence)[:5]

    # ========== 辅助方法 ==========

    def _normalize_url(self, url: str) -> str:
        if not url:
            return ""
        url = url.split("?")[0]
        url = re.sub(r"\$\{(\w+)\}", r"{\1}", url)
        url = re.sub(r":(\w+)", r"{\1}", url)
        url = re.sub(r"/+", "/", url)
        url = url.rstrip("/")
        if not url.startswith("/"):
            url = "/" + url
        return url

    def _split_path(self, url: str) -> List[str]:
        """分割路径为段，统一参数名为 {paramN}"""
        url = self._remove_version_prefix(url)
        url = self._unify_param_names(url)
        return url.split("/")

    def _remove_version_prefix(self, url: str) -> str:
        return re.sub(r"/v\d+", "", url)

    def _unify_param_names(self, url: str) -> str:
        count = [0]

        def replacer(match):
            count[0] += 1
            return f"{{param{count[0]}}}"

        return re.sub(r"\{(\w+)\}", replacer, url)

    def _extract_resource_segments(self, segments: List[str]) -> tuple:
        """
        分离资源段和参数段索引。

        Returns:
            (resource_segments: List[str], param_indices: Set[int])
        """
        resource = []
        param_indices = set()
        for i, seg in enumerate(segments):
            if PARAM_PATTERN.match(seg):
                param_indices.add(i)
            else:
                resource.append(seg)
        return resource, param_indices

    def _urls_match(self, url1: str, url2: str) -> bool:
        n1 = self._normalize_url(url1)
        n2 = self._normalize_url(url2)
        return n1 == n2

    def _fuzzy_segment_match(self, s1: str, s2: str) -> bool:
        """
        模糊段匹配：允许连字符/下划线差异和单复数差异。

        例如：
        - tenant_config vs tenant-config → True
        - user vs users → True
        """
        n1 = s1.lower().replace("-", "_").rstrip("s")
        n2 = s2.lower().replace("-", "_").rstrip("s")
        return n1 == n2

    def _lcs_length(self, seq1: List[str], seq2: List[str]) -> int:
        """最长公共子序列长度"""
        m, n = len(seq1), len(seq2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if seq1[i - 1].lower() == seq2[j - 1].lower():
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
        return dp[m][n]

    def _match_via_mapping(
        self, url: FrontendUrl, mappings: List[MappingRule]
    ) -> Optional[MappingRule]:
        for mapping in mappings:
            if self._urls_match(url.raw_url, mapping.uri):
                return mapping
        return None

    def _find_route_for_mapping(
        self, mapping: MappingRule, routes: List[GatewayRoute]
    ) -> Optional[GatewayRoute]:
        target_url = mapping.target_uri or mapping.uri
        for route in routes:
            if route.method == mapping.method and self._urls_match(route.full_path, target_url):
                return route
        return None

    def _get_normalization_details(self, url: FrontendUrl, route: GatewayRoute) -> str:
        url_norm = self._normalize_url(url.raw_url)
        route_norm = self._normalize_url(route.full_path)
        details = []
        if url_norm != url.raw_url:
            details.append(f"normalized url: {url.raw_url} -> {url_norm}")
        if route_norm != route.full_path:
            details.append(f"normalized route: {route.full_path} -> {route_norm}")
        return "; ".join(details) if details else "path normalized"
