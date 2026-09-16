"""Source documents must never be committed, and never published.

The Materials tool ships textual citations only. Its upstream project enforces
that at build and release verification; these tests enforce the half that lives
in this repository, so a stray `git add -f` or a hand-edited dataset fails here
rather than on the live site.
"""

import json
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
MATERIALS = REPO / "tools" / "materials"

DOCUMENT_SUFFIXES = {
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".odt",
    ".ods",
    ".odp",
    ".rtf",
}


def tracked_files() -> list[str]:
    """Every path git tracks, which is exactly what a deploy would publish."""
    listing = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    )
    return [path for path in listing.stdout.split("\0") if path]


def test_no_source_document_is_tracked():
    """A committed datasheet would be served from the published root."""
    offenders = [
        path
        for path in tracked_files()
        if Path(path).suffix.lower() in DOCUMENT_SUFFIXES
    ]
    assert offenders == [], (
        "Source documents must stay in private-sources/, which is git-ignored: "
        + ", ".join(offenders)
    )


def test_private_sources_holds_only_its_readme():
    """The ignore rule must expose the policy note and nothing else."""
    tracked = [p for p in tracked_files() if p.startswith("private-sources/")]
    assert tracked == ["private-sources/README.md"]


@pytest.mark.skipif(not MATERIALS.exists(), reason="Materials tool not vendored")
def test_published_materials_data_cites_without_linking():
    """Published data may name a source, never link to or embed one."""
    payloads = sorted(MATERIALS.glob("data/*/*.json"))
    assert payloads, "Expected vendored Materials data to check"
    for path in payloads:
        text = path.read_text(encoding="utf-8")
        assert ".pdf" not in text.lower(), f"{path.name} references a document"
        urls = re.findall(r"https?://[^\s\"'\\]+", text)
        assert urls == [], f"{path.name} carries source URLs: {urls[:3]}"


@pytest.mark.skipif(not MATERIALS.exists(), reason="Materials tool not vendored")
def test_published_sources_keep_attribution():
    """Removing links must not cost the citation that makes a value checkable."""
    sources = sorted(MATERIALS.glob("data/*/sources.json"))
    assert sources, "Expected a vendored sources payload"
    records = json.loads(sources[0].read_text(encoding="utf-8"))
    entries = records["sources"] if isinstance(records, dict) else records
    assert entries, "Expected at least one cited source"
    for entry in entries:
        assert entry.get("organization"), f"{entry.get('id')} has no publisher"
        assert entry.get("sha256"), f"{entry.get('id')} has no snapshot hash"


@pytest.mark.skipif(not MATERIALS.exists(), reason="Materials tool not vendored")
def test_vendored_build_matches_its_release_manifest():
    """Catch a vendored copy that drifted from the build it came from.

    Two files are adapted on purpose when vendoring, and are listed here so the
    adaptation stays visible rather than being absorbed into a loose check.
    Everything else must still hash to the build it came from.
    """
    manifest = json.loads(
        (MATERIALS / "release-manifest.json").read_text(encoding="utf-8")
    )
    import hashlib

    adapted = {
        # scripts/inject_seo_meta.py adds catalog-derived canonical and Open
        # Graph tags after the build. The GA4 snippet and description are baked
        # into materials/src/index.html, so a rebuild cannot drop those.
        "index.html",
    }
    mismatched = []
    for name, expected in manifest["files"].items():
        if name in adapted:
            continue
        target = MATERIALS / name
        if not target.exists():
            mismatched.append(f"{name}: missing")
            continue
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        if digest != expected["sha256"]:
            mismatched.append(f"{name}: content changed since the build")
    assert mismatched == [], mismatched[:5]


@pytest.mark.skipif(not MATERIALS.exists(), reason="Materials tool not vendored")
def test_published_materials_page_keeps_its_analytics():
    """A rebuild must not silently ship the tool without analytics.

    The snippet is invisible on the page, so nothing else would reveal its
    loss. It lives in materials/src/index.html for exactly this reason.
    """
    page = (MATERIALS / "index.html").read_text(encoding="utf-8")
    assert "G-YG3SBRRZFZ" in page, "GA4 snippet missing from the built page"
    assert "analytics-autotrack.js" in page, "run scripts/inject_seo_meta.py"
    assert 'rel="canonical"' in page, "run scripts/inject_seo_meta.py"
