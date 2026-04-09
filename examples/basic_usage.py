#!/usr/bin/env python3
"""
Example usage of the Multi-Repo Code Graph Builder

This script demonstrates the complete workflow:
  1. Phase 1: Build single-repo graphs
  2. Phase 2: Analyze cross-repo calls
"""

from repo_analyzer import GraphBuilder, RepoGroup, Neo4jWriter


def main():
    print("=" * 60)
    print("Multi-Repo Code Graph Builder - Example Usage")
    print("=" * 60)

    # Initialize Neo4j connection
    # Option 1: From environment variables
    # writer = Neo4jWriter.from_config()

    # Option 2: From config file
    # writer = Neo4jWriter.from_file("neo4j_config.json")

    # Option 3: Direct configuration
    from repo_analyzer.config.neo4j_config import Neo4jConfig

    config = Neo4jConfig(uri="bolt://localhost:7687", user="neo4j", password="password")
    writer = Neo4jWriter(config)

    try:
        # Create constraints and indexes
        print("\n[1] Creating Neo4j constraints and indexes...")
        writer.create_unique_constraints()
        writer.create_indexes()

        # Initialize builders
        builder = GraphBuilder(writer)
        manager = RepoGroup(writer)

        # ==================== Phase 1: Build Single-Repo Graphs ====================
        print("\n" + "=" * 60)
        print("PHASE 1: Building Single-Repo Graphs")
        print("=" * 60)

        # Replace these paths with your actual repo paths
        repos_config = [
            {
                "name": "backend",
                "path": "/path/to/your/backend/repo",
                "type": "backend",
            },
            {
                "name": "gateway",
                "path": "/path/to/your/gateway/repo",
                "type": "gateway",
            },
            {
                "name": "frontend",
                "path": "/path/to/your/frontend/repo",
                "type": "frontend",
            },
        ]

        for repo_config in repos_config:
            repo_name = repo_config["name"]
            repo_path = repo_config["path"]
            repo_type = repo_config["type"]

            print(f"\n[Building] {repo_name} ({repo_type})...")

            try:
                stats = builder.build_repo_graph(repo_name, repo_path, repo_type)
                print(f"  -> Extracted entities: {stats}")
            except ValueError as e:
                print(f"  -> Skipped: {e}")
                print(f"  -> Please update the repo path in this script")

        # ==================== Phase 2: Cross-Repo Analysis ====================
        print("\n" + "=" * 60)
        print("PHASE 2: Cross-Repo Call Analysis")
        print("=" * 60)

        # Create a repo group
        group_name = "full_stack"
        repo_names = [r["name"] for r in repos_config]

        print(f"\n[Creating] RepoGroup '{group_name}'...")
        manager.create_group(group_name, repo_names)

        # Analyze cross-repo relations
        print(f"\n[Analyzing] Cross-repo calls...")
        try:
            results = manager.analyze_group(group_name)

            print("\n[Results]")
            print(
                f"  Frontend -> Gateway: {results.get('frontend_to_gateway', 0)} relations"
            )
            print(
                f"  Gateway -> Backend: {results.get('gateway_to_backend', 0)} relations"
            )
            print(f"  Mapping relations: {results.get('mapping_relations', 0)}")

            # Get statistics
            stats = manager.get_group_stats(group_name)
            print(f"\n[Stats] Total relations: {stats.get('total_relations', 0)}")

            # Query call chains
            print("\n[Query] Sample call chains:")
            chains = manager.get_call_chain(limit=5)
            for chain in chains:
                print(f"  {chain['frontend_url']}")
                print(f"    -> {chain['gateway_path']}")
                print(f"    -> {chain['backend_class']}.{chain['backend_method']}")

        except ValueError as e:
            print(f"\n  Analysis skipped: {e}")
            print("  Make sure all repos have been built successfully.")

    finally:
        writer.close()

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
