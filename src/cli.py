"""
KIRP Enterprise CLI — developer experience helper.

Usage:
  python -m src.cli show-config
  python -m src.cli show-contracts
"""

from __future__ import annotations

import argparse
import json

from src.core.config import get_settings
from src.core.contracts import get_contracts


def cmd_show_config() -> None:
    """Print effective non-secret config for debugging."""
    settings = get_settings()
    data = settings.dict()
    # Hide sensitive values
    data.pop("jwt_secret", None)
    print(json.dumps(data, indent=2, sort_keys=True))


def cmd_show_contracts() -> None:
    """Print current data contracts (JSON Schemas)."""
    contracts = get_contracts()
    print(json.dumps(contracts, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="kirp", description="KIRP Enterprise CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("show-config", help="Show effective runtime config (non-secret).")
    sub.add_parser("show-contracts", help="Show JSON Schemas for API models.")

    args = parser.parse_args(argv)
    if args.command == "show-config":
        cmd_show_config()
    elif args.command == "show-contracts":
        cmd_show_contracts()


if __name__ == "__main__":
    main()

