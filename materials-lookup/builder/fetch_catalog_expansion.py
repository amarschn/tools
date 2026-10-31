#!/usr/bin/env python3
"""Cache public CDA reference pages for the October 2026 catalog review.

Development only. Reads public HTML, never the authenticated CDA API. Existing
files are reused; importers separately check the reviewed snapshot hashes.
Original pages belong in the git-ignored private-sources directory.
"""

from __future__ import annotations

import argparse
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import urlopen


def download(url: str, path: Path) -> str:
    """Cache one public HTML page with bounded retries and request pacing."""
    if path.exists():
        return path.read_text()
    for attempt in range(3):
        try:
            with urlopen(url, timeout=40) as response:
                data = response.read()
            if b"<html" not in data.lower() or b"copper" not in data.lower():
                raise ValueError(f"Unexpected page: {url} ({len(data)} bytes)")
            path.write_bytes(data)
            time.sleep(0.35)
            return data.decode("utf-8")
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("Unreachable")


def main() -> None:
    """Discover public alloy links, then cache each page with two workers."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    first = download("https://alloys.copper.org/", args.output / "index-0.html")
    total = int(re.search(r"([0-9]+) Alloys Found", first)[1])
    codes = set(re.findall(r"/alloy/(C\d{5})", first))
    for start in range(50, total, 50):
        html = download(
            f"https://alloys.copper.org/search/alloys/browse?q=&start={start}",
            args.output / f"index-{start}.html",
        )
        codes.update(re.findall(r"/alloy/(C\d{5})", html))
    if len(codes) != total:
        raise ValueError(f"Index changed during retrieval: {len(codes)} != {total}")
    print(f"Discovered {total} public alloy references", flush=True)

    def fetch(code: str) -> str:
        download(
            f"https://alloys.copper.org/alloy/{code}", args.output / f"{code}.html"
        )
        return code

    with ThreadPoolExecutor(max_workers=2) as pool:
        for index, code in enumerate(pool.map(fetch, sorted(codes)), 1):
            if index % 50 == 0 or index == total:
                print(f"Cached {index}/{total}: {code}", flush=True)


if __name__ == "__main__":
    main()
