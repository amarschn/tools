"""Migration gate: the legacy corpus survives intact and the rewrite is deterministic.

The legacy JS corpus is the M0 evidence base. These tests compare the migrated
dataset against it directly rather than against a snapshot, so a migration that
quietly drops or invents data fails here.
"""

import json
import subprocess
import unittest
from pathlib import Path

from schema_lab.adversarial import apply as apply_adversarial
from schema_lab.migrate import migrate

REPO_ROOT = Path(__file__).resolve().parent.parent
DUMP_SCRIPT = REPO_ROOT / "builder" / "dump_legacy_corpus.js"
CORPUS_PATH = REPO_ROOT / "fixtures" / "schema-lab" / "v0.1.0" / "corpus.json"

STATE_ONLY_LEGACY_KEYS = {
    "material_state",
    "formulation",
    "reinforcement",
    "fiber_mass_fraction_1",
    "layup",
}
OBSERVATION_ONLY_LEGACY_KEYS = {"product_form", "moisture_content_1"}


def node_available():
    try:
        subprocess.run(["node", "--version"], capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return False
    return True


def load_legacy():
    result = subprocess.run(
        ["node", str(DUMP_SCRIPT)], capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout)


@unittest.skipUnless(node_available(), "node is required to read the legacy corpus")
class MigrationLosslessnessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy()
        cls.migrated, cls.report = migrate(cls.legacy)

    def test_every_observation_survives(self):
        legacy_ids = {row["id"] for row in self.legacy["observations"]}
        migrated_ids = {row["id"] for row in self.migrated["observations"]}
        self.assertEqual(legacy_ids, migrated_ids)

    def test_every_material_survives(self):
        legacy_ids = {row["id"] for row in self.legacy["materials"]}
        migrated_ids = {row["id"] for row in self.migrated["materials"]}
        self.assertEqual(legacy_ids, migrated_ids)

    def test_every_taxon_survives(self):
        legacy_ids = {row["id"] for row in self.legacy["taxa"]}
        migrated_ids = {row["id"] for row in self.migrated["taxa"]}
        self.assertEqual(legacy_ids, migrated_ids)

    def test_canonical_values_are_unchanged(self):
        """Migration re-shapes records; it must not re-compute the numbers."""
        legacy = {row["id"]: row for row in self.legacy["observations"]}
        for observation in self.migrated["observations"]:
            source = legacy[observation["id"]]
            result = observation["result"]
            with self.subTest(observation=observation["id"]):
                if source["value"] is not None:
                    self.assertEqual(result["kind"], "point")
                    self.assertEqual(result["canonical"]["value"], source["value"])
                    self.assertEqual(result["canonical"]["unit"], source["unit"])
                elif source["value_min"] is not None:
                    self.assertEqual(result["kind"], "interval")
                    self.assertEqual(result["canonical"]["minimum"], source["value_min"])
                    self.assertEqual(result["canonical"]["maximum"], source["value_max"])

    def test_stripped_state_attributes_were_genuine_duplicates(self):
        """Nothing is dropped unless the named state already carries it.

        This is the load-bearing losslessness claim: 228 condition entries were
        removed from observations, and every one must have been an exact copy of
        its state's fixed value rather than a distinct fact.
        """
        legacy_states = {row["id"]: row for row in self.legacy["states"]}
        migrated_states = {row["id"]: row for row in self.migrated["states"]}

        for observation in self.legacy["observations"]:
            state_id = observation.get("state_id")
            if not state_id:
                continue
            legacy_fixed = legacy_states[state_id].get("fixed_conditions") or {}
            for key, value in (observation.get("conditions") or {}).items():
                if key not in STATE_ONLY_LEGACY_KEYS:
                    continue
                with self.subTest(observation=observation["id"], key=key):
                    self.assertIn(
                        key,
                        legacy_fixed,
                        "a state-only key on an observation must be fixed by its state",
                    )
                    self.assertEqual(
                        legacy_fixed[key],
                        value,
                        "a stripped duplicate must not have disagreed with its state",
                    )
                    if key == "material_state":
                        continue
                    migrated_state = migrated_states.get(state_id)
                    self.assertIsNotNone(migrated_state)
                    self.assertIn(key, migrated_state["fixed_attributes"])

    def test_observation_context_fixed_on_states_moved_down(self):
        """Product form and moisture move to observations, never vanish."""
        legacy_states = {row["id"]: row for row in self.legacy["states"]}
        migrated = {row["id"]: row for row in self.migrated["observations"]}

        for observation in self.legacy["observations"]:
            state_id = observation.get("state_id")
            if not state_id:
                continue
            fixed = legacy_states[state_id].get("fixed_conditions") or {}
            for key in OBSERVATION_ONLY_LEGACY_KEYS & set(fixed):
                with self.subTest(observation=observation["id"], key=key):
                    self.assertEqual(
                        migrated[observation["id"]]["conditions"].get(key),
                        fixed[key],
                    )

    def test_dissolved_states_keep_their_observations(self):
        """A dissolved state's data attaches to the material, it is not deleted."""
        migrated_state_ids = {row["id"] for row in self.migrated["states"]}
        dissolved = {
            row["id"] for row in self.legacy["states"]
        } - migrated_state_ids
        self.assertTrue(dissolved, "the form-only states should have dissolved")

        legacy_by_id = {row["id"]: row for row in self.legacy["observations"]}
        migrated_by_id = {row["id"]: row for row in self.migrated["observations"]}
        for observation_id, legacy_observation in legacy_by_id.items():
            if legacy_observation.get("state_id") in dissolved:
                with self.subTest(observation=observation_id):
                    migrated_observation = migrated_by_id[observation_id]
                    self.assertIsNone(migrated_observation["state_id"])
                    self.assertEqual(
                        migrated_observation["material_id"],
                        legacy_observation["material_id"],
                    )
                    self.assertIn("product_form", migrated_observation["conditions"])

    def test_dissolved_states_were_defined_only_by_product_form(self):
        migrated_state_ids = {row["id"] for row in self.migrated["states"]}
        legacy_states = {row["id"]: row for row in self.legacy["states"]}
        for state_id in set(legacy_states) - migrated_state_ids:
            with self.subTest(state=state_id):
                fixed = legacy_states[state_id].get("fixed_conditions") or {}
                self.assertEqual(set(fixed), {"product_form"})

    def test_temper_is_recovered_from_labels(self):
        """The legacy corpus held temper only in a display label."""
        tempered = [
            row
            for row in self.migrated["states"]
            if "temper" in row["fixed_attributes"]
        ]
        self.assertTrue(tempered)
        for state in tempered:
            with self.subTest(state=state["id"]):
                self.assertEqual(state["fixed_attributes"]["temper"], state["name"])
                self.assertNotIn("·", state["name"])

    def test_legacy_material_state_is_fully_mapped(self):
        for state in self.migrated["states"]:
            with self.subTest(state=state["id"]):
                self.assertNotIn("material_state", state["fixed_attributes"])
        unmapped = [
            entry
            for entry in self.report.entries
            if entry["kind"] == "unmapped_legacy_state"
        ]
        self.assertEqual(unmapped, [])

    def test_conditioning_states_come_from_labels_not_moisture(self):
        """A named conditioning state must not be manufactured from a number."""
        conditioned = [
            row
            for row in self.migrated["states"]
            if "conditioning_state" in row["fixed_attributes"]
        ]
        self.assertTrue(conditioned)
        for state in conditioned:
            with self.subTest(state=state["id"]):
                self.assertNotIn("moisture_content_1", state["fixed_attributes"])

    def test_designations_carry_their_issuing_system(self):
        for material in self.migrated["materials"]:
            for designation in material["designations"]:
                with self.subTest(material=material["id"]):
                    self.assertIn("system_id", designation)
                    self.assertIn("value", designation)

    def test_every_legacy_source_is_registered(self):
        registered = {row["id"] for row in self.migrated["sources"]}
        used = {row["source_id"] for row in self.legacy["observations"]}
        self.assertEqual(used - registered, set())

    def test_the_conflicting_second_source_stays_distinct(self):
        """The disagreeing observation is a fixture, not a duplicate to merge."""
        registered = {row["id"] for row in self.migrated["sources"]}
        self.assertIn("synthetic-fixture-b", registered)

    def test_migration_is_deterministic(self):
        again, _ = migrate(self.legacy)
        self.assertEqual(
            json.dumps(again, sort_keys=True),
            json.dumps(self.migrated, sort_keys=True),
        )

    def test_report_accounts_for_every_change(self):
        counts = self.report.counts
        self.assertEqual(counts["duplicate_state_attribute_stripped"], 228)
        self.assertEqual(counts["state_dissolved"], 3)
        self.assertEqual(counts["attribute_moved_to_observations"], 13)


@unittest.skipUnless(node_available(), "node is required to read the legacy corpus")
class CheckedInCorpusTest(unittest.TestCase):
    """The checked-in fixture must be what the current code produces."""

    def test_corpus_matches_a_fresh_build(self):
        dataset, _ = migrate(load_legacy())
        dataset, _ = apply_adversarial(dataset)
        stored = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            json.dumps(dataset, sort_keys=True),
            json.dumps(stored, sort_keys=True),
            "run `python3 materials/builder/schema_lab.py migrate` to refresh the fixture",
        )


