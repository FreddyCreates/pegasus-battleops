#!/usr/bin/env python
"""
CLI Script: Medina Operating System 🧠
Invoke the core cognitive operating framework from the command line.

Usage:
    python -m spatium_computationis.scripts.medina_os process "your input"
    python -m spatium_computationis.scripts.medina_os perceive "your input"
    python -m spatium_computationis.scripts.medina_os synthesize "your input"
    python -m spatium_computationis.scripts.medina_os doctrine-alignment "your input"
    python -m spatium_computationis.scripts.medina_os principles
"""

from __future__ import annotations

import asyncio
import json
import sys
from argparse import ArgumentParser

from spatium_computationis.agents.medina_operating_system.agent import (
    process,
    perceive,
    synthesize,
    extract_doctrine_alignment,
    get_operating_principles,
)


def main() -> None:
    """Main CLI entry point."""
    parser = ArgumentParser(
        description="Medina Operating System — Core cognitive framework"
    )
    parser.add_argument(
        "command",
        choices=[
            "process",
            "perceive",
            "synthesize",
            "doctrine-alignment",
            "principles",
        ],
        help="Command to execute",
    )
    parser.add_argument("input_text", nargs="?", default=None, help="Input to process")
    parser.add_argument(
        "--mode",
        default="full",
        help="Processing mode (for process command): full|perception|synthesis|doctrine",
    )

    args = parser.parse_args()

    if args.command == "principles":
        principles = get_operating_principles()
        output = {"system": "medina-operating-system", "principles": principles}
        print(json.dumps(output, indent=2))
        sys.exit(0)

    if not args.input_text:
        parser.error(f"Command '{args.command}' requires input_text argument")

    # Run async function
    result = asyncio.run(_execute_command(args.command, args.input_text, args.mode))

    # Output as JSON (standard for CLI)
    print(json.dumps(result, indent=2))


async def _execute_command(command: str, input_text: str, mode: str) -> dict:
    """Execute the specified command."""
    if command == "process":
        return await process(input_text, processing_mode=mode)
    elif command == "perceive":
        return await perceive(input_text)
    elif command == "synthesize":
        return await synthesize(input_text)
    elif command == "doctrine-alignment":
        return await extract_doctrine_alignment(input_text)
    else:
        return {"error": f"Unknown command: {command}"}


if __name__ == "__main__":
    main()
