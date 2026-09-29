#!/usr/bin/env python3
"""One deterministic command surface for the schema lab.

    python3 materials/builder/schema_lab.py migrate    # legacy corpus -> canonical fixture
    python3 materials/builder/schema_lab.py validate   # structural + semantic validation
    python3 materials/builder/schema_lab.py check      # migrate to a temp buffer and diff

`check` is the build gate: it re-runs migration in memory and fails when the
checked-in fixture is not what the current code produces, which is what keeps
repeated builds identical.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from schema_lab import diagnostics as D  # noqa: E402
from schema_lab.adversarial import apply as apply_adversarial  # noqa: E402
from schema_lab.goldens import build as build_goldens  # noqa: E402
from schema_lab.migrate import migrate  # noqa: E402
from schema_lab.projections import Corpus  # noqa: E402
from schema_lab.render import render_material, render_units  # noqa: E402
from schema_lab.validator import (  # noqa: E402
    jsonschema_available,
    validate,
)

LEGACY_DUMP = REPO_ROOT / "builder" / "dump_legacy_corpus.js"
FIXTURE_DIR = REPO_ROOT / "fixtures" / "schema-lab" / "v0.1.0"
CORPUS_PATH = FIXTURE_DIR / "corpus.json"
REPORT_PATH = FIXTURE_DIR / "migration-report.json"
GOLDEN_DIR = FIXTURE_DIR / "goldens"


def load_legacy() -> dict:
    """Execute the frozen prototype corpus and read it back as JSON."""
    result = subprocess.run(
        ["node", str(LEGACY_DUMP)],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=False, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def build_corpus() -> tuple[dict, dict]:
    """Migrate the legacy corpus and overlay the adversarial cases."""
    legacy = load_legacy()
    dataset, report = migrate(legacy)
    dataset, added = apply_adversarial(dataset)
    payload = report.as_dict()
    payload["adversarial_additions"] = added
    return dataset, payload


def command_migrate(args: argparse.Namespace) -> int:
    dataset, report = build_corpus()
    write_json(CORPUS_PATH, dataset)
    write_json(REPORT_PATH, report)

    counts = dataset["dataset"]["expected_counts"]
    print(f"Wrote {CORPUS_PATH.relative_to(REPO_ROOT)}")
    print("  " + ", ".join(f"{key}: {value}" for key, value in sorted(counts.items())))
    print(f"Wrote {REPORT_PATH.relative_to(REPO_ROOT)}")
    for kind, count in sorted(report["counts"].items()):
        print(f"  {kind}: {count}")
    print(f"  adversarial_additions: {len(report['adversarial_additions'])}")
    return 0


def command_validate(args: argparse.Namespace) -> int:
    path = Path(args.path) if args.path else CORPUS_PATH
    dataset = json.loads(path.read_text(encoding="utf-8"))

    structural = jsonschema_available()
    if not structural:
        print(
            "warning: jsonschema is not installed; running semantic checks only. "
            "Install it with: python3 -m pip install -r requirements-dev.txt",
            file=sys.stderr,
        )

    found = validate(dataset, structural=structural)
    errors = [item for item in found if item.severity == D.ERROR]
    warnings = [item for item in found if item.severity == D.WARNING]

    for item in found:
        stream = sys.stderr if item.severity == D.ERROR else sys.stdout
        print(str(item), file=stream)

    print(
        f"{path.relative_to(REPO_ROOT)}: {len(errors)} errors, {len(warnings)} warnings"
        + ("" if structural else " (semantic only)")
    )
    return 1 if errors else 0


def command_goldens(args: argparse.Namespace) -> int:
    dataset = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    for name, payload in build_goldens(dataset).items():
        write_json(GOLDEN_DIR / f"{name}.json", payload)
        print(f"Wrote {(GOLDEN_DIR / f'{name}.json').relative_to(REPO_ROOT)}")
    return 0


def command_show(args: argparse.Namespace) -> int:
    """Render one material through the contract, for demonstration."""
    dataset = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    corpus = Corpus(dataset)

    if args.list or not args.material:
        print("Materials in the corpus:\n")
        for material_id in sorted(
            corpus.materials, key=lambda key: corpus.materials[key]["name"]
        ):
            material = corpus.materials[material_id]
            states = corpus.states_by_material.get(material_id, [])
            suffix = f"  ({len(states)} states)" if states else ""
            print(f"  {material['name']:<32} {material_id}{suffix}")
        print("\nProperties:\n")
        for property_id in sorted(corpus.properties):
            print(f"  {render_units(corpus.properties[property_id])}")
        return 0

    if args.material not in corpus.materials:
        matches = [
            key
            for key in corpus.materials
            if args.material.lower() in key.lower()
            or args.material.lower() in corpus.materials[key]["name"].lower()
        ]
        if len(matches) != 1:
            print(f"unknown material {args.material!r}", file=sys.stderr)
            if matches:
                print("did you mean: " + ", ".join(sorted(matches)), file=sys.stderr)
            return 1
        args.material = matches[0]

    print(
        render_material(
            corpus, args.material, property_id=args.property, system=args.units
        )
    )
    return 0


def command_check(args: argparse.Namespace) -> int:
    """Fail when the checked-in fixture differs from a fresh migration."""
    if not CORPUS_PATH.exists():
        print(f"missing {CORPUS_PATH.relative_to(REPO_ROOT)}; run migrate", file=sys.stderr)
        return 1

    fresh, _ = build_corpus()
    stored = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    if fresh != stored:
        print(
            "checked-in corpus does not match a fresh migration; run "
            "`python3 materials/builder/schema_lab.py migrate`",
            file=sys.stderr,
        )
        return 1

    print("corpus matches a fresh migration")
    return command_validate(args)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("migrate", help="rebuild the canonical fixture")
    subparsers.add_parser("goldens", help="rebuild the projection goldens")

    validate_parser = subparsers.add_parser("validate", help="validate a dataset")
    validate_parser.add_argument("path", nargs="?", help="dataset JSON to validate")

    check_parser = subparsers.add_parser("check", help="verify determinism and validity")
    check_parser.add_argument("path", nargs="?", help=argparse.SUPPRESS)

    show_parser = subparsers.add_parser(
        "show", help="render a material through the contract"
    )
    show_parser.add_argument("material", nargs="?", help="material id or name fragment")
    show_parser.add_argument("--property", help="restrict to one property, with provenance")
    show_parser.add_argument(
        "--units",
        choices=["metric", "imperial"],
        default="metric",
        help="display unit system (default: metric)",
    )
    show_parser.add_argument(
        "--list", action="store_true", help="list materials and available units"
    )

    args = parser.parse_args(argv)
    handlers = {
        "migrate": command_migrate,
        "goldens": command_goldens,
        "validate": command_validate,
        "check": command_check,
        "show": command_show,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
