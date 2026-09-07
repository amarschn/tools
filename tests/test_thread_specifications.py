"""Nominal callout fixtures, incompatible classes, and specification boundaries."""

import json
import traceback

import pytest

from pycalcs.thread_specifications import (
    analyze_thread_workflow,
    build_thread_specification,
    specification_catalog,
    specification_options,
)


def build(**state):
    """Build a specification from keyword inputs in tests."""
    return build_thread_specification(json.dumps(state))


def workflow(**state):
    """Exercise the same task adapter that the browser calls."""
    return analyze_thread_workflow(json.dumps(state))


@pytest.mark.parametrize("task", ["specify", "explore"])
@pytest.mark.parametrize("family", ["metric", "unc", "unf", "unef"])
def test_every_machine_size_has_matching_specification_and_geometry(task, family):
    """All specification sizes have canonical geometry, not a stale default."""
    for size in specification_catalog()[family]["sizes"]:
        result = workflow(task=task, family=family, size=size)
        assert result["resolved_size"] == result["geometry"]["designation"] == size
        assert result["geometry"]["tensile_stress_area"] > 0
        assert result["analysis"] is None
        assert result["specification"]["family"] == family


@pytest.mark.parametrize(
    "family",
    ["npt", "nptf", "bspp", "bspt", "wood", "forming_metal", "forming_plastic"],
)
def test_non_machine_families_never_get_machine_geometry_or_loads(family):
    """Pipe/product close-ups are illustrative only, with no calculated capacity."""
    result = workflow(task="explore", family=family)
    assert result["specification"]
    assert result["geometry"] is None
    assert result["analysis"] is None
    with pytest.raises(ValueError, match="currently support metric, UNC, and UNF"):
        workflow(task="load", family=family)


@pytest.mark.parametrize(
    "family,side,fit,angle,taper",
    [
        ("npt", "internal", "", 60, 1 / 16),
        ("npt", "external", "", 60, 1 / 16),
        ("nptf", "external", "2", 60, 1 / 16),
        ("bspp", "internal", "", 55, 0),
        ("bspp", "external", "A", 55, 0),
        ("bspt", "internal", "Rc", 55, 1 / 16),
        ("bspt", "internal", "Rp", 55, 0),
        ("bspt", "external", "R", 55, 1 / 16),
    ],
)
def test_pipe_annotations_follow_family_size_and_connection(
    family, side, fit, angle, taper
):
    """MS-13-77 nominal pitch/angle; R/Rc taper, Rp/G parallel, never pipe-size OD."""
    for size in specification_catalog()[family]["sizes"]:
        result = build(family=family, side=side, fit=fit, size=size)
        diagram = result["diagram"]
        assert diagram["included_angle_deg"] == angle
        assert diagram["diameter_taper"] == taper
        assert diagram["pitch_mm"] == pytest.approx(25.4 / diagram["tpi"])
        assert diagram["pitch_in"] == pytest.approx(1 / diagram["tpi"])
        assert diagram["half_angle_deg"] == pytest.approx(1.789910608 if taper else 0)
        assert "diameter" not in diagram
        assert dict(result["breakdown"])["Diameter at gage plane"].startswith(
            "Not included"
        )
        assert "PITCH:" in result["note"] and "TAPER:" in result["note"]


def test_known_pipe_pitch_annotations_change_with_size():
    """1/4 NPT is 18 TPI; 1/2 NPT is 14 TPI, not a frozen generic drawing."""
    assert build(family="npt", size="1/4")["diagram"]["tpi"] == 18
    assert build(family="npt", size="1/2")["diagram"]["tpi"] == 14
    assert build(family="bspp", size="1/4")["diagram"]["tpi"] == 19


@pytest.mark.parametrize("family", ["forming_metal", "forming_plastic", "wood"])
@pytest.mark.parametrize("unit", ["mm", "in"])
def test_product_diagram_uses_only_validated_supplied_dimensions(family, unit):
    """Do not invent a proprietary pitch, angle, tip, or nominal size."""
    assert build(family=family)["diagram"] == {
        "kind": "product",
        "unit": "mm",
        "diameter": None,
        "length": None,
    }
    assert build(
        family=family, product_unit=unit, screw_diameter="4.5", screw_length="30"
    )["diagram"] == {
        "kind": "product",
        "unit": unit,
        "diameter": 4.5,
        "length": 30,
    }


