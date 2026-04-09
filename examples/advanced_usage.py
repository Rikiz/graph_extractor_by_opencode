"""
Example: Advanced usage scenarios.

This demonstrates:
- Custom matching strategies
- Handling complex URL patterns
- Working with mapping rules
- Querying and analyzing results
"""

from repo_analyzer import GraphBuilder, RepoGroup, Neo4jWriter
from repo_analyzer.matcher.url_matcher import UrlMatcher
from repo_analyzer.models.entities import FrontendUrl, GatewayRoute, MappingRule


def example_custom_matching():
    """Example: Custom matching strategy."""

    matcher = UrlMatcher()

    # Scenario 1: Version prefix normalization
    frontend_url = FrontendUrl(
        raw_url="/api/v1/users/123",
        file_path="userService.ts",
        repo="frontend",
        line_number=10,
        http_method="GET",
    )

    gateway_route = GatewayRoute(method="GET", full_path="/v2/users/{id}", repo="gateway")

    results = matcher.match_frontend_to_gateway(frontend_url, [gateway_route], [])

    print(f"Match type: {results[0].match_type}")
    print(f"Confidence: {results[0].confidence}")

    # Scenario 2: Using mapping rules
    mapping = MappingRule(
        uri="/api/users/{id}",
        method="GET",
        repo="frontend",
        file_path="mapping.json",
        target_uri="/v2/users/{id}",
    )

    frontend_with_mapping = FrontendUrl(
        raw_url="/api/users/456",
        file_path="userService.ts",
        repo="frontend",
        line_number=20,
        http_method="GET",
    )

    results = matcher.match_frontend_to_gateway(frontend_with_mapping, [gateway_route], [mapping])

    print(f"With mapping: {results[0].match_type}")


def example_batch_analysis():
    """Example: Analyzing multiple groups."""

    writer = Neo4jWriter.from_config()

    try:
        manager = RepoGroup(writer)

        # Define multiple groups
        groups = {
            "mobile_app": ["mobile_frontend", "gateway", "backend"],
            "web_app": ["web_frontend", "gateway", "backend"],
            "admin_portal": ["admin_frontend", "gateway", "backend"],
        }

        for group_name, repos in groups.items():
            # Create group
            manager.create_group(group_name, repos)

            # Analyze
            results = manager.analyze_group(group_name)

            print(f"\n{group_name}:")
            print(f"  FE -> GW: {results['frontend_to_gateway']}")
            print(f"  GW -> BE: {results['gateway_to_backend']}")

            # Get stats
            stats = manager.get_group_stats(group_name)
            print(f"  Total: {stats['total_relations']}")

    finally:
        writer.close()


def example_query_patterns():
    """Example: Common query patterns."""

    writer = Neo4jWriter.from_config()

    try:
        # 1. Find all GET endpoints in backend
        backend_gets = writer.execute("""
            MATCH (api:BackendApi {repo: 'backend', method: 'GET'})
            RETURN api.full_path, api.class_name, api.method_name
            ORDER BY api.full_path
        """)
        print(f"Backend GET endpoints: {len(backend_gets)}")

        # 2. Find deprecated routes
        deprecated = writer.execute("""
            MATCH (route:GatewayRoute {deprecated: true})
            RETURN route.full_path, route.operation_id
        """)
        print(f"Deprecated routes: {len(deprecated)}")

        # 3. Find high-confidence call chains
        chains = writer.execute("""
            MATCH (url:FrontendUrl)-[c:CALLS]->(route:GatewayRoute)
                  -[r:ROUTES_TO]->(api:BackendApi)
            WHERE c.confidence >= 0.9 AND r.confidence >= 0.9
            RETURN url.raw_url, route.full_path, 
                   api.class_name, api.method_name
            LIMIT 10
        """)

        print("\nHigh-confidence chains:")
        for chain in chains:
            print(f"  {chain['url.raw_url']}")
            print(f"    -> {chain['route.full_path']}")
            print(f"    -> {chain['api.class_name']}.{chain['api.method_name']}")

        # 4. Find orphaned frontend URLs
        orphaned = writer.execute("""
            MATCH (url:FrontendUrl)
            WHERE NOT (url)-[:CALLS]->() AND NOT (url)-[:USES_MAPPING]->()
            RETURN url.raw_url, url.file_path, url.line_number
            LIMIT 20
        """)

        print(f"\nOrphaned URLs: {len(orphaned)}")

        # 5. Coverage statistics
        coverage = writer.execute("""
            MATCH (url:FrontendUrl)
            WITH count(url) as total
            OPTIONAL MATCH (url:FrontendUrl)-[:CALLS]->(:GatewayRoute)
            WITH total, count(url) as matched
            RETURN total, matched, 
                   toFloat(matched) / total * 100 as coverage_percent
        """)

        if coverage:
            print(f"\nCoverage: {coverage[0]['coverage_percent']:.1f}%")

    finally:
        writer.close()


def example_incremental_update():
    """Example: Incremental updates."""

    writer = Neo4jWriter.from_config()
    builder = GraphBuilder(writer)

    try:
        # Rebuild only backend (frontend/gateway unchanged)
        print("Rebuilding backend...")
        stats = builder.rebuild_repo("backend", "/path/to/backend", "backend")
        print(f"Updated: {stats}")

        # Re-run analysis
        manager = RepoGroup(writer)
        results = manager.analyze_group("full_stack")
        print(f"Analysis updated: {results}")

    finally:
        writer.close()


def example_export_results():
    """Example: Export results to file."""

    writer = Neo4jWriter.from_config()

    try:
        import json

        # Export call chains
        chains = writer.execute("""
            MATCH (url:FrontendUrl)-[c:CALLS]->(route:GatewayRoute)
                  -[r:ROUTES_TO]->(api:BackendApi)
            RETURN {
                frontend: url.raw_url,
                frontend_file: url.file_path,
                frontend_line: url.line_number,
                gateway: route.full_path,
                backend_class: api.class_name,
                backend_method: api.method_name,
                fe_confidence: c.confidence,
                gw_confidence: r.confidence,
                fe_match_type: c.match_type,
                gw_match_type: r.match_type
            } as chain
            ORDER BY c.confidence DESC
        """)

        with open("call_chains.json", "w") as f:
            json.dump([c["chain"] for c in chains], f, indent=2)

        print(f"Exported {len(chains)} call chains to call_chains.json")

        # Export unmatched URLs
        unmatched = writer.execute("""
            MATCH (url:FrontendUrl)
            WHERE NOT (url)-[:CALLS]->()
            RETURN url.raw_url, url.file_path, url.line_number
        """)

        with open("unmatched_urls.json", "w") as f:
            json.dump(unmatched, f, indent=2)

        print(f"Exported {len(unmatched)} unmatched URLs")

    finally:
        writer.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Advanced Usage Examples")
    print("=" * 60)

    print("\n1. Custom Matching:")
    example_custom_matching()

    print("\n" + "=" * 60)
    print("\nNote: Other examples require Neo4j connection and data.")
    print("Uncomment to run with your setup.")

    # example_batch_analysis()
    # example_query_patterns()
    # example_incremental_update()
    # example_export_results()
