#!/usr/bin/env python3
"""Require full validation, exact build output, and a self-contained publish tree."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_site import load_database
from release.compiler import render_outputs
from schema_lab.validator import jsonschema_available


def main():
    if not jsonschema_available():
        raise SystemExit('Release verification needs jsonschema. Install requirements-dev.txt with Python 3.10 or newer.')
    expected = render_outputs(ROOT, load_database(ROOT))
    output = ROOT / 'materials'
    actual_paths = {p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file()}
    owned = set(expected) | {'.build-manifest.json'}
    errors = []
    for relative, content in expected.items():
        path = output / relative
        if not path.is_file() or path.read_bytes() != content:
            errors.append(f'Stale or missing generated output: {relative}')
    for relative in sorted(actual_paths - owned): errors.append(f'Unowned file in publish tree: {relative}')
    if errors: raise SystemExit('\n'.join(errors) + '\nRun scripts/build_site.py and check the publish directory.')
    manifest = json.loads(expected['release-manifest.json'])
    print(f"Release {manifest['version']} / {manifest['build_id']}: full validation, {len(expected)} artifacts, hashes and current output passed.")
    print(f"Search index: {manifest['index_bytes']:,} bytes raw; {manifest['index_gzip_bytes']:,} bytes gzip.")


if __name__ == '__main__': main()
