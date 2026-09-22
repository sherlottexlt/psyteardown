"""Export the Product Studio OpenAPI schema for generated clients."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from psyteardown.api.app import create_app


def export_openapi(output: Path) -> None:
    """Write a deterministic, UTF-8 OpenAPI document."""

    payload = json.dumps(
        create_app().openapi(),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(f"{payload}\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    export_openapi(arguments.output)


if __name__ == "__main__":
    main()
