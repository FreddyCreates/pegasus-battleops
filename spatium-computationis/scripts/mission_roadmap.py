#!/usr/bin/env python
"""
CLI Script: Mission Roadmap Orchestrator 🗺️
Invoke roadmap generation from the command line.

Usage:
    python -m spatium_computationis.scripts.mission_roadmap generate "project description"
    python -m spatium_computationis.scripts.mission_roadmap next-actions "project description"
    python -m spatium_computationis.scripts.mission_roadmap structure
"""

from __future__ import annotations

import asyncio
import json
import sys
from argparse import ArgumentParser

from spatium_computationis.agents.mission_roadmap_orchestrator.agent import (
    generate_roadmap,
    extract_next_actions,
    get_roadmap_structure,
)


def main() -> None:
    """Main CLI entry point."""
    parser = ArgumentParser(
        description="Mission Roadmap Orchestrator — Generate execution roadmaps"
    )
    parser.add_argument(
        "command",
        choices=["generate", "next-actions", "structure"],
        help="Command to execute",
    )
    parser.add_argument(
        "project_input",
        nargs="?",
        default=None,
        help="Project description or vision",
    )

    args = parser.parse_args()

    if args.command == "structure":
        structure = get_roadmap_structure()
        output = {"orchestrator": "mission-roadmap", "structure": structure}
        print(json.dumps(output, indent=2))
        sys.exit(0)

    if not args.project_input:
        parser.error(f"Command '{args.command}' requires project_input argument")

    # Run async function
    result = asyncio.run(_execute_command(args.command, args.project_input))

    # Output as JSON (standard for CLI)
    print(json.dumps(result, indent=2))


async def _execute_command(command: str, project_input: str) -> dict:
    """Execute the specified command."""
    if command == "generate":
        return await generate_roadmap(project_input)
    elif command == "next-actions":
        return await extract_next_actions(project_input)
    else:
        return {"error": f"Unknown command: {command}"}


if __name__ == "__main__":
    main()
