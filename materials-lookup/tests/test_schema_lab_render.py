"""Demo rendering: unit preference, precision, and the drill-down as displayed."""

import json
import unittest
from pathlib import Path

from schema_lab.projections import Corpus, active, span
from schema_lab.render import display_span, render_material, render_units
from schema_lab.units import (
    find_conversion,
    format_significant,
    round_to_significant_figures,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_PATH = REPO_ROOT / "fixtures" / "schema-lab" / "v0.1.0" / "corpus.json"

DRILLDOWN_MATERIAL = "synthetic-synal-ax70"
ADVERSARIAL_MATERIAL = "synthetic-advdemo-cfpeek"


def load_corpus():
    return Corpus(json.loads(CORPUS_PATH.read_text(encoding="utf-8")))


class FormatTest(unittest.TestCase):
    def test_plain_decimal_is_used_for_engineering_magnitudes(self):
        """130 MPa at two significant figures must not render as 1.3e+02."""
        self.assertEqual(format_significant(130.0, 2), "130")
        self.assertEqual(format_significant(0.48, 2), "0.48")
        self.assertEqual(format_significant(79.48, 3), "79.5")
        self.assertEqual(format_significant(1410.0, 4), "1410")

    def test_scientific_notation_survives_for_extreme_magnitudes(self):
        self.assertIn("e", format_significant(4.1e-08, 2))

    def test_zero_and_non_finite_are_handled(self):
        self.assertEqual(format_significant(0.0, 3), "0")
        self.assertEqual(format_significant(float("inf"), 3), "inf")

    def test_rounding_does_not_add_precision(self):
        self.assertEqual(round_to_significant_figures(548_000_000, 3), 548_000_000)
        self.assertEqual(round_to_significant_figures(79.4838, 3), 79.5)


class SpanPrecisionTest(unittest.TestCase):
    def setUp(self):
        self.corpus = load_corpus()

    def test_span_carries_its_least_precise_contributor(self):
        observations = active(
            self.corpus.observations_by_material[DRILLDOWN_MATERIAL]
        )
        entry = span(observations, "ultimate_tensile_strength")
        contributors = [
            row["result"]["reported"]["significant_figures"]
            for row in observations
            if row["property_id"] == "ultimate_tensile_strength"
        ]
        self.assertEqual(entry["significant_figures"], min(contributors))

    def test_empty_span_reports_no_precision(self):
        observations = self.corpus.observations_by_material[ADVERSARIAL_MATERIAL]
        entry = span(observations, "electrical_resistivity")
        self.assertIsNone(entry["significant_figures"])


class DisplayUnitTest(unittest.TestCase):
    def setUp(self):
        self.corpus = load_corpus()
        self.property = self.corpus.properties["ultimate_tensile_strength"]
        self.observations = active(
            self.corpus.observations_by_state["synthetic-synal-ax70-t6"]
        )
        self.span = span(self.observations, "ultimate_tensile_strength")

    def test_metric_is_the_default(self):
        self.assertIn("MPa", display_span(self.span, self.property, "metric"))

    def test_imperial_converts_correctly(self):
        text = display_span(self.span, self.property, "imperial")
        self.assertIn("ksi", text)
        conversion = find_conversion("pressure", "ksi")
        expected = format_significant(
            conversion.to_display(self.span["minimum"]),
            self.span["significant_figures"],
        )
        self.assertIn(expected, text)

    def test_switching_units_never_adds_significant_figures(self):
        """The whole reason the reported form was kept at checkpoint 1."""
        figures = self.span["significant_figures"]
        for system in ("metric", "imperial"):
            text = display_span(self.span, self.property, system)
            number = text.split()[0].lstrip("≥").strip()
            digits = [ch for ch in number if ch.isdigit()]
            with self.subTest(system=system):
                self.assertLessEqual(len(digits), figures + 1)

    def test_a_singleton_renders_one_value_not_a_degenerate_range(self):
        text = display_span(self.span, self.property, "metric")
        self.assertNotIn("–", text)
        self.assertIn("1 reported value", text)

    def test_a_bound_is_marked_rather_than_shown_as_a_value(self):
        observations = self.corpus.observations_by_material[ADVERSARIAL_MATERIAL]
        entry = span(observations, "tensile_yield_strength")
        text = display_span(entry, self.corpus.properties["tensile_yield_strength"], "metric")
        self.assertTrue(text.startswith("≥"))

    def test_missing_data_is_distinguished_from_zero(self):
        observations = self.corpus.observations_by_material[ADVERSARIAL_MATERIAL]
        entry = span(observations, "electrical_resistivity")
        text = display_span(entry, self.corpus.properties["electrical_resistivity"], "metric")
        self.assertIn("not reported", text)
        self.assertNotIn("0 ", text)

    def test_absent_coverage_renders_as_no_data(self):
        self.assertEqual(
            display_span(None, self.property, "metric"), "no data"
        )


class RenderMaterialTest(unittest.TestCase):
    def setUp(self):
        self.corpus = load_corpus()

    def test_every_level_appears_with_a_range(self):
        text = render_material(
            self.corpus, DRILLDOWN_MATERIAL, "ultimate_tensile_strength"
        )
        self.assertIn("Synal AX70:", text)
        self.assertIn("T6:", text)
        self.assertIn("plate:", text)

    def test_narrowing_is_visible_in_the_output(self):
        text = render_material(
            self.corpus, DRILLDOWN_MATERIAL, "ultimate_tensile_strength"
        )
        self.assertIn("481", text)
        self.assertIn("548", text)

    def test_an_undesignated_material_says_so(self):
        text = render_material(self.corpus, ADVERSARIAL_MATERIAL)
        self.assertIn("no standard designation", text)

    def test_supplemental_classification_is_shown(self):
        text = render_material(self.corpus, ADVERSARIAL_MATERIAL)
        self.assertIn("also classified under", text)

    def test_provenance_includes_superseded_observations(self):
        text = render_material(
            self.corpus, ADVERSARIAL_MATERIAL, "thermal_conductivity"
        )
        self.assertIn("[superseded]", text)

    def test_superseded_values_stay_out_of_the_reported_range(self):
        text = render_material(
            self.corpus, ADVERSARIAL_MATERIAL, "thermal_conductivity"
        )
        headline = text.split("Provenance")[0]
        self.assertIn("0.48", headline)
        self.assertNotIn("0.42", headline)

    def test_direct_grade_data_is_labelled_separately_from_states(self):
        text = render_material(
            self.corpus, ADVERSARIAL_MATERIAL, "max_service_temperature"
        )
        self.assertIn("reported for the grade itself", text)

    def test_rendering_is_deterministic(self):
        first = render_material(self.corpus, DRILLDOWN_MATERIAL)
        second = render_material(load_corpus(), DRILLDOWN_MATERIAL)
        self.assertEqual(first, second)

    def test_every_material_renders_without_error(self):
        for material_id in self.corpus.materials:
            with self.subTest(material=material_id):
                self.assertTrue(render_material(self.corpus, material_id).strip())


class UnitListingTest(unittest.TestCase):
    def test_pressure_offers_both_systems(self):
        corpus = load_corpus()
        text = render_units(corpus.properties["ultimate_tensile_strength"])
        self.assertIn("metric", text)
        self.assertIn("imperial", text)
        self.assertIn("ksi", text)


if __name__ == "__main__":
    unittest.main()
