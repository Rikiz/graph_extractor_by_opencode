"""
验证新匹配算法对用户报告的 5 个问题案例的处理。
"""

from repo_analyzer.matcher.url_matcher import UrlMatcher


def test_case(case_name, path1, path2, expected_behavior):
    matcher = UrlMatcher()
    score, details = matcher._compute_confidence(path1, path2)

    status = "✅" if expected_behavior(score) else "❌"
    print(f"{status} {case_name}")
    print(f"   {path1}")
    print(f"   vs")
    print(f"   {path2}")
    print(f"   score={score:.3f}  details={details}")
    print()
    return score


print("=" * 70)
print("验证用户报告的 5 个问题案例")
print("=" * 70)
print()

# 案例1: tenant-configs vs system-configs → 应该不匹配
test_case(
    "案例1: tenant-configs vs system-configs",
    "/data/v1/tenant-configs/{id}",
    "/rest/v2/system-configs/{config_id}",
    lambda s: s == 0.0,  # 主资源不匹配，应该0分
)

# 案例2: tenant-package-status vs inner-cron/status → 应该不匹配
test_case(
    "案例2: tenant-package-status vs inner-cron/status",
    "/portal/v4/tenant/tenant-package-status",
    "/v2/inner-cron/status",
    lambda s: s == 0.0,  # 主资源不匹配，应该0分
)

# 案例3: tenant-configs vs system-configs (GET) → 应该不匹配
test_case(
    "案例3: tenant-configs vs system-configs (GET)",
    "/data/v1/tenant-configs",
    "/rest/v2/system-configs",
    lambda s: s == 0.0,  # 主资源不匹配，应该0分
)

# 案例4: defects/next-status vs offering/status → 应该不匹配
test_case(
    "案例4: defects/next-status vs offering/status",
    "/report/v1/defects/next-status",
    "/rest/v2/offering/status",
    lambda s: s == 0.0,  # 主资源不匹配，应该0分
)

# 案例5: 应该匹配但之前失败的案例
test_case(
    "案例5: 应该匹配 - tenant-configs PUT",
    "/data/v1/tenant-configs/{id}",
    "/rest/v1/tenant-configs/{id}",
    lambda s: s >= 0.8,  # 主资源相同，应该高置信度
)

print("=" * 70)
print("额外测试：合理匹配场景")
print("=" * 70)
print()

# 正确匹配：相同资源不同版本
test_case(
    "合理匹配: 相同资源不同版本", "/api/v1/users/{id}", "/api/v2/users/{id}", lambda s: s >= 0.9
)

# 正确匹配：不同前缀但同一资源
test_case(
    "合理匹配: 不同前缀同一资源",
    "/data/v1/tenant-configs/{id}",
    "/rest/v1/tenant-configs/{id}",
    lambda s: s >= 0.8,
)

# 归一化匹配：连字符 vs 下划线
test_case(
    "合理匹配: 连字符 vs 下划线",
    "/api/v1/tenant-configs/{id}",
    "/api/v1/tenant_configs/{id}",
    lambda s: s >= 0.7,
)

# 精确匹配
test_case("精确匹配: 完全相同路径", "/api/v1/users/{id}", "/api/v1/users/{id}", lambda s: s == 1.0)

# 不应该匹配：完全不同的资源
test_case(
    "不匹配: users vs products", "/api/v1/users/{id}", "/api/v1/products/{id}", lambda s: s == 0.0
)

# 不应该匹配：类似但不相关
test_case(
    "不匹配: user-profile vs system-profile",
    "/api/v1/user-profile/{id}",
    "/api/v1/system-profile/{id}",
    lambda s: s == 0.0,
)

# 应该匹配：共享核心词
test_case(
    "共享核心词: user-profile vs user-detail",
    "/api/v1/user-profile/{id}",
    "/api/v1/user-detail/{id}",
    lambda s: s >= 0.3,
)
