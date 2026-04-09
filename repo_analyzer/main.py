#!/usr/bin/env python3
import argparse
import logging
import sys

from repo_analyzer.writer.neo4j_writer import Neo4jWriter
from repo_analyzer.core.graph_builder import GraphBuilder
from repo_analyzer.core.repo_manager import RepoGroup
from repo_analyzer.core.cross_analyzer import CrossAnalyzer

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_parser():
    parser = argparse.ArgumentParser(
        description="Multi-repo code graph builder and cross-repo call analyzer"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    build_parser = subparsers.add_parser("build", help="Build single repo graph")
    build_parser.add_argument("--name", required=True, help="Repo name")
    build_parser.add_argument("--path", required=True, help="Repo path")
    build_parser.add_argument(
        "--type",
        required=True,
        choices=["backend", "gateway", "frontend"],
        help="Repo type",
    )
    build_parser.add_argument(
        "--rebuild", action="store_true", help="Rebuild if exists"
    )

    group_parser = subparsers.add_parser("group", help="Manage repo groups")
    group_parser.add_argument(
        "action", choices=["create", "analyze", "stats", "list"], help="Group action"
    )
    group_parser.add_argument("--name", help="Group name")
    group_parser.add_argument("--repos", nargs="+", help="Repo names")

    analyze_parser = subparsers.add_parser("analyze", help="Analyze cross-repo calls")
    analyze_parser.add_argument("--group", required=True, help="Group name")

    query_parser = subparsers.add_parser("query", help="Query graph")
    query_parser.add_argument(
        "query_type",
        choices=["chain", "unmatched-fe", "unmatched-gw"],
        help="Query type",
    )
    query_parser.add_argument("--group", help="Group name")
    query_parser.add_argument("--limit", type=int, default=100, help="Result limit")

    return parser


def cmd_build(args):
    writer = Neo4jWriter.from_config()

    try:
        writer.create_unique_constraints()
        writer.create_indexes()

        builder = GraphBuilder(writer)

        if args.rebuild and writer.repo_exists(args.name):
            logger.info(f"Rebuilding repo '{args.name}'...")
            stats = builder.rebuild_repo(args.name, args.path, args.type)
        else:
            stats = builder.build_repo_graph(args.name, args.path, args.type)

        print(f"\nBuild complete: {stats}")
    finally:
        writer.close()


def cmd_group(args):
    writer = Neo4jWriter.from_config()

    try:
        manager = RepoGroup(writer)

        if args.action == "create":
            if not args.name or not args.repos:
                print("--name and --repos are required for create")
                sys.exit(1)
            manager.create_group(args.name, args.repos)
            print(f"Created group '{args.name}' with repos: {args.repos}")

        elif args.action == "analyze":
            if not args.name:
                print("--name is required for analyze")
                sys.exit(1)
            results = manager.analyze_group(args.name)
            print(f"\nAnalysis results: {results}")

        elif args.action == "stats":
            if not args.name:
                print("--name is required for stats")
                sys.exit(1)
            stats = manager.get_group_stats(args.name)
            print(f"\nGroup stats: {stats}")

        elif args.action == "list":
            groups = manager.list_groups()
            print("\nRepo Groups:")
            for g in groups:
                print(f"  - {g['name']}: {g['repos']} ({g['status']})")
    finally:
        writer.close()


def cmd_analyze(args):
    writer = Neo4jWriter.from_config()

    try:
        manager = RepoGroup(writer)
        results = manager.analyze_group(args.group)
        print(f"\nCross-repo analysis complete:")
        print(f"  Frontend -> Gateway: {results['frontend_to_gateway']} relations")
        print(f"  Gateway -> Backend: {results['gateway_to_backend']} relations")
        print(f"  Mapping relations: {results['mapping_relations']}")
    finally:
        writer.close()


def cmd_query(args):
    writer = Neo4jWriter.from_config()

    try:
        manager = RepoGroup(writer)

        if args.query_type == "chain":
            results = manager.get_call_chain(limit=args.limit)
            print(f"\nCall chains ({len(results)}):")
            for r in results:
                print(f"  {r['frontend_url']}")
                print(
                    f"    -> {r['gateway_path']} (match: {r['frontend_match_type']}, {r['frontend_confidence']})"
                )
                print(
                    f"    -> {r['backend_class']}.{r['backend_method']} (match: {r['gateway_match_type']}, {r['gateway_confidence']})"
                )

        elif args.query_type == "unmatched-fe":
            results = manager.get_unmatched_frontend_urls()
            print(f"\nUnmatched frontend URLs ({len(results)}):")
            for r in results:
                print(f"  {r['url']} ({r['file_path']}:{r['line']})")

        elif args.query_type == "unmatched-gw":
            results = manager.get_unmatched_gateway_routes()
            print(f"\nUnmatched gateway routes ({len(results)}):")
            for r in results:
                print(f"  {r['method']} {r['path']} ({r['operation_id']})")
    finally:
        writer.close()


def main():
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "build":
            cmd_build(args)
        elif args.command == "group":
            cmd_group(args)
        elif args.command == "analyze":
            cmd_analyze(args)
        elif args.command == "query":
            cmd_query(args)
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
