"""Validation gate: valid data is clean, and every invalid fixture fails for its reason."""

import json
import unittest
from pathlib import Path

from schema_lab import CONTRACT_VERSION
from schema_lab import diagnostics as D
from schema_lab.negative import apply_operations, base_dataset, cases
from schema_lab.validator import (
    errors,
    jsonschema_available,
    validate,
    validate_semantics,
    validate_structure,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_PATH = REPO_ROOT / "fixtures" / "schema-lab" / "v0.1.0" / "corpus.json"


def load_corpus():
    return json.loads(CORPUS_PATH.read_text(encoding="utf-8"))


class NegativeBaseTest(unittest.TestCase):
    def test_base_is_valid(self):
        found = validate(base_dataset())
        self.assertEqual([d.as_dict() for d in errors(found)], [])

    def test_base_has_no_warnings(self):
        found = validate(base_dataset())
        self.assertEqual([d.as_dict() for d in found], [])


class NegativeCaseTest(unittest.TestCase):
    """Each fixture must fail for its intended, stable diagnostic code.

    Asserting only that a case fails would be worthless: it could fail for an
    unrelated defect introduced later, which is the regression these fixtures
    exist to catch.
    """

    def test_each_case_produces_its_intended_code(self):
        base = base_dataset()
        for case in cases():
            with self.subTest(case=case["id"]):
                patched = apply_operations(base, case["operations"])
                found = errors(validate_semantics(patched))
                codes = {item.code for item in found}
                self.assertIn(
                    case["expected_code"],
                    codes,
                    f"{case['id']} should raise {case['expected_code']}; got {sorted(codes)}",
                )

    def test_case_ids_are_unique(self):
        identifiers = [case["id"] for case in cases()]
        self.assertEqual(len(identifiers), len(set(identifiers)))

    def test_every_case_states_a_reason(self):
        for case in cases():
            with self.subTest(case=case["id"]):
                self.assertTrue(case["reason"].strip())

    def test_base_dataset_is_not_mutated_by_patching(self):
        base = base_dataset()
        snapshot = json.dumps(base, sort_keys=True)
        for case in cases():
            apply_operations(base, case["operations"])
        self.assertEqual(json.dumps(base, sort_keys=True), snapshot)


class CorpusValidationTest(unittest.TestCase):
    def setUp(self):
        self.corpus = load_corpus()

    def test_corpus_has_no_errors(self):
        found = errors(validate(self.corpus))
        self.assertEqual([d.as_dict() for d in found], [])

    def test_corpus_declares_the_supported_contract_version(self):
        self.assertEqual(self.corpus["dataset"]["contract_version"], CONTRACT_VERSION)

    def test_corpus_is_marked_synthetic(self):
        self.assertTrue(self.corpus["dataset"]["synthetic"])
        self.assertIn("Not engineering data", self.corpus["dataset"]["warning"])

    def test_expected_counts_match_the_collections(self):
        counts = self.corpus["dataset"]["expected_counts"]
        for collection, expected in counts.items():
            with self.subTest(collection=collection):
                self.assertEqual(len(self.corpus[collection]), expected)

    def test_alias_collisions_are_warnings_not_errors(self):
        found = validate_semantics(self.corpus)
        collisions = [item for item in found if item.code == D.ALIAS_COLLISION]
        self.assertTrue(collisions, "the corpus should retain deliberate near-collisions")
        for item in collisions:
            self.assertEqual(item.severity, D.WARNING)

    def test_validation_is_deterministic(self):
        first = [item.as_dict() for item in validate_semantics(self.corpus)]
        second = [item.as_dict() for item in validate_semantics(load_corpus())]
        self.assertEqual(first, second)

    def test_no_retired_condition_key_survives(self):
        for state in self.corpus["states"]:
            self.assertNotIn("material_state", state["fixed_attributes"])
        for observation in self.corpus["observations"]:
            self.assertNotIn("material_state", observation["conditions"])


class ConditionPlacementTest(unittest.TestCase):
    """Checkpoint 1's placement rule, checked against the whole corpus."""

    def setUp(self):
        self.corpus = load_corpus()
        self.conditions = {row["id"]: row for row in self.corpus["conditions"]}

    def test_states_only_fix_state_attributes(self):
        for state in self.corpus["states"]:
            for key in state["fixed_attributes"]:
                with self.subTest(state=state["id"], key=key):
                    self.assertEqual(
                        self.conditions[key]["allowed_placement"],
                        "state_fixed_attribute",
                    )

    def test_observations_only_carry_observation_conditions(self):
        for observation in self.corpus["observations"]:
            for key in observation["conditions"]:
                with self.subTest(observation=observation["id"], key=key):
                    self.assertEqual(
                        self.conditions[key]["allowed_placement"],
                        "observation_condition",
                    )

    def test_navigable_conditions_are_enumerated(self):
        navigable = [row for row in self.corpus["conditions"] if row.get("navigable")]
        self.assertTrue(navigable, "product form should be navigable")
        for condition in navigable:
            with self.subTest(condition=condition["id"]):
                self.assertEqual(condition["value_type"], "enum")
                self.assertTrue(condition["allowed_values"])

    def test_continuous_conditions_are_never_navigable(self):
        """Thickness is the line the user drew: it must not generate pages."""
        for condition in self.corpus["conditions"]:
            if condition["value_type"] in ("number", "number_interval"):
                with self.subTest(condition=condition["id"]):
                    self.assertFalse(condition.get("navigable", False))


class ProvenanceTest(unittest.TestCase):
    def setUp(self):
        self.corpus = load_corpus()

    def test_every_numeric_observation_has_a_locator_label(self):
        for observation in self.corpus["observations"]:
            if observation["result"]["kind"] in ("unavailable", "not_applicable"):
                continue
            with self.subTest(observation=observation["id"]):
                self.assertTrue(observation["source_locator"]["label"].strip())

    def test_every_numeric_result_states_its_precision(self):
        for observation in self.corpus["observations"]:
            result = observation["result"]
            if result["kind"] in ("unavailable", "not_applicable"):
                continue
            with self.subTest(observation=observation["id"]):
                self.assertIsInstance(
                    result["reported"]["significant_figures"], int
                )

    def test_reported_and_canonical_forms_both_survive(self):
        """Decision 3: canonical drives display, reported preserves precision."""
        for observation in self.corpus["observations"]:
            result = observation["result"]
            if result["kind"] in ("unavailable", "not_applicable"):
                continue
            with self.subTest(observation=observation["id"]):
                self.assertIn("reported", result)
                self.assertIn("canonical", result)


@unittest.skipUnless(
    jsonschema_available(), "jsonschema is not installed; see requirements-dev.txt"
)
class StructuralTest(unittest.TestCase):
    def test_corpus_matches_the_schema(self):
        found = validate_structure(load_corpus())
        self.assertEqual([d.as_dict() for d in found], [])

    def test_base_matches_the_schema(self):
        self.assertEqual(validate_structure(base_dataset()), [])

    def test_schema_rejects_an_unknown_top_level_key(self):
        broken = base_dataset()
        broken["unexpected"] = []
        self.assertTrue(validate_structure(broken))


if __name__ == "__main__":
    unittest.main()
