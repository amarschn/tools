"""Catch JavaScript parse errors that prevent the resonance tool from starting."""

from html.parser import HTMLParser
from pathlib import Path
import shutil
import subprocess

import pytest


class InlineScripts(HTMLParser):
    """Collect executable inline scripts, excluding external and data scripts."""

    def __init__(self):
        super().__init__()
        self.scripts = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "script" and "src" not in attributes:
            if attributes.get("type", "") in ("", "module", "text/javascript"):
                self.current = []

    def handle_data(self, data):
        if self.current is not None:
            self.current.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.current is not None:
            self.scripts.append("".join(self.current))
            self.current = None


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is not installed")
def test_resonance_javascript_parses(tmp_path):
    """Literal newlines in JS strings previously stopped all initialization."""
    page = Path(__file__).resolve().parents[1] / "tools/structural-resonance/index.html"
    parser = InlineScripts()
    parser.feed(page.read_text())
    assert parser.scripts, "No inline scripts found in the tool"
    sources = parser.scripts + [path.read_text() for path in page.parent.glob("*.js")]
    for index, source in enumerate(sources):
        script = tmp_path / f"inline-{index}.mjs"
        script.write_text(source)
        result = subprocess.run(
            [shutil.which("node"), "--check", str(script)],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert result.returncode == 0, result.stderr