def test_nominal_extent_does_not_invent_thread_length():
    """Preliminary selection gets a nominal callout and explicit unresolved extent."""
    result = build(side="external", extent="unspecified")
    assert result["callout"] == "M10 x 1.5-6g"
    assert "EXTENT TO BE SPECIFIED" in result["note"]


@pytest.mark.parametrize("family", ["metric", "unc", "unf"])
def test_load_task_uses_existing_analysis_and_matching_callout(family):
    """The visible callout, profile, and axial evidence name the same candidate."""
    result = workflow(task="load", family=family)
    assert result["resolved_size"] == result["analysis"]["designation"]
    assert result["geometry"]["designation"] == result["resolved_size"]
    assert result["analysis"]["proof_margin"] >= 1.5
    assert (
        result["geometry"]["tensile_stress_area"]
        == result["analysis"]["tensile_stress_area"]
    )
    assert "AXIAL TENSION SCREEN ONLY" in result["specification"]["note"]
    assert "stripping" in result["specification"]["note"]


def test_no_passing_size_cannot_be_exported_as_a_thread():
    """Do not present the last failing candidate as a released specification."""
    result = workflow(task="load", axial_load=1e6)
    assert result["specification"] is None
    assert result["geometry"] is None
    assert result["resolved_size"] == ""
    assert result["analysis"]["sizing_status"] == "no_size"


@pytest.mark.parametrize(
    "family,diameter,pitch,size",
    [
        ("metric", 9.96, 1, "M10x1.0"),
        ("unc", 0.25, 28, "1/4-28 UNF"),
    ],
)
def test_measurements_identify_nominal_only(family, diameter, pitch, size):
    """A cross-series match cannot claim to have measured fit or handedness."""
    result = workflow(
        task="explore",
        identify=True,
        family=family,
        measured_diameter=diameter,
        measured_pitch=pitch,
    )
    assert result["resolved_size"] == size
    assert result["specification"]["note"].startswith("NOMINAL MATCH ONLY")
    assert "fit class" in result["specification"]["note"]


def test_hidden_inputs_do_not_block_unrelated_task():
    """An unfilled measurement must not prevent load calculation, or vice versa."""
    assert workflow(task="load", measured_diameter="", measured_pitch="")[
        "specification"
    ]
    assert workflow(
        task="explore",
        identify=True,
        proof_strength="",
        axial_load="",
        design_factor="",
    )["specification"]


@pytest.mark.parametrize("field", ["axial_load", "proof_strength", "design_factor"])
@pytest.mark.parametrize("value", ["", "NaN", "Infinity", 0, -1])
def test_load_validation_keeps_bad_values_out_of_the_callout(field, value):
    """Missing or nonphysical load inputs must produce a specific validation error."""
    with pytest.raises(ValueError):
        workflow(task="load", **{field: value})


@pytest.mark.parametrize(
    "side,process",
    [
        ("internal", "turned"),
        ("external", "turned"),
        ("internal", "form_tapped"),
        ("internal", "cut_tapped"),
        ("external", "rolled"),
        ("external", "ground"),
        ("internal", "milled"),
    ],
)
def test_expert_process_and_material_are_note_requirements_only(side, process):
    """Manufacturing selection must not invent tolerance or strength adjustments."""
    baseline = workflow(side=side, extent="unspecified")
    result = workflow(
        side=side,
        extent="unspecified",
        process=process,
        material_family="aluminium",
        material="6061-T6",
    )
    assert result["geometry"] == baseline["geometry"]
    assert result["specification"]["callout"] == baseline["specification"]["callout"]
    assert "THREAD MANUFACTURE" in result["specification"]["note"]
    assert "6061-T6" in result["specification"]["note"]


