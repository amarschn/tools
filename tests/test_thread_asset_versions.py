"""Cache keys must change with source edits, without defeating warm caching."""

import re

from scripts import version_thread_assets as assets


def test_checked_in_thread_asset_keys_are_current() -> None:
    source = assets.INDEX.read_text(encoding="utf-8")
    assert source == assets.versioned_index(), "Run scripts/version_thread_assets.py"
    keys = assets.VERSION.findall(source)
    assert len(keys) == 7  # One shared meta key, five controllers, one stylesheet.
    assert len(set(keys)) == 1
    assert re.fullmatch(r"thread-[a-f0-9]{16}", keys[0])


def test_revision_tracks_sources_and_is_idempotent(tmp_path, monkeypatch) -> None:
    tool = tmp_path / "tools" / "thread-visualizer-sizer"
    tool.mkdir(parents=True)
    calculations = tmp_path / "pycalcs"
    calculations.mkdir()
    for name in ("fasteners", "threads", "thread_specifications", "thread_models"):
        (calculations / (name + ".py")).write_text("# initial\n")
    index = tool / "index.html"
    index.write_text('<meta name="thread-asset-version" content="thread-dev">')
    controller = tool / "thread-specification.js"
    controller.write_text("// initial\n")
    monkeypatch.setattr(assets, "REPO", tmp_path)
    monkeypatch.setattr(assets, "TOOL", tool)
    monkeypatch.setattr(assets, "INDEX", index)
    rendered = assets.versioned_index()
    index.write_text(rendered)
    assert rendered == assets.versioned_index()
    for path in (controller, calculations / "thread_models.py", index):
        path.write_text(path.read_text() + "\n")
        next_rendered = assets.versioned_index()
        assert next_rendered != rendered
        index.write_text(next_rendered)
        assert next_rendered == assets.versioned_index()
        rendered = next_rendered


def test_lazy_export_controllers_use_the_page_revision() -> None:
    source = (assets.TOOL / "thread-exports.js").read_text(encoding="utf-8")
    for path in ("thread-print.js", "thread-cad-worker.js"):
        assert f"window.threadAssetUrl('{path}')" in source
