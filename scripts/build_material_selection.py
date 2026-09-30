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
from pycalcs.material_selection import build_selection_database  # noqa: E402

OUTPUT = ROOT / "data/materials/selection.json"


def render() -> str:
    """Build deterministic chart data from the verified public catalog export."""
    source = ROOT / "tools/materials"
    manifest = json.loads((source / "release-manifest.json").read_text())
    catalog = (source / manifest["catalog"]).read_bytes()
    digest = hashlib.sha256(catalog).hexdigest()
    if digest != manifest["files"][manifest["catalog"]]["sha256"]:
        raise ValueError("Materials catalog differs from its release manifest; rebuild Materials first.")
    result = build_selection_database(json.loads(catalog))
    result["source_build_id"] = manifest["build_id"]
    result["source_sha256"] = digest
    return json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"


def main() -> None:
    """Write the generated projection, or fail if it has become stale."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    content = render()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text() != content:
            raise SystemExit("Ashby data is stale; run python3 scripts/build_material_selection.py")
        print("Ashby data matches the Materials release and Python indices.")
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(content)
        print(f"Wrote {OUTPUT.relative_to(ROOT)} ({len(content.encode()):,} bytes).")


if __name__ == "__main__":
    main()
