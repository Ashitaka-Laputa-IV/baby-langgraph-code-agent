"""Command-line entry point and interactive terminal loop."""

from __future__ import annotations

import argparse
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="baby-code-agent",
        description="A small LangGraph code agent that reads, edits, and runs code in the current directory.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    parser.parse_args(argv)

    from baby_code_agent.settings import ConfigError, load_settings

    try:
        load_settings()
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    return 0
