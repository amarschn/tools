"""Static regression tests for the thread profile technical drawing."""

from __future__ import annotations

import re
from pathlib import Path

INDEX = (
    Path(__file__).resolve().parent.parent
    / "tools"
    / "thread-visualizer-sizer"
    / "index.html"
)


def _coordinate(value: str) -> tuple[float, float]:
    """Parse one SVG coordinate pair."""
    x_value, y_value = value.split(",")
    return float(x_value), float(y_value)


def test_thread_diagram_uses_one_persistent_svg() -> None:
    """View changes should update one authored SVG instead of replacing it."""
    source = INDEX.read_text(encoding="utf-8")

    assert source.count('id="thread-profile-svg"') == 1
    assert source.count('data-thread-layout="desktop"') == 1
    assert source.count('data-thread-layout="mobile"') == 1
    assert source.count('data-thread-view="external"') == 2
    assert source.count('data-thread-view="internal"') == 2
    assert source.count('data-thread-view="engaged"') == 2
    assert "thread-diagram').innerHTML" not in source
    assert "threadProfileSvg.setAttribute(" in source


def test_thread_dimensions_do_not_use_svg_markers() -> None:
    """Dimension arrowheads should be explicit geometry with fixed endpoints."""
    source = INDEX.read_text(encoding="utf-8")

    assert "<marker" not in source
    assert "marker-start" not in source
    assert "marker-end" not in source
    assert source.count('class="dimension-arrow"') == 20


def test_pitch_arrow_tips_match_dimension_endpoints() -> None:
    """Every authored pitch arrow tip should land on its dimension line."""
    source = INDEX.read_text(encoding="utf-8")
    groups = re.findall(
        r'<g aria-label="Pitch dimension">(.*?)</g>',
        source,
        flags=re.DOTALL,
    )

    assert len(groups) == 6
    for group in groups:
        line = re.search(
            r'class="dimension-line"'
            r' x1="([^"]+)" y1="([^"]+)"'
            r' x2="([^"]+)" y2="([^"]+)"',
            group,
        )
        assert line is not None
        start = float(line.group(1)), float(line.group(2))
        end = float(line.group(3)), float(line.group(4))

        arrow_points = re.findall(
            r'class="dimension-arrow" points="([^"]+)"',
            group,
        )
        assert len(arrow_points) == 2
        tips = [_coordinate(points.split()[0]) for points in arrow_points]

        assert tips == [start, end]


def test_thread_drawing_keeps_normalized_geometry_and_accessibility() -> None:
    """The SVG should retain its normalized model and accessible description."""
    source = INDEX.read_text(encoding="utf-8")

    assert "const THREAD_DRAWING_PITCH = 100;" in source
    assert 'id="thread-svg-title"' in source
    assert 'id="thread-svg-desc"' in source
    assert 'aria-labelledby="thread-svg-title thread-svg-desc"' in source
    assert "threadDiagramMedia.addEventListener('change'" in source


def test_three_tasks_share_a_single_result_workspace() -> None:
    """Task navigation must not reintroduce separate calculator/background layouts."""
    source = INDEX.read_text(encoding="utf-8")
    assert source.count('aria-controls="thread-task-panel"') == 3
    assert source.count('id="spec-output"') == 1
    assert source.count('id="drawing-callout"') == 1
    assert source.count('id="thread-profile-svg"') == 1
    for task in ("specify", "load", "find"):
        assert f'data-section="{task}"' in source
    assert 'id="tab-background"' not in source
    assert source.index('class="thread-reference-area"') > source.index(
        'id="spec-output"'
    )


def test_complexity_is_collapsed_until_requested() -> None:
    """Expert inputs and calculation evidence are opt-in; copyable notes are visible."""
    source = INDEX.read_text(encoding="utf-8")
    for element_id in (
        "thread-details",
        "expert-options",
        "dimension-details",
        "calculation-details",
        "thread-guide",
    ):
        tag = re.search(rf'<details[^>]+id="{element_id}"[^>]*>', source)
        assert tag is not None
        assert " open" not in tag.group()


def test_copy_icons_are_next_to_visible_callout_and_note() -> None:
    """Readers should see the text they copy without opening a details element."""
    source = INDEX.read_text(encoding="utf-8")
    note = re.search(r'<section[^>]+id="note-details".*?</section>', source, re.DOTALL)
    assert note is not None
    assert 'id="spec-note"' in note.group()
    assert 'id="copy-detailed-note"' in note.group()
    assert 'id="review-details"' not in source
    for button_id, label in (
        ("copy-drawing-callout", "Copy callout"),
        ("copy-detailed-note", "Copy detailed note"),
    ):
        button = re.search(
            rf'<button[^>]+id="{button_id}".*?</button>', source, re.DOTALL
        )
        assert button is not None
        assert f'aria-label="{label}"' in button.group()
        assert 'class="copy-glyph"' in button.group()
        assert 'class="copied-glyph"' in button.group()


def test_every_field_has_authored_help_for_its_visible_button() -> None:
    """Do not ship another advanced control with an unexplained help icon."""
    source = INDEX.read_text(encoding="utf-8")
    form = re.search(r'<form id="spec-form".*?</form>', source, re.DOTALL)
    assert form is not None
    fields = re.findall(r"<(?:input|select)\b[^>]*>", form.group())
    assert fields
    for field in fields:
        title = re.search(r'title="([^"]+)"', field)
        described_by = re.search(r'aria-describedby="([^"]+)"', field)
        assert title or described_by, field
        if described_by:
            for element_id in described_by.group(1).split():
                assert f'id="{element_id}"' in source
    assert source.index('src="thread-help.js?') < source.index(
        'src="thread-specification.js?'
    )