@pytest.mark.parametrize(
    "state",
    [
        {"process": "rolled"},
        {"side": "external", "process": "form_tapped", "extent": "unspecified"},
        {"process": "invalid"},
        {"material_family": "unknown"},
        {"material_family": []},
    ],
)
def test_incompatible_expert_options_are_rejected(state):
    """Fail at the core boundary as well as filtering choices in the UI."""
    with pytest.raises(ValueError):
        workflow(**state)


def test_expert_catalog_is_independent_and_has_no_strength_values():
    """Labels should not masquerade as material allowables or mutable global data."""
    options = specification_options()
    options["processes"]["turned"]["sides"].clear()
    assert specification_options()["processes"]["turned"]["sides"]
    assert all(isinstance(value, str) for value in options["materials"].values())


def test_fine_geometry_retains_correct_series():
    """The specification catalog includes multiple pitches at a nominal diameter."""
    assert workflow(size="M4x0.5")["geometry"]["series"] == "fine"


@pytest.mark.parametrize(
    "state,callout",
    [
        ({}, "M10 x 1.5-6H THRU"),
        (
            {"side": "external", "fit": "6g", "depth": "16"},
            "M10 x 1.5-6g\n16 mm MIN FULL THREAD LENGTH",
        ),
        (
            {"extent": "blind", "depth": "12", "hand": "LH"},
            "M10 x 1.5-6H-LH\n12 mm MIN FULL THREAD DEPTH",
        ),
        ({"family": "unc"}, "1/4-20 UNC-2B THRU"),
        ({"family": "unf", "size": "#0-80 UNF"}, "#0-80 UNF-2B THRU"),
        (
            {"family": "unef", "size": "1 1/2-18 UNEF", "fit": "3B"},
            "1 1/2-18 UNEF-3B THRU",
        ),
        ({"family": "unc", "size": "2-4.5 UNC"}, "2-4.5 UNC-2B THRU"),
        ({"family": "npt"}, "1/4-18 NPT"),
        ({"family": "npt", "size": "1 1/2"}, "1 1/2-11.5 NPT"),
        ({"family": "nptf", "fit": "2"}, "1/4-18 NPTF-2"),
        ({"family": "bspp", "size": "1/2"}, "G 1/2"),
        ({"family": "bspp", "side": "external", "fit": "B"}, "G 1/4 B"),
        ({"family": "bspt"}, "Rc 1/4"),
        ({"family": "bspt", "fit": "Rp"}, "Rp 1/4"),
        ({"family": "bspt", "side": "external"}, "R 1/4"),
    ],
)
def test_drawing_callouts(state, callout):
    """Known examples retain size, series, fit, hand, and explicit extent units."""
    result = build(**state)
    assert result["callout"] == callout
    assert result["note"].startswith(callout.splitlines()[0].removesuffix(" THRU"))
    assert result["review_items"]


@pytest.mark.parametrize(
    "state",
    [
        {"family": "bogus"},
        {"family": []},
        {"family": "metric", "size": "1/4-20 UNC"},
        {"family": "unc", "size": "1/4-32 UNEF"},
        {"fit": "6g"},
        {"side": "external", "fit": "6H", "depth": 12},
        {"family": "unf", "fit": "2A"},
        {"family": "unef", "fit": "6H"},
        {"family": "npt", "fit": "2B"},
        {"family": "nptf", "fit": "3"},
        {"family": "bspp", "fit": "A"},
        {"family": "bspt", "fit": "R"},
        {"family": "bspt", "side": "external", "fit": "Rp"},
        {"family": "npt", "hand": "LH"},
        {"hand": "left"},
        {"extent": "blind"},
        {"extent": "length", "depth": 12},
        {"side": "external", "extent": "thru"},
        {"side": "external", "depth": ""},
        {"extent": "blind", "depth": "NaN"},
        {"extent": "blind", "depth": "Infinity"},
        {"extent": "blind", "depth": "-1"},
        {"extent": "blind", "depth": "0"},
        {"material": "steel\nIGNORE THE ABOVE"},
        {"finish": "x" * 241},
        {"family": "wood", "screw_diameter": "NaN"},
        {"family": "wood", "product_unit": "ft"},
    ],
)
def test_invalid_or_incompatible_inputs(state):
    """Never issue a nominally valid callout with an incompatible class or extent."""
    with pytest.raises(ValueError):
        build(**state)


