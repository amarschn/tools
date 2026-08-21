#!/usr/bin/env python3
"""Generate and validate repository metadata shown in the tool index."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CATALOG = REPO / "catalog.json"
OUTPUT = REPO / "data" / "homepage-tool-meta.json"
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def is_public_tool(entry: dict) -> bool:
    categories = {str(value).strip().lower() for value in entry.get("category", [])}
    return "templates" not in categories and tool_directory(entry) is not None


def tool_directory(entry: dict) -> str | None:
    match = re.search(r"(?:^|/)tools/([^/]+)/?", str(entry.get("path", "")))
    return f"tools/{match.group(1)}" if match else None


def metadata_key(entry: dict) -> str:
    directory = tool_directory(entry)
    if directory is None:
        raise ValueError(f"Invalid tool path: {entry.get('path')!r}")
    return f"/{directory}/"


def git_output(*arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def build_metadata(catalog: list[dict]) -> dict[str, dict]:
    metadata = {}
    for entry in catalog:
        if not is_public_tool(entry):
            continue
        directory = tool_directory(entry)
        changed_on = git_output("log", "-1", "--format=%cs", "--", directory)
        revision_count = int(
            git_output("rev-list", "--count", "HEAD", "--", directory)
        )
        version = entry.get("version")
        if version is not None:
            version = str(version).strip()
            if not version:
                raise ValueError(f"Empty version for {entry.get('title')}")
        metadata[metadata_key(entry)] = {
            "last_updated": changed_on,
            "revision_count": revision_count,
            "version": version,
        }
    return metadata


def validate_metadata(catalog: list[dict], metadata: dict) -> None:
    expected_keys = {
        metadata_key(entry) for entry in catalog if is_public_tool(entry)
    }
    if set(metadata) != expected_keys:
        missing = sorted(expected_keys - set(metadata))
        extra = sorted(set(metadata) - expected_keys)
        raise ValueError(
            f"Metadata coverage mismatch. Missing: {missing}; extra: {extra}"
        )

    versions = {
        metadata_key(entry): entry.get("version")
        for entry in catalog
        if is_public_tool(entry)
    }
    for key, value in metadata.items():
        if set(value) != {"last_updated", "revision_count", "version"}:
            raise ValueError(f"Unexpected fields for {key}: {sorted(value)}")
        if not DATE_PATTERN.fullmatch(str(value["last_updated"])):
            raise ValueError(f"Invalid date for {key}: {value['last_updated']!r}")
        date.fromisoformat(value["last_updated"])
        if not isinstance(value["revision_count"], int) or value["revision_count"] < 1:
            raise ValueError(f"Invalid revision count for {key}")
        expected_version = versions[key]
        if value["version"] != expected_version:
            raise ValueError(
                "Version mismatch for "
                f"{key}: {value['version']!r} != {expected_version!r}"
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    catalog = json.loads(CATALOG.read_text())
    if args.validate:
        validate_metadata(catalog, json.loads(OUTPUT.read_text()))
        print(f"Validated {OUTPUT.relative_to(REPO)}")
        return

    generated = build_metadata(catalog)
    validate_metadata(catalog, generated)
    rendered = json.dumps(generated, indent=2) + "\n"
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text() != rendered:
            raise SystemExit(f"{OUTPUT.relative_to(REPO)} is out of date")
        print(f"Checked {OUTPUT.relative_to(REPO)}")
        return

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(rendered)
    print(f"Wrote {OUTPUT.relative_to(REPO)} with {len(generated)} tools")


if __name__ == "__main__":
    main()
