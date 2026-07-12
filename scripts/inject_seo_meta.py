#!/usr/bin/env python3
"""Backfill SEO meta tags + analytics autotrack into each tool's index.html.

Reads titles/descriptions from catalog.json (single source of truth) and inserts,
immediately after each tool's <title> tag, any of these that are MISSING:

  - <meta name="description">
  - <link rel="canonical">
  - OpenGraph + Twitter card tags
  - <script src="/shared/analytics-autotrack.js" defer>

Idempotent: re-running only adds what is absent, so it is a clean no-op once
applied. Skips example/prototype tools. Run from anywhere:

    python3 scripts/inject_seo_meta.py            # apply
    python3 scripts/inject_seo_meta.py --check    # report only, no writes
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CATALOG = REPO / "catalog.json"
BASE = "https://transparent.tools"
OG_IMAGE = f"{BASE}/og-image.png"
EXCLUDE_PREFIXES = ("example_tool", "unit_conversion_prototyping")

AUTOTRACK_SRC = "/shared/analytics-autotrack.js"


def tool_slug(path: str) -> str | None:
    m = re.search(r"tools/([^/]+)/", path)
    return m.group(1) if m else None


def clean_desc(desc: str) -> str:
    desc = " ".join(desc.split())
    if len(desc) > 155:
        desc = desc[:152].rstrip() + "..."
    return html.escape(desc, quote=True)


def page_title(source: str, fallback: str) -> str:
    m = re.search(r"<title>(.*?)</title>", source, re.DOTALL)
    title = m.group(1).strip() if m and m.group(1).strip() else fallback
    return html.escape(html.unescape(title), quote=True)


def build_block(entry: dict, source: str, slug: str) -> tuple[str, list[str]]:
    """Return (indented_html_block, list_of_added_tag_names). Only missing tags."""
    canonical = f"{BASE}/tools/{slug}/"
    desc = clean_desc(entry.get("description", entry.get("title", "")))
    title = page_title(source, entry.get("title", slug))

    added: list[str] = []
    lines: list[str] = []

    if 'name="description"' not in source:
        lines.append(f'    <meta name="description" content="{desc}">')
        added.append("description")
    if 'rel="canonical"' not in source:
        lines.append(f'    <link rel="canonical" href="{canonical}">')
        added.append("canonical")
    if "og:title" not in source:
        lines.extend(
            [
                f'    <meta property="og:type" content="website">',
                f'    <meta property="og:title" content="{title}">',
                f'    <meta property="og:description" content="{desc}">',
                f'    <meta property="og:url" content="{canonical}">',
                f'    <meta property="og:image" content="{OG_IMAGE}">',
                f'    <meta name="twitter:card" content="summary_large_image">',
                f'    <meta name="twitter:title" content="{title}">',
                f'    <meta name="twitter:description" content="{desc}">',
                f'    <meta name="twitter:image" content="{OG_IMAGE}">',
            ]
        )
        added.append("opengraph")
    if AUTOTRACK_SRC not in source:
        lines.append(f'    <script src="{AUTOTRACK_SRC}" defer></script>')
        added.append("autotrack")

    return ("\n".join(lines), added)


def patch_tool(slug: str, entry: dict, check: bool) -> str:
    path = REPO / "tools" / slug / "index.html"
    if not path.exists():
        return f"  SKIP {slug}: no index.html"
    source = path.read_text()
    if "<title>" not in source:
        return f"  SKIP {slug}: no <title> to anchor insertion"

    block, added = build_block(entry, source, slug)
    if not added:
        return f"  ok   {slug}: already complete"
    if check:
        return f"  WOULD add [{', '.join(added)}] to {slug}"

    new_source = re.sub(
        r"(</title>)",
        r"\1\n" + block,
        source,
        count=1,
    )
    path.write_text(new_source)
    return f"  +    {slug}: added [{', '.join(added)}]"


def main() -> None:
    check = "--check" in sys.argv
    catalog = json.loads(CATALOG.read_text())
    results = []
    for entry in catalog:
        slug = tool_slug(entry.get("path", ""))
        if not slug or slug.startswith(EXCLUDE_PREFIXES):
            continue
        results.append(patch_tool(slug, entry, check))

    for line in results:
        print(line)
    changed = sum(1 for r in results if r.strip().startswith(("+", "WOULD")))
    print(f"\n{'Would change' if check else 'Changed'} {changed} tool(s).")


if __name__ == "__main__":
    main()
