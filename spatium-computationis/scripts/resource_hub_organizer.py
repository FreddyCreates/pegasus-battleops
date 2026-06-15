#!/usr/bin/env python
"""
CLI Script: Resource Hub Organizer 📂
Invoke resource organization from the command line.

Usage:
    python -m spatium_computationis.scripts.resource_hub_organizer organize "material"
    python -m spatium_computationis.scripts.resource_hub_organizer suggest-collections "material"
    python -m spatium_computationis.scripts.resource_hub_organizer principles
"""

from __future__ import annotations

import asyncio
import json
import sys
from argparse import ArgumentParser

from spatium_computationis.agents.resource_hub_organizer.agent import (
    organize,
    suggest_collections,
    get_organization_principles,
)


def main() -> None:
    """Main CLI entry point."""
    parser = ArgumentParser(
        description="Resource Hub Organizer — Organize intellectual resources"
    )
    parser.add_argument(
        "command",
        choices=["organize", "suggest-collections", "principles"],
        help="Command to execute",
    )
    parser.add_argument("material", nargs="?", default=None, help="Material to organize")
    parser.add_argument(
        "--material-type",
        default="mixed",
        help="Type of material: ideas|documents|doctrine|projects|mixed",
    )
    parser.add_argument("--json", action="store_true", help="Output as formatted JSON")

    args = parser.parse_args()

    if args.command == "principles":
        principles = get_organization_principles()
        output = {"organizer": "resource-hub-organizer", "principles": principles}
        print(json.dumps(output, indent=2))
        sys.exit(0)

    if not args.material:
        parser.error(f"Command '{args.command}' requires material argument")

    # Run async function
    result = asyncio.run(_execute_command(args.command, args.material, args.material_type))

    # Output
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result, indent=2))


async def _execute_command(command: str, material: str, material_type: str) -> dict:
    """Execute the specified command."""
    if command == "organize":
        return await organize(material, material_type=material_type)
    elif command == "suggest-collections":
        return await suggest_collections(material)
    else:
        return {"error": f"Unknown command: {command}"}


if __name__ == "__main__":
    main()
