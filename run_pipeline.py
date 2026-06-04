"""CLI entry point for the function embedding pipeline.

Usage:
    python run_pipeline.py [options]

Options:
    --config PATH     Path to config.json (default: ./config.json)
    --repo NAME       Repository name to process (default: first in list)
    --dry-run         Extract and embed but skip all Neo4j writes
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from src.core.pipeline_config import load_pipeline_config
from src.pipeline.pipeline import EmbeddingPipeline
from src.pipeline.reporter import generate_report


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Function embedding and similarity pipeline")
    parser.add_argument("--config", default="config.json", help="Path to config.json")
    parser.add_argument("--repo", default=None, help="Repository name to process")
    parser.add_argument("--path", default=None, help="Override repo_path (e.g. a subfolder for quick testing)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Extract and embed but skip Neo4j writes",
    )
    parser.add_argument(
        "--no-descriptions",
        action="store_true",
        help="Skip LLM description generation and description embeddings",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate a markdown similarity report after the pipeline completes",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Skip the pipeline and only generate a report from the current Neo4j data",
    )
    return parser.parse_args()


async def _run(args: argparse.Namespace) -> int:
    config = load_pipeline_config(config_path=args.config, repo_name=args.repo)

    if args.path:
        from dataclasses import replace
        config = replace(config, repo_path=args.path)

    if args.report_only:
        print(f"Generating report for: {config.repo_name}")
        report_dir = await generate_report(
            config.neo4j, config.repo_name,
            include_tests=config.include_tests_in_graph,
            pipeline_config=config,
        )
        print(f"Report written to: {report_dir}/")
        return 0

    print(f"Repository : {config.repo_name}")
    print(f"Path       : {config.repo_path}")
    print(f"Languages  : {', '.join(config.supported_languages)}")
    print(f"Embed model: {config.embedding_model}")
    print(f"Chat model : {config.chat_model}")
    print(f"Neo4j      : {config.neo4j.uri}/{config.neo4j.database}")
    print(f"Dry run    : {args.dry_run}")
    print(f"Descriptions: {'off' if args.no_descriptions else 'on'}")
    print()

    pipeline = EmbeddingPipeline(config, dry_run=args.dry_run, skip_descriptions=args.no_descriptions)
    try:
        result = await pipeline.run()
    finally:
        await pipeline.close()

    print()
    print("=== Pipeline Result ===")
    print(f"  Extracted  : {result.total_extracted}")
    print(f"  Changed    : {result.changed}")
    print(f"  Unchanged  : {result.unchanged}")
    print(f"  Deleted    : {result.newly_deleted}")
    print(f"  Edges      : {result.edges_written}")
    print(f"  Duration   : {result.duration_seconds:.1f}s")

    if result.errors:
        print(f"  Errors     : {len(result.errors)}")
        for err in result.errors:
            print(f"    - {err}")

    if (args.report or args.report_only) and not args.dry_run:
        print()
        report_dir = await generate_report(
            config.neo4j, config.repo_name,
            include_tests=config.include_tests_in_graph,
            pipeline_config=config,
        )
        print(f"Report written to: {report_dir}/")

    return 1 if result.errors else 0


def main() -> None:
    args = _parse_args()
    sys.exit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
