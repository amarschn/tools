import copy
import json
import tempfile
import unittest
from pathlib import Path

from builder import build_site


def observation(property_id, value, unit, *, basis="typical"):
    return {
        "property": property_id,
        "value": value,
        "unit": unit,
        "uncertainty": {"kind": "implied", "sigfigs": 3},
        "basis": basis,
        "conditions": {
            "temperature_K": 293.15,
            "product_form": "sheet",
        },
        "test_method": "ASTM demo",
        "source_id": "fixture-source",
        "source_locator": f"Table 1, {property_id}",
    }


def fixture_documents():
    properties = {
        "schema_version": "0.1.0",
        "thesaurus": {"strength": "yield_strength"},
        "properties": [
            {
                "id": "yield_strength",
                "name": "Yield strength",
                "aliases": ["yield", "proof stress"],
                "quantity_kind": "pressure",
                "canonical_unit": "Pa",
                "symbol": "σy",
                "description": "Stress at permanent deformation.",
                "display_precision": 3,
                "typical_scale": 1_000_000,
            },
            {
                "id": "density",
                "name": "Density",
                "aliases": ["mass density"],
                "quantity_kind": "density",
                "canonical_unit": "kg/m^3",
                "symbol": "ρ",
                "description": "Mass per unit volume.",
                "display_precision": 4,
                "typical_scale": 1,
            },
        ],
    }
    conditions = {
        "schema_version": "0.1.0",
        "conditions": [
            {
                "id": "temperature_K",
                "name": "Temperature",
                "value_type": "number",
                "unit": "K",
                "allowed_values": None,
            },
            {
                "id": "product_form",
                "name": "Product form",
                "value_type": "enum",
                "unit": None,
                "allowed_values": ["sheet", "bar"],
            },
        ],
    }
    sources = {
        "schema_version": "0.1.0",
        "sources": [
            {
                "id": "fixture-source",
                "title": "Fixture handbook",
                "organization": "Fixture laboratory",
                "source_type": "government_handbook",
                "publication_date": "2020-06",
                "revision": "A",
                "license": "Public domain",
                "url": "https://example.test/fixture.pdf",
                "retrieved_date": "2026-07-29",
                "notes": "Test fixture.",
            }
        ],
    }
    materials = {
        "schema_version": "0.1.0",
        "thesaurus": {"aircraft alloy": "al-demo-t6"},
        "materials": [
            {
                "id": "metals",
                "name": "Metals",
                "record_type": "family",
                "parent_id": None,
                "aliases": ["metal"],
                "family": ["metal"],
                "designations": {},
                "condition": None,
                "prominence": 5,
                "description": "Top-level metal family.",
                "observations": [],
            },
            {
                "id": "aluminium-alloys",
                "name": "Aluminium alloys",
                "record_type": "family",
                "parent_id": "metals",
                "aliases": ["aluminum"],
                "family": ["metal", "aluminium"],
                "designations": {},
                "condition": None,
                "prominence": 5,
                "description": "Nested aluminium family.",
                "observations": [],
            },
            {
                "id": "al-demo",
                "name": "Aluminium demo grade",
                "record_type": "grade",
                "parent_id": "aluminium-alloys",
                "aliases": ["demo grade"],
                "family": ["metal", "aluminium"],
                "designations": {"AA": "DEMO"},
                "condition": None,
                "prominence": 4,
                "description": "A grade with observations stored on variants.",
                "observations": [],
            },
            {
                "id": "al-demo-t4",
                "name": "Aluminium demo T4",
                "record_type": "variant",
                "parent_id": "al-demo",
                "aliases": ["demo T4"],
                "family": ["metal", "aluminium"],
                "designations": {"AA": "DEMO-T4"},
                "condition": "T4",
                "prominence": 3,
                "description": "Lower-strength fixture variant.",
                "observations": [
                    observation("yield_strength", 200_000_000, "Pa", basis="minimum"),
                    observation("density", 2700, "kg/m^3"),
                ],
            },
            {
                "id": "al-demo-t6",
                "name": "Aluminium demo T6",
                "record_type": "variant",
                "parent_id": "al-demo",
                "aliases": ["demo T6", "aircraft demo"],
                "family": ["metal", "aluminium"],
                "designations": {"AA": "DEMO-T6"},
                "condition": "T6",
                "prominence": 5,
                "description": "Higher-strength fixture variant.",
                "observations": [
                    observation("yield_strength", 300_000_000, "Pa"),
                    observation("density", 2800, "kg/m^3"),
                ],
            },
        ],
    }
    return materials, properties, conditions, sources


class BuildSiteTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.documents = fixture_documents()
        self.write_documents(*self.documents)

    def tearDown(self):
        self.temporary.cleanup()

    def write_json(self, relative_path, document):
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(document, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def write_documents(self, materials, properties, conditions, sources):
        self.write_json("curated/materials.json", materials)
        self.write_json("registry/properties.json", properties)
        self.write_json("registry/conditions.json", conditions)
        self.write_json("curated/sources.json", sources)

    def test_builds_parallel_index_records_and_sorted_pages(self):
        output = self.root / "public" / "materials"
        counts = build_site.build(self.root, output)

        self.assertEqual(counts, (5, 2))
        index = json.loads((output / "search-index.json").read_text())
        self.assertEqual(
            index["fields"],
            [
                "id",
                "name",
                "record_type",
                "parent_id",
                "family",
                "aliases",
                "prominence",
                "href",
                "description",
                "headline",
            ],
        )
        self.assertTrue(all(len(row) == len(index["fields"]) for row in index["rows"]))
        self.assertEqual(index["token_list"], sorted(index["tokens"]))
        id_position = index["fields"].index("id")
        t6_row = next(
            row_number
            for row_number, row in enumerate(index["rows"])
            if row[id_position] == "al-demo-t6"
        )
        self.assertIn(t6_row, index["tokens"]["aircraft"])
        self.assertEqual(index["thesaurus"]["strength"], "yield_strength")
        self.assertEqual(index["thesaurus"]["aircraft alloy"], "al-demo-t6")
        self.assertEqual(index["thesaurus"]["proof stress"], "yield_strength")

        record = json.loads((output / "records/al-demo.json").read_text())
        self.assertEqual(record["children"], ["al-demo-t4", "al-demo-t6"])
        yield_envelope = next(
            item
            for item in record["derived_envelopes"]
            if item["property"] == "yield_strength"
        )
        self.assertEqual(yield_envelope["min"], 200_000_000)
        self.assertEqual(yield_envelope["max"], 300_000_000)
        self.assertEqual(yield_envelope["variant_count"], 2)
        family_record = json.loads((output / "records/metals.json").read_text())
        self.assertEqual(
            next(
                item
                for item in family_record["derived_envelopes"]
                if item["property"] == "yield_strength"
            )["variant_count"],
            2,
        )
        variant = json.loads((output / "records/al-demo-t6.json").read_text())
        self.assertIn("fixture-source", variant["source_details"])
        self.assertTrue((output / "al-demo-t6/index.html").is_file())
        self.assertTrue((output / "index.html").is_file())
        self.assertIn(
            "Derived descendant envelopes",
            (output / "al-demo/index.html").read_text(),
        )
        self.assertIn(
            "Public domain",
            (output / "sources/index.html").read_text(),
        )

        grade_row = next(
            row for row in index["rows"] if row[id_position] == "al-demo"
        )
        headline_position = index["fields"].index("headline")
        self.assertEqual(
            grade_row[headline_position][0]["basis"], "descendant-envelope"
        )
        self.assertIn("min", grade_row[headline_position][0]["value"])

        property_page = (
            output / "by" / "yield-strength" / "index.html"
        ).read_text()
        self.assertLess(
            property_page.index("Aluminium demo T6"),
            property_page.index("Aluminium demo T4"),
        )

    def test_accepts_bare_arrays_and_id_keyed_maps(self):
        materials, properties, conditions, sources = copy.deepcopy(self.documents)
        bare_materials = materials["materials"]
        property_map = {
            item.pop("id"): item for item in properties["properties"]
        }
        condition_map = {
            item.pop("id"): item for item in conditions["conditions"]
        }
        source_map = {item.pop("id"): item for item in sources["sources"]}
        self.write_documents(
            bare_materials,
            property_map,
            condition_map,
            source_map,
        )

        database = build_site.load_database(self.root)
        self.assertEqual(len(database.materials), 5)
        self.assertEqual(set(database.property_by_id), {"yield_strength", "density"})
        self.assertEqual(
            set(database.condition_by_key), {"temperature_K", "product_form"}
        )
        self.assertEqual(set(database.source_by_id), {"fixture-source"})

    def test_reports_registry_hierarchy_unit_basis_and_citation_errors(self):
        materials, properties, conditions, sources = copy.deepcopy(self.documents)
        bad_observation = materials["materials"][-1]["observations"][0]
        bad_observation.update(
            {
                "property": "mystery_property",
                "unit": "MPa",
                "basis": "average",
                "conditions": {"made_up_condition": "ambient"},
                "source_id": "missing-source",
                "source_locator": "",
            }
        )
        materials["materials"][2]["observations"] = [
            observation("density", 2700, "kg/m^3")
        ]
        materials["materials"][-1]["parent_id"] = "metals"
        self.write_documents(materials, properties, conditions, sources)

        with self.assertRaises(build_site.ValidationError) as raised:
            build_site.load_database(self.root)
        message = "\n".join(raised.exception.errors)
        self.assertIn("unknown registered property", message)
        self.assertIn("not a coherent SI unit", message)
        self.assertIn(".basis:", message)
        self.assertIn("unknown registered condition key", message)
        self.assertIn("unknown source id", message)
        self.assertIn(".source_locator:", message)
        self.assertIn("grade records must be structural", message)
        self.assertIn("variant parent must be a grade", message)

    def test_wrong_json_types_are_reported_without_tracebacks(self):
        materials, properties, conditions, sources = copy.deepcopy(self.documents)
        materials["materials"][0]["aliases"] = None
        materials["materials"][2]["parent_id"] = []
        bad_observation = materials["materials"][-1]["observations"][0]
        bad_observation["property"] = []
        bad_observation["basis"] = []
        bad_observation["source_id"] = []
        self.write_documents(materials, properties, conditions, sources)

        with self.assertRaises(build_site.ValidationError) as raised:
            build_site.load_database(self.root)
        message = "\n".join(raised.exception.errors)
        self.assertIn("must be an array of strings", message)
        self.assertIn("must be null or a material id", message)
        self.assertIn("unknown registered property", message)
        self.assertIn(".basis:", message)
        self.assertIn("unknown source id", message)

    def test_detects_family_cycle(self):
        materials, properties, conditions, sources = copy.deepcopy(self.documents)
        materials["materials"][0]["parent_id"] = "aluminium-alloys"
        self.write_documents(materials, properties, conditions, sources)

        with self.assertRaises(build_site.ValidationError) as raised:
            build_site.load_database(self.root)
        self.assertTrue(
            any("cycle detected" in error for error in raised.exception.errors)
        )

    def test_manifest_removes_only_stale_generated_files(self):
        output = self.root / "materials"
        build_site.build(self.root, output)
        unrelated = output / "notes.txt"
        unrelated.write_text("keep me", encoding="utf-8")

        materials, properties, conditions, sources = copy.deepcopy(self.documents)
        materials["materials"] = [
            item for item in materials["materials"] if item["id"] != "al-demo-t4"
        ]
        self.write_documents(materials, properties, conditions, sources)
        build_site.build(self.root, output)

        self.assertFalse((output / "records/al-demo-t4.json").exists())
        self.assertFalse((output / "al-demo-t4/index.html").exists())
        self.assertEqual(unrelated.read_text(encoding="utf-8"), "keep me")

    def test_refuses_untracked_collision_before_writing(self):
        output = self.root / "materials"
        output.mkdir()
        collision = output / "index.html"
        collision.write_text("hand-authored", encoding="utf-8")

        with self.assertRaisesRegex(
            build_site.BuildError, "refusing to overwrite untracked"
        ):
            build_site.build(self.root, output)
        self.assertEqual(collision.read_text(encoding="utf-8"), "hand-authored")
        self.assertFalse((output / "search-index.json").exists())

    def test_refuses_nested_output_symlink(self):
        output = self.root / "materials"
        outside = self.root / "outside"
        output.mkdir()
        outside.mkdir()
        (output / "records").symlink_to(outside, target_is_directory=True)

        with self.assertRaisesRegex(build_site.BuildError, "output symlink"):
            build_site.build(self.root, output)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertFalse((output / "search-index.json").exists())

    def test_refuses_output_that_overlaps_sources(self):
        with self.assertRaisesRegex(build_site.BuildError, "must not overlap"):
            build_site.build(self.root, self.root / "curated" / "generated")

    def test_uses_frontend_sources_and_resolves_template_tokens(self):
        src = self.root / "src"
        src.mkdir()
        (src / "index.html").write_text(
            "<!doctype html><title>Fixture search</title>", encoding="utf-8"
        )
        (src / "styles.css").write_text(
            "body { color: black; }\n", encoding="utf-8"
        )
        template = (
            "<!doctype html><html><head><title>{{TITLE}}</title>"
            '<meta name="description" content="{{DESCRIPTION}}">{{STYLE}}'
            "</head><body>{{CONTENT}}</body></html>"
        )
        (src / "detail_template.html").write_text(template, encoding="utf-8")
        (src / "property_template.html").write_text(template, encoding="utf-8")
        output = self.root / "materials"

        build_site.build(self.root, output)

        self.assertEqual(
            (output / "index.html").read_text(),
            "<!doctype html><title>Fixture search</title>",
        )
        self.assertEqual(
            (output / "assets/styles.css").read_text(),
            "body { color: black; }\n",
        )
        detail = (output / "al-demo-t6/index.html").read_text()
        prop = (output / "by/yield-strength/index.html").read_text()
        credits = (output / "sources/index.html").read_text()
        for rendered in (detail, prop, credits):
            self.assertNotIn("{{", rendered)
            self.assertIn("/materials/assets/styles.css", rendered)
        database = build_site.load_database(self.root)
        self.assertEqual(
            build_site.render_outputs(self.root, database),
            build_site.render_outputs(self.root, database),
        )

    def test_rejects_unsupported_schema_condition_type_and_unit_syntax(self):
        materials, properties, conditions, sources = copy.deepcopy(self.documents)
        for document in (materials, properties, conditions, sources):
            document["schema_version"] = "999.0.0"
        conditions["conditions"][0]["value_type"] = "potato"
        properties["properties"][0]["canonical_unit"] = "Pa++"
        materials["materials"][-1]["observations"][0]["unit"] = "Pa++"
        self.write_documents(materials, properties, conditions, sources)

        with self.assertRaises(build_site.ValidationError) as raised:
            build_site.load_database(self.root)
        message = "\n".join(raised.exception.errors)
        self.assertIn("unsupported version", message)
        self.assertIn("unsupported condition type", message)
        self.assertIn("not a coherent SI unit", message)

    def test_accepts_a_single_condition_record_using_id(self):
        materials, properties, conditions, sources = copy.deepcopy(self.documents)
        for material in materials["materials"]:
            for item in material["observations"]:
                item["conditions"] = {"temperature_K": 293.15}
        self.write_documents(
            materials,
            properties,
            conditions["conditions"][0],
            sources,
        )
        database = build_site.load_database(self.root)
        self.assertEqual(set(database.condition_by_key), {"temperature_K"})

    def test_check_mode_does_not_create_output(self):
        output = self.root / "materials"
        counts = build_site.build(self.root, output, check=True)
        self.assertEqual(counts, (5, 2))
        self.assertFalse(output.exists())

    def test_missing_required_input_fails_clearly(self):
        (self.root / "curated/sources.json").unlink()
        with self.assertRaisesRegex(build_site.BuildError, "required input is missing"):
            build_site.load_database(self.root)


if __name__ == "__main__":
    unittest.main()
