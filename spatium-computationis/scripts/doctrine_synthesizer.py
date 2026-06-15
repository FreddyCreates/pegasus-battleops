#!/usr/bin/env python
"""
CLI Script: Doctrine Synthesizer ⚗️
Invoke doctrine synthesis from the command line.

Usage:
    python -m spatium_computationis.scripts.doctrine_synthesizer synthesize "raw ideas"
    python -m spatium_computationis.scripts.doctrine_synthesizer extract-laws "raw ideas"
    python -m spatium_computationis.scripts.doctrine_synthesizer framework "raw ideas"
    python -m spatium_computationis.scripts.doctrine_synthesizer hierarchy
"""

from __future__ import annotations

import asyncio
import json
import sys
from argparse import ArgumentParser

from spatium_computationis.agents.doctrine_synthesizer.agent import (
    synthesize,
    extract_laws,
    synthesize_framework,
    get_doctrine_hierarchy,
)


def main() -> None:
    """Main CLI entry point."""
    parser = ArgumentParser(description="Doctrine Synthesizer — Convert raw ideas into doctrine")
    parser.add_argument(
        "command",
        choices=["synthesize", "extract-laws", "framework", "hierarchy"],
        help="Command to execute",
    )
    parser.add_argument("input_text", nargs="?", default=None, help="Raw material to synthesize")

    args = parser.parse_args()

    if args.command == "hierarchy":
        hierarchy = get_doctrine_hierarchy()
        output = {"synthesizer": "doctrine-synthesizer", "hierarchy": hierarchy}
        print(json.dumps(output, indent=2))
        sys.exit(0)

    if not args.input_text:
        parser.error(f"Command '{args.command}' requires input_text argument")

    # Run async function
    result = asyncio.run(_execute_command(args.command, args.input_text))

    # Output as JSON (standard for CLI)
    print(json.dumps(result, indent=2))


async def _execute_command(command: str, input_text: str) -> dict:
    """Execute the specified command."""
    if command == "synthesize":
        return await synthesize(input_text, synthesis_type="full")
    elif command == "extract-laws":
        return await extract_laws(input_text)
    elif command == "framework":
        return await synthesize_framework(input_text)
    else:
        return {"error": f"Unknown command: {command}"}


if __name__ == "__main__":
    main()
