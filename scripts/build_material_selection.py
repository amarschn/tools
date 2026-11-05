#!/usr/bin/env python3
"""Generate the shared Ashby projection from the published Materials release."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pycalcs.material_selection import build_chart_files, build_selection_database  # noqa: E402

DATA = ROOT / "data/materials"
OUTPUT = DATA / "selection.json"
CORE_OUTPUT = DATA / "selection-core.json"
DETAILS_OUTPUT = DATA / "selection-details.json"


def _dump(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"


def render() -> dict[Path, str]:
    """Build deterministic chart data from the verified public catalog export."""
    source = ROOT / "tools/materials"
    manifest = json.loads((source / "release-manifest.json").read_text())
    catalog = (source / manifest["catalog"]).read_bytes()
    digest = hashlib.sha256(catalog).hexdigest()
    if digest != manifest["files"][manifest["catalog"]]["sha256"]:
        raise ValueError("Materials catalog differs from its release manifest; rebuild Materials first.")
    result = build_selection_database(json.loads(catalog))
    core, details = build_chart_files(result)
    outputs = {}
    for path, payload in ((OUTPUT, result), (CORE_OUTPUT, core), (DETAILS_OUTPUT, details)):
        payload["source_build_id"] = manifest["build_id"]
        payload["source_sha256"] = digest
        outputs[path] = _dump(payload)
    return outputs


def main() -> None:
    """Write the generated projection, or fail if it has become stale."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    outputs = render()
    if args.check:
        stale = [path for path, content in outputs.items() if not path.exists() or path.read_text() != content]
        if stale:
            names = ", ".join(path.name for path in stale)
            raise SystemExit(f"Ashby data is stale ({names}); run python3 scripts/build_material_selection.py")
        print("Ashby data matches the Materials release and Python indices.")
    else:
        DATA.mkdir(parents=True, exist_ok=True)
        for path, content in outputs.items():
            path.write_text(content)
            print(f"Wrote {path.relative_to(ROOT)} ({len(content.encode()):,} bytes).")


if __name__ == "__main__":
    main()
