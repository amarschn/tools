"""Derived semantics gate: counting, ranges, inheritance, ordering, and goldens."""

import json
import unittest
from pathlib import Path

from schema_lab.goldens import build as build_goldens
from schema_lab.projections import (
    Corpus,
    assemble_material_record,
    coverage,
    drilldown_levels,
    effective_context,
    mixed_condition_flags,
    navigation_ranges,
    span,
    taxon_coverage,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DIR = REPO_ROOT / "fixtures" / "schema-lab" / "v0.1.0"
CORPUS_PATH = FIXTURE_DIR / "corpus.json"
GOLDEN_DIR = FIXTURE_DIR / "goldens"

ADVERSARIAL_MATERIAL = "synthetic-advdemo-cfpeek"
DRILLDOWN_MATERIAL = "synthetic-synal-ax70"
SURVEY_PROPERTY = "ultimate_tensile_strength"


def load_corpus():
    return json.loads(CORPUS_PATH.read_text(encoding="utf-8"))


class SpanTest(unittest.TestCase):
    def setUp(self):
        self.corpus = Corpus(load_corpus())

    def test_no_coverage_is_empty_not_zero(self):
        """A missing property is neither zero nor inherited."""
        result = span(
            self.corpus.observations_by_material.get(DRILLDOWN_MATERIAL, []),
            "shore_a_hardness",
        )
        self.assertIsNone(result)

    def test_single_value_is_a_singleton_not_a_degenerate_range(self):
        observations = self.corpus.observations_by_state[
            "synthetic-synal-ax70-t6"
        ]
        result = span(observations, SURVEY_PROPERTY)
        self.assertTrue(result["singleton"])
        self.assertEqual(result["minimum"], result["maximum"])

    def test_interval_contributes_its_endpoints(self):
        observations = self.corpus.observations_by_material[ADVERSARIAL_MATERIAL]
        result = span(observations, SURVEY_PROPERTY)
        self.assertEqual(result["minimum"], 210_000_000)
        self.assertEqual(result["maximum"], 240_000_000)

    def test_uncertainty_does_not_widen_the_span(self):
        """Density is 1410 +/- 15; the span is 1410, not 1395-1425."""
        observations = self.corpus.observations_by_material[ADVERSARIAL_MATERIAL]
        result = span(observations, "density")
        self.assertEqual(result["minimum"], 1410)
        self.assertEqual(result["maximum"], 1410)
        self.assertTrue(result["singleton"])

    def test_superseded_observations_are_excluded_by_default(self):
        observations = self.corpus.observations_by_material[ADVERSARIAL_MATERIAL]
        default = span(observations, "thermal_conductivity")
        self.assertEqual(default["observation_count"], 1)
        self.assertEqual(default["minimum"], 0.48)

    def test_superseded_observations_remain_auditable(self):
        observations = self.corpus.observations_by_material[ADVERSARIAL_MATERIAL]
        history = span(observations, "thermal_conductivity", include_superseded=True)
        self.assertEqual(history["observation_count"], 2)
        self.assertEqual(history["minimum"], 0.42)

    def test_unavailable_assertions_are_counted_not_ranged(self):
        observations = self.corpus.observations_by_material[ADVERSARIAL_MATERIAL]
        result = span(observations, "electrical_resistivity")
        self.assertEqual(result["observation_count"], 0)
        self.assertEqual(result["unavailable_count"], 1)
        self.assertIsNone(result["minimum"])

    def test_a_bound_is_flagged_rather_than_silently_treated_as_a_value(self):
        observations = self.corpus.observations_by_material[ADVERSARIAL_MATERIAL]
        result = span(observations, "tensile_yield_strength")
        self.assertTrue(result["includes_bound"])


class InheritanceTest(unittest.TestCase):
    """Checkpoint 1, decision 5: measurements never inherit silently."""

    def setUp(self):
        self.corpus = Corpus(load_corpus())
        self.record = assemble_material_record(self.corpus, ADVERSARIAL_MATERIAL)

    def test_direct_material_data_does_not_flow_into_states(self):
        direct_properties = {
            row["property_id"] for row in self.record["direct_observations"]
        }
        self.assertIn("max_service_temperature", direct_properties)
        for state in self.record["states"]:
            state_properties = {row["property_id"] for row in state["observations"]}
            with self.subTest(state=state["id"]):
                self.assertNotIn("max_service_temperature", state_properties)

    def test_state_data_does_not_flow_up_to_the_material(self):
        direct_properties = {
            row["property_id"] for row in self.record["direct_observations"]
        }
        self.assertNotIn(SURVEY_PROPERTY, direct_properties)

    def test_sibling_states_do_not_share_observations(self):
        corpus = Corpus(load_corpus())
        record = assemble_material_record(corpus, DRILLDOWN_MATERIAL)
        seen = set()
        for state in record["states"]:
            for observation in state["observations"]:
                with self.subTest(observation=observation["id"]):
                    self.assertNotIn(observation["id"], seen)
                    seen.add(observation["id"])


class EffectiveContextTest(unittest.TestCase):
    def setUp(self):
        self.corpus = Corpus(load_corpus())

    def test_context_unions_state_and_observation_without_mutating(self):
        observation = self.corpus.observations_by_state["synthetic-synal-ax70-t6"][0]
        before = json.dumps(observation, sort_keys=True)
        context = effective_context(observation, self.corpus)
        self.assertEqual(context.get("temper"), "T6")
        self.assertIn("product_form", context)
        self.assertEqual(json.dumps(observation, sort_keys=True), before)

    def test_stored_containers_stay_separate(self):
        """The union is a display view; storage keeps placement checkable."""
        observation = self.corpus.observations_by_state["synthetic-synal-ax70-t6"][0]
        self.assertNotIn("temper", observation["conditions"])

    def test_context_is_sorted_for_stable_rendering(self):
        observation = self.corpus.observations_by_state["synthetic-synal-ax70-t6"][0]
        context = effective_context(observation, self.corpus)
        self.assertEqual(list(context), sorted(context))


class CoverageCountTest(unittest.TestCase):
    def setUp(self):
        self.corpus = Corpus(load_corpus())

    def test_a_state_with_two_observations_is_one_subject_and_two_observations(self):
        observations = self.corpus.observations_by_state["synthetic-synal-ax70-t6"]
        counts = coverage(observations, self.corpus)
        self.assertEqual(counts["observations"], len(observations))
        result = taxon_coverage(self.corpus, "aluminium-like-alloys", SURVEY_PROPERTY)
        self.assertGreater(result["eligible_subjects"], result["materials"])

    def test_supplemental_membership_does_not_double_count(self):
        """CF-PEEK browses under a chemistry path and a composite path.

        Counting it in both would inflate every ancestor of both paths, so the
        invariant is that summing each root category's members reproduces the
        material count exactly.
        """
        material = self.corpus.materials[ADVERSARIAL_MATERIAL]
        self.assertTrue(material["supplemental_taxon_ids"])

        roots = [
            taxon_id
            for taxon_id, taxon in self.corpus.taxa.items()
            if taxon["primary_parent_id"] is None
        ]
        total = sum(len(self.corpus.materials_under(root)) for root in roots)
        self.assertEqual(
            total,
            len(self.corpus.materials),
            "a material counted under two paths would make the roots sum too high",
        )

        under_primary = {
            row["id"] for row in self.corpus.materials_under("peek-like-polymers")
        }
        under_supplemental = {
            row["id"] for row in self.corpus.materials_under("fiber-reinforced-polymers")
        }
        self.assertIn(ADVERSARIAL_MATERIAL, under_primary)
        self.assertNotIn(ADVERSARIAL_MATERIAL, under_supplemental)

    def test_an_empty_category_is_a_valid_empty_result(self):
        result = taxon_coverage(self.corpus, "thermosets", SURVEY_PROPERTY)
        self.assertEqual(result["materials"], 0)
        self.assertEqual(result["observation_count"], 0)
        self.assertIsNone(result["minimum"])

    def test_a_category_with_members_but_no_data_is_not_zero(self):
        result = taxon_coverage(self.corpus, "ceramics", SURVEY_PROPERTY)
        self.assertGreater(result["materials"], 0)
        self.assertEqual(result["covered_subjects"], 0)
        self.assertIsNone(result["minimum"])

    def test_categories_never_own_observations(self):
        for taxon_id in self.corpus.taxa:
            with self.subTest(taxon=taxon_id):
                self.assertNotIn(taxon_id, self.corpus.observations_by_material)

    def test_counts_are_kept_separate(self):
        counts = coverage(
            self.corpus.observations_by_material[ADVERSARIAL_MATERIAL], self.corpus
        )
        for key in (
            "observations",
            "properties_covered",
            "unavailable_assertions",
            "condition_sets",
            "bases",
            "sources",
        ):
            self.assertIn(key, counts)
        self.assertEqual(counts["unavailable_assertions"], 2)


class DrilldownTest(unittest.TestCase):
    """The checkpoint 1 decision: product form is a level, thickness is not."""

    def setUp(self):
        self.corpus = Corpus(load_corpus())

    def test_product_form_is_the_only_navigable_condition(self):
        self.assertEqual(self.corpus.navigable_conditions(), ["product_form"])

    def test_a_state_offers_a_product_form_level(self):
        levels = drilldown_levels(
            self.corpus, DRILLDOWN_MATERIAL, "synthetic-synal-ax70-t6"
        )
        self.assertEqual([level["condition_id"] for level in levels], ["product_form"])
        self.assertEqual([entry["value"] for entry in levels[0]["values"]], ["plate"])

    def test_a_level_is_absent_rather_than_empty_when_unused(self):
        material_id = "synthetic-wooddemo-w1"
        if material_id not in self.corpus.materials:
            self.skipTest("wood fixture absent")
        levels = drilldown_levels(self.corpus, material_id)
        self.assertEqual(levels, [])

    def test_every_level_reports_a_range(self):
        ranges = navigation_ranges(self.corpus, DRILLDOWN_MATERIAL, SURVEY_PROPERTY)
        self.assertIsNotNone(ranges["material"])
        for state in ranges["states"]:
            with self.subTest(state=state["state_id"]):
                self.assertIsNotNone(state["span"])
                for level in state["levels"]:
                    for entry in level["values"]:
                        self.assertIsNotNone(entry["span"])

    def test_narrowing_never_widens_the_range(self):
        """AX70 shows the envelope; T6 narrows it; plate narrows it further."""
        ranges = navigation_ranges(self.corpus, DRILLDOWN_MATERIAL, SURVEY_PROPERTY)
        material = ranges["material"]
        for state in ranges["states"]:
            with self.subTest(state=state["state_id"]):
                self.assertGreaterEqual(state["span"]["minimum"], material["minimum"])
                self.assertLessEqual(state["span"]["maximum"], material["maximum"])
                for level in state["levels"]:
                    for entry in level["values"]:
                        self.assertGreaterEqual(
                            entry["span"]["minimum"], state["span"]["minimum"]
                        )
                        self.assertLessEqual(
                            entry["span"]["maximum"], state["span"]["maximum"]
                        )

    def test_level_values_are_ordered_alphabetically_not_numerically(self):
        for state in self.corpus.states_by_material.get(DRILLDOWN_MATERIAL, []):
            for level in drilldown_levels(self.corpus, DRILLDOWN_MATERIAL, state["id"]):
                values = [entry["value"] for entry in level["values"]]
                with self.subTest(state=state["id"]):
                    self.assertEqual(values, sorted(values))


class MixedConditionTest(unittest.TestCase):
    def setUp(self):
        self.corpus = Corpus(load_corpus())

    def test_flags_are_sorted_and_deterministic(self):
        observations = self.corpus.observations_by_material[ADVERSARIAL_MATERIAL]
        first = mixed_condition_flags(observations, self.corpus)
        second = mixed_condition_flags(list(observations), self.corpus)
        self.assertEqual(first, second)
        self.assertEqual(first, sorted(first))

    def test_a_mixed_basis_is_flagged(self):
        observations = self.corpus.observations_by_material[ADVERSARIAL_MATERIAL]
        self.assertIn("basis", mixed_condition_flags(observations, self.corpus))

    def test_a_uniform_set_is_not_flagged(self):
        observations = self.corpus.observations_by_state["synthetic-synal-ax70-t6"]
        flags = mixed_condition_flags(observations, self.corpus)
        self.assertNotIn("product_form", flags)


class GoldenTest(unittest.TestCase):
    """Projection outputs are checked in so behaviour changes appear as diffs."""

    def setUp(self):
        self.built = build_goldens(load_corpus())

    def test_goldens_match_the_checked_in_files(self):
        for name, payload in self.built.items():
            path = GOLDEN_DIR / f"{name}.json"
            with self.subTest(golden=name):
                self.assertTrue(
                    path.exists(),
                    f"missing golden {name}; run `python3 scripts/schema_lab.py goldens`",
                )
                stored = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(
                    json.dumps(payload, sort_keys=True),
                    json.dumps(stored, sort_keys=True),
                    f"{name} changed; review the diff before regenerating",
                )

    def test_goldens_are_deterministic(self):
        again = build_goldens(load_corpus())
        self.assertEqual(
            json.dumps(again, sort_keys=True),
            json.dumps(self.built, sort_keys=True),
        )

    def test_no_stray_golden_files(self):
        stored = {path.stem for path in GOLDEN_DIR.glob("*.json")}
        self.assertEqual(stored, set(self.built))


if __name__ == "__main__":
    unittest.main()
