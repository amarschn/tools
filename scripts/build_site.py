#!/usr/bin/env python3
"""Run the generated-file steps required by both production hosts."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent


def run(script: str, *arguments: str) -> None:
    subprocess.run(
        [sys.executable, str(SCRIPTS / script), *arguments],
        cwd=REPO,
        check=True,
    )


def main() -> None:
    run("generate_sitemap.py")
    run("inject_seo_meta.py")
    run("version_thread_assets.py")
    run("generate_homepage_metadata.py", "--check")


if __name__ == "__main__":
    main()
