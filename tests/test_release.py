"""Release gates against the factual catalog, separate from synthetic lab tests."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest
import csv
import io

from scripts.build_site import load_database
from release.catalog import adapt, canonical_bytes
from release.compiler import compile_data, render_outputs, summary
from release.publication import public_source, verify_public_outputs
from schema_lab.projections import Corpus
from schema_lab.validator import validate

ROOT = Path(__file__).resolve().parents[1]


class ReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.database = load_database(ROOT)
        cls.data, cls.extras, cls.index, cls.records, cls.projections = compile_data(cls.database)

    def test_factual_contract_and_no_artificial_states(self):
        self.assertFalse(self.data['dataset']['synthetic'])
        self.assertEqual([], [str(d) for d in validate(self.data) if d.severity == 'error'])
        self.assertEqual(158, len(self.data['materials']))
        self.assertEqual(37, len(self.data['states']))
        self.assertEqual(1138, len(self.data['observations']))
        self.assertFalse(any(s['name'] in ('stock shape', 'supplier reference state') for s in self.data['states']))

    def test_every_authored_observation_survives_with_its_source_literal(self):
        originals = [o for m in self.database.materials for o in m['observations']]
        self.assertEqual(len(originals), len(self.data['observations']))
        for o in self.data['observations']:
            self.assertIn(o['id'], self.extras['observations'])
            self.assertGreater(o['source_locator']['page'], 0)
            self.assertTrue(o['source_locator']['label'])
            self.assertTrue(self.extras['observations'][o['id']]['source_value']['text'])

    def test_hydro_density_is_direct_grade_data_and_not_inherited_by_tempers(self):
        rows = [o for o in self.records['al-6061']['observations'] if o['property_id'] == 'density']
        self.assertEqual(1, len(rows))
        self.assertIsNone(rows[0]['state_id'])
        self.assertAlmostEqual(.098 * 27679.904710203122, rows[0]['result']['canonical']['value'])
        self.assertEqual(2, rows[0]['result']['reported']['significant_figures'])
        for o in self.records['al-6061']['observations']:
            if o['property_id'] == 'thermal_conductivity': self.assertEqual(298.15, o['conditions']['temperature_K'])

    def test_stainless_physical_table_does_not_inherit_mechanical_work_condition(self):
        rows = [o for o in self.data['observations'] if o['source_id'].startswith('outokumpu')]
        for o in rows:
            if 'Table 7' in o['source_locator']['label']: self.assertIsNone(o['state_id'])
            if 'Table 5' in o['source_locator']['label'] and o['source_id'] != 'outokumpu-therma': self.assertIsNotNone(o['state_id'])

    def test_specialty_batch_preserves_conditions_limits_and_source_footnotes(self):
        forta = self.records['stainless-forta-dx-2205']['observations']
        strength = next(o for o in forta if o['property_id'] == 'tensile_yield_strength')
        self.assertEqual('lower_bound', strength['result']['kind'])
        self.assertEqual(500e6, strength['result']['canonical']['value'])
        self.assertEqual('coil', strength['conditions']['product_form'])
        self.assertIsNotNone(strength['state_id'])
        self.assertIsNone(next(o for o in forta if o['property_id'] == 'density')['state_id'])
        edx = next(o for o in self.records['stainless-forta-edx-2304']['observations'] if o['property_id'] == 'elongation_at_break')
        self.assertIn('A5', edx['source_locator']['label'])
        self.assertIn('MDS-D35', edx['test_method']['reported_label'])
        self.assertEqual(.25, edx['result']['canonical']['value'])
        therma = self.records['stainless-therma-253-ma']['observations']
        moduli = {o['conditions']['temperature_K']:o['result']['canonical']['value'] for o in therma if o['property_id'] == 'youngs_modulus'}
        self.assertEqual({293.15:200e9,873.15:155e9,1273.15:120e9}, moduli)
        self.assertTrue(all(o['state_id'] is None for o in therma))
        self.assertFalse(any(o['property_id'] == 'max_service_temperature' for o in therma))
        hot_strength = next(o for o in therma if o['property_id'] == 'ultimate_tensile_strength' and o['conditions']['temperature_K'] == 323.15)
        self.assertEqual(630e6, hot_strength['result']['canonical']['value'])
        self.assertEqual('lower_bound', hot_strength['result']['kind'])
        nickel = self.records['nickel-ultra-alloy-825']
        self.assertEqual('nickel-alloys', nickel['material']['primary_taxon_id'])
        self.assertTrue(any(d == {'system_id':'din','value':'2.4858'} for d in nickel['material']['designations']))
        self.assertTrue(all('ISO 6208' in o['test_method']['reported_label'] for o in nickel['observations'] if o['state_id']))
        self.assertFalse(self.records['stainless-ultra-725ln']['states'])
        self.assertFalse(any(d['system_id'] == 'en' for d in self.records['stainless-ultra-317l']['material']['designations']))

    def test_specified_minimums_never_become_observed_range_endpoints(self):
        s = self.records['al-6061']['summaries']['tensile_yield_strength']
        self.assertIsNone(s['range'])
        self.assertEqual(110e6, s['limits']['lower_bound']['minimum'])
        self.assertEqual(240e6, s['limits']['lower_bound']['maximum'])
        pool = deepcopy(self.records['al-6061']['observations'])
        point = deepcopy(next(o for o in pool if o['property_id'] == 'tensile_yield_strength'))
        point['id'] = 'obs-test-point'
        point['result']['kind'] = 'point'
        point['result']['canonical']['value'] = 200e6
        s = summary(pool + [point], 'tensile_yield_strength', Corpus(self.data))
        self.assertEqual(200e6, s['range']['minimum'])
        self.assertEqual(200e6, s['range']['maximum'])

    def test_release_rejects_a_changed_canonical_value_without_a_matching_literal(self):
        db = deepcopy(self.database)
        next(m for m in db.materials if m['observations'])['observations'][0]['value'] *= 1.01
        with self.assertRaisesRegex(ValueError, 'Reported/SI mismatch'): adapt(db)

    def test_release_cannot_silently_drop_unmapped_uncertainty(self):
        db = deepcopy(self.database)
        next(m for m in db.materials if m['observations'])['observations'][0]['uncertainty'] = {'kind':'stddev','sd':1}
        with self.assertRaisesRegex(ValueError, 'Unreviewed uncertainty mapping'): adapt(db)

    def test_search_entities_have_no_values_and_every_target_resolves(self):
        for e in self.index['entities']:
            self.assertNotIn('observations', e)
            self.assertNotIn('value', e)
            route = e['route']
            if 'material' in route:
                record = self.records[route['material']]
                if 'state' in route: self.assertIn(route['state'], [s['id'] for s in record['states']])
                if 'form' in route:
                    self.assertTrue(any(o['conditions'].get('product_form') == route['form'] and o['state_id'] == route.get('state') for o in record['observations']))
            else: self.assertIn(route['category'], [t['id'] for t in self.data['taxa']])

    def test_all_projected_counts_are_derived_from_raw_canonical_observations(self):
        for pid, projection in self.projections.items():
            for mid, s in projection['materials'].items():
                expected = sum(o['material_id'] == mid and o['property_id'] == pid for o in self.data['observations'])
                self.assertEqual(expected, s['observation_count'])

    def test_release_is_reproducible_and_every_manifest_hash_matches(self):
        first = render_outputs(ROOT, self.database)
        self.assertEqual(first, render_outputs(ROOT, self.database))
        manifest = json.loads(first['release-manifest.json'])
        for path, spec in manifest['files'].items():
            self.assertEqual(spec['sha256'], hashlib.sha256(first[path]).hexdigest())
        self.assertLess(manifest['index_gzip_bytes'], 100_000)
        self.assertNotIn(b'/materials/', first['index.html'])
        self.assertNotIn(b'synthetic-corpus', first['index.html'])
        self.assertNotIn(b'{{', first['index.html'])

    def test_public_ui_and_exports_exclude_document_access_but_keep_citations(self):
        outputs = render_outputs(ROOT, self.database)
        for source in self.database.sources:
            for path, content in outputs.items():
                self.assertNotIn(source['url'].encode(), content, path)
        for source in self.extras['sources']:
            self.assertNotIn('url', source)
            self.assertTrue(source['title'])
        csv_bytes = next(value for path, value in outputs.items() if path.endswith('/observations.csv'))
        rows = list(csv.DictReader(io.StringIO(csv_bytes.decode())))
        self.assertNotIn('source_url', rows[0])
        self.assertTrue(all(r['source_id'] and r['source_title'] and r['source_locator'] for r in rows))
        self.assertEqual(len(self.data['observations']), len(rows))
        private = dict(self.database.sources[0], download_url='https://private.example/token', storage_key='secret-object')
        self.assertNotIn('download_url', public_source(private))
        self.assertNotIn('storage_key', public_source(private))

    def test_publication_gate_rejects_documents_disguised_files_and_links(self):
        for path, content in [('sheet.PDF', b'document'), ('asset.bin', b'%PDF-1.7\n'),
                              ('view.html', b'<iframe src="https://example.com/sheet.pdf">'),
                              ('data.json', self.database.sources[0]['url'].encode())]:
            with self.subTest(path=path), self.assertRaises(ValueError):
                verify_public_outputs({path:content}, self.database.sources)

    def test_private_review_cannot_be_generated_under_public_preview_root(self):
        from scripts.prepare_source_review import prepare
        with self.assertRaisesRegex(ValueError, 'outside the repository'):
            prepare(ROOT, ROOT / 'private-sources')


if __name__ == '__main__': unittest.main()