class AdversarialOverlayTest(unittest.TestCase):
    def setUp(self):
        self.corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
        self.kinds = {
            row["result"]["kind"] for row in self.corpus["observations"]
        }

    def test_every_result_kind_is_exercised(self):
        self.assertEqual(
            self.kinds,
            {"point", "interval", "lower_bound", "unavailable", "not_applicable"},
        )

    def test_a_superseded_observation_exists(self):
        superseded = [
            row for row in self.corpus["observations"] if row["status"] == "superseded"
        ]
        self.assertEqual(len(superseded), 1)

    def test_the_superseding_observation_points_at_it(self):
        superseded = next(
            row for row in self.corpus["observations"] if row["status"] == "superseded"
        )
        replacements = [
            row
            for row in self.corpus["observations"]
            if superseded["id"] in row["supersedes_observation_ids"]
        ]
        self.assertEqual(len(replacements), 1)

    def test_a_commercial_material_has_no_designation(self):
        undesignated = [
            row for row in self.corpus["materials"] if not row["designations"]
        ]
        self.assertTrue(undesignated)

    def test_a_material_has_a_supplemental_classification(self):
        supplemental = [
            row
            for row in self.corpus["materials"]
            if row.get("supplemental_taxon_ids")
        ]
        self.assertTrue(supplemental)
        for material in supplemental:
            with self.subTest(material=material["id"]):
                self.assertNotIn(
                    material["primary_taxon_id"], material["supplemental_taxon_ids"]
                )

    def test_uncertainty_is_separate_from_a_reported_interval(self):
        with_uncertainty = [
            row for row in self.corpus["observations"] if row.get("uncertainty")
        ]
        self.assertTrue(with_uncertainty)
        for observation in with_uncertainty:
            with self.subTest(observation=observation["id"]):
                self.assertEqual(observation["result"]["kind"], "point")
                self.assertNotIn("minimum", observation["uncertainty"]["reported"])

    def test_a_long_structured_locator_exists(self):
        detailed = [
            row
            for row in self.corpus["observations"]
            if row["source_locator"].get("table") and row["source_locator"].get("column")
        ]
        self.assertTrue(detailed)


if __name__ == "__main__":
    unittest.main()