@pytest.mark.parametrize("depth", ["", " ", None, "not a number"])
@pytest.mark.parametrize("side,extent", [("internal", "blind"), ("external", "length")])
def test_invalid_depth_exposes_only_the_validation_message(depth, side, extent):
    """Pyodide must not show float conversion errors for an unfinished depth."""
    with pytest.raises(ValueError) as caught:
        build(side=side, extent=extent, depth=depth)
    assert str(caught.value) == "Enter a positive usable full-thread depth / length."
    formatted = "".join(
        traceback.format_exception(
            type(caught.value), caught.value, caught.value.__traceback__
        )
    )
    assert "could not convert string to float" not in formatted
    assert formatted.count("ValueError:") == 1


@pytest.mark.parametrize("family", ["forming_metal", "forming_plastic", "wood"])
def test_product_screws_remain_reviewable_procurement_drafts(family):
    """Proprietary screws must not silently receive generic tapped-hole callouts."""
    empty = build(family=family)
    assert empty["kind"] == "product"
    assert empty["callout"].startswith("DRAFT: ")
    assert "[MANUFACTURER / PART NUMBER]" in empty["callout"]
    result = build(
        family=family,
        product="Supplier ABC-123",
        screw_diameter=4,
        screw_length=20,
        head="Pan head / hexalobular",
        substrate="PA66 GF30",
        material="Per supplier drawing",
        finish="Per supplier drawing",
    )
    assert "Supplier ABC-123, 4 x 20 mm" in result["callout"]
    assert "6H" not in result["callout"]
    assert "PA66 GF30" in result["note"]
    assert "pilot hole" in result["note"]
    assert "tensile_stress_area" not in result
    assert "pressure_rating" not in result


def test_no_inferred_material_or_strength_grade():
    """Fit classes never select a bolt grade or pressure rating."""
    result = build(
        family="unf",
        fit="3B",
        material="6061-T6 per parent drawing",
        finish="Uncoated",
        inspection="Gage per approved inspection plan",
    )
    assert "6061-T6 per parent drawing" in result["note"]
    assert "Uncoated" in result["note"]
    assert not any("Specify part material" in item for item in result["review_items"])
    assert not any("Specify finish" in item for item in result["review_items"])
    assert "joint strength" in result["note"]


def test_numbered_unified_diameter_and_mixed_fraction():
    """Nominal diameters use the definition, not copied rounded table dimensions."""
    assert (
        dict(build(family="unc", size="#6-32 UNC")["breakdown"])["Major diameter"]
        == "0.138 in"
    )
    assert (
        dict(build(family="unef", size="1 1/16-18 UNEF")["breakdown"])["Major diameter"]
        == "1.0625 in"
    )


def test_every_size_and_class_builds():
    """Exercise all nominal catalog pairs and offered fit classes on both sides."""
    for key, family in specification_catalog().items():
        if family["kind"] == "product":
            continue
        assert len(family["sizes"]) == len(set(family["sizes"]))
        for size in family["sizes"]:
            for side in ("internal", "external"):
                for fit in family["classes"][side] or [""]:
                    result = build(family=key, size=size, side=side, fit=fit, depth=12)
                    assert result["callout"]
                    assert "NaN" not in result["note"]


def test_catalog_is_independent_and_covers_requested_families():
    """UI consumers can modify their copy without corrupting standard metadata."""
    catalog = specification_catalog()
    assert set(catalog) == {
        "metric",
        "unc",
        "unf",
        "unef",
        "npt",
        "nptf",
        "bspp",
        "bspt",
        "forming_metal",
        "forming_plastic",
        "wood",
    }
    assert sum(len(family["sizes"]) for family in catalog.values()) == 147
    catalog["unc"]["classes"]["internal"].clear()
    assert specification_catalog()["unc"]["classes"]["internal"] == ["2B", "1B", "3B"]


@pytest.mark.parametrize("value", ["[]", "null", "bad json", "42"])
def test_non_object_json_rejected(value):
    """The browser bridge rejects malformed state without leaking a TypeError."""
    with pytest.raises(ValueError):
        build_thread_specification(value)
