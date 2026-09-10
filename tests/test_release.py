"""Release gates against the factual catalog, separate from synthetic lab tests."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from scripts.build_site import load_database
from release.catalog import adapt, canonical_bytes
from release.compiler import compile_data, render_outputs, summary
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
        self.assertEqual(134, len(self.data['materials']))
        self.assertEqual(24, len(self.data['states']))
        self.assertEqual(840, len(self.data['observations']))
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
            if 'Table 5' in o['source_locator']['label']: self.assertIsNotNone(o['state_id'])

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


if __name__ == '__main__': unittest.main()
