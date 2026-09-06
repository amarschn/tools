"""Keep the thread page, controllers and Python sources on one cache revision."""

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TOOL = REPO / "tools" / "thread-visualizer-sizer"
INDEX = TOOL / "index.html"
VERSION = re.compile(r'(?<=content=")thread-[\w-]+(?=")|(?<=\?v=)thread-[\w-]+')


def versioned_index() -> str:
    """Return HTML whose local asset URLs share a source-content fingerprint.

    Normalize generated tokens before hashing to make repeated runs idempotent.
    Include inline UI code, all tool-owned JS/CSS (including lazy exports), and
    each Python dependency. Vendor directory names already pin exact versions.
    """
    source = INDEX.read_text(encoding="utf-8")
    digest = hashlib.sha256()
    paths = sorted(
        [INDEX, *TOOL.glob("*.js"), *TOOL.glob("*.css")]
        + [REPO / "pycalcs" / (name + ".py") for name in (
            "fasteners", "threads", "thread_specifications", "thread_models"
        )]
    )
    for path in paths:
        content = path.read_bytes()
        if path == INDEX:
            content = VERSION.sub("thread-BUILD", source).encode("utf-8")
        digest.update(str(path.relative_to(REPO)).encode("utf-8") + b"\0")
        digest.update(content + b"\0")
    return VERSION.sub("thread-" + digest.hexdigest()[:16], source)


def main() -> None:
    """Refresh generated URLs, or fail --check when an edit needs a new key."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = versioned_index()
    if INDEX.read_text(encoding="utf-8") == expected:
        return
    if args.check:
        parser.exit(1, "Thread asset keys are stale. Run scripts/version_thread_assets.py.\n")
    INDEX.write_text(expected, encoding="utf-8")
    print("Updated thread asset cache keys.")


if __name__ == "__main__":
    main()
