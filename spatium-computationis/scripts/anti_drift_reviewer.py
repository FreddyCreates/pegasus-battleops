#!/usr/bin/env python
"""
CLI Script: Anti-Drift Reviewer 🔍
Invoke drift auditing from the command line.

Usage:
    python -m spatium_computationis.scripts.anti_drift_reviewer audit "your content"
    python -m spatium_computationis.scripts.anti_drift_reviewer quick-check "your content"
    python -m spatium_computationis.scripts.anti_drift_reviewer comparative "current content" --baseline "baseline content"
    python -m spatium_computationis.scripts.anti_drift_reviewer categories
"""

from __future__ import annotations

import asyncio
import json
import sys
from argparse import ArgumentParser

from spatium_computationis.agents.anti_drift_reviewer.agent import (
    audit,
    quick_check,
    comparative_audit,
    get_drift_categories,
)


def main() -> None:
    """Main CLI entry point."""
    parser = ArgumentParser(description="Anti-Drift Reviewer — Drift auditing and validation")
    parser.add_argument(
        "command",
        choices=["audit", "quick-check", "comparative", "categories"],
        help="Command to execute",
    )
    parser.add_argument("content", nargs="?", default=None, help="Content to audit")
    parser.add_argument(
        "--content-type",
        default="general",
        help="Type of content: output|architecture|conversation|document|general",
    )
    parser.add_argument("--baseline", help="Baseline content (for comparative audit)")
    parser.add_argument("--doctrine-context", help="Doctrine context for alignment check")
    parser.add_argument("--json", action="store_true", help="Output as formatted JSON")

    args = parser.parse_args()

    if args.command == "categories":
        categories = get_drift_categories()
        output = {"reviewer": "anti-drift-reviewer", "categories": categories}
        print(json.dumps(output, indent=2))
        sys.exit(0)

    if not args.content:
        parser.error(f"Command '{args.command}' requires content argument")

    # Run async function
    result = asyncio.run(
        _execute_command(args.command, args.content, args.content_type, args.baseline, args.doctrine_context)
    )

    # Output
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result, indent=2))


async def _execute_command(
    command: str,
    content: str,
    content_type: str,
    baseline: str | None,
    doctrine_context: str | None,
) -> dict:
    """Execute the specified command."""
    if command == "audit":
        return await audit(content, content_type=content_type, doctrine_context=doctrine_context)
    elif command == "quick-check":
        return await quick_check(content)
    elif command == "comparative":
        if not baseline:
            return {"error": "Comparative audit requires --baseline argument"}
        return await comparative_audit(content, baseline, content_type=content_type)
    else:
        return {"error": f"Unknown command: {command}"}


if __name__ == "__main__":
    main()
