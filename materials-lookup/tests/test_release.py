"""Release gates against the factual catalog, separate from synthetic lab tests."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest
import csv
import io

from builder.build_site import load_database
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
        self.assertEqual(222, len(self.data['materials']))
        self.assertEqual(92, len(self.data['states']))
        self.assertEqual(1593, len(self.data['observations']))
        self.assertEqual(28, len(self.data['sources']))
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

    def test_aluminum_tempers_thickness_and_elongation_exemptions(self):
        rows = self.records['al-6063']['observations']
        density = next(o for o in rows if o['property_id'] == 'density')
        self.assertIsNone(density['state_id'])
        t6 = [o for o in rows if o['state_id'] == 'al-6063-t6']
        strength = next(o for o in t6 if o['property_id'] == 'tensile_yield_strength')
        self.assertEqual('lower_bound', strength['result']['kind'])
        self.assertEqual(170e6, strength['result']['canonical']['value'])
        self.assertEqual({'minimum': None, 'maximum': .124 * .0254}, strength['conditions']['thickness_m'])
        elongation = next(o for o in t6 if o['property_id'] == 'elongation_at_break')
        self.assertEqual(.062 * .0254, elongation['conditions']['thickness_m']['minimum'])
        self.assertIn('standard specimen', elongation['notes'])
        conductivity = next(o for o in t6 if o['property_id'] == 'thermal_conductivity')
        self.assertEqual(298.15, conductivity['conditions']['temperature_K'])
        self.assertEqual(201, conductivity['result']['canonical']['value'])
        # The conflicting second T6 thickness row is not silently imported.
        self.assertEqual(4, len(t6))
        annealed = next(o for o in self.records['al-1100']['observations']
                        if o['state_id'] == 'al-1100-o' and o['property_id'] == 'ultimate_tensile_strength')
        self.assertEqual('interval', annealed['result']['kind'])
        self.assertEqual({'minimum': 75e6, 'maximum': 105e6, 'unit': 'Pa'}, annealed['result']['canonical'])
        self.assertFalse(any(o['property_id'] == 'elongation_at_break' for o in self.records['al-1350']['observations']))

    def test_copper_physical_units_intervals_and_missing_cells(self):
        copper = self.records['cu-c11000']['observations']
        density = next(o for o in copper if o['property_id'] == 'density')
        self.assertEqual('interval', density['result']['kind'])
        self.assertAlmostEqual(.321 * 27679.904710203122, density['result']['canonical']['minimum'])
        self.assertAlmostEqual(.323 * 27679.904710203122, density['result']['canonical']['maximum'])
        heat = next(o for o in copper if o['property_id'] == 'specific_heat')
        self.assertAlmostEqual(385.1856, heat['result']['canonical']['value'])
        self.assertTrue(all(o['state_id'] is None and o['conditions']['temperature_K'] == 293.15 for o in copper))
        self.assertTrue(all(o['basis'] == 'reference' for o in copper))
        thermal = next(o for o in self.records['cu-c17200']['observations'] if o['property_id'] == 'thermal_conductivity')
        self.assertAlmostEqual(62 * 1.730734666295328, thermal['result']['canonical']['minimum'])
        self.assertAlmostEqual(75 * 1.730734666295328, thermal['result']['canonical']['maximum'])
        self.assertFalse(any(o['property_id'] == 'thermal_conductivity' for o in self.records['cu-c18200']['observations']))
        self.assertFalse(any(o['property_id'] == 'specific_heat' for o in self.records['cu-c38500']['observations']))
        self.assertEqual('supplier_catalog', next(s for s in self.data['sources'] if s['id'] == 'copper-alloys-guide')['source_type'])

    def test_titanium_retains_temperature_state_and_size_scope(self):
        ti64 = self.records['ti-6al-4v']['observations']
        thermal = [o for o in ti64 if o['property_id'] == 'thermal_conductivity']
        self.assertEqual({293.15: 6.6, 588.15: 10.6, 923.15: 17.5},
                         {o['conditions']['temperature_K']: o['result']['canonical']['value'] for o in thermal})
        self.assertTrue(all(o['state_id'] == 'ti-6al-4v-mill-annealed' for o in thermal))
        modulus = next(o for o in ti64 if o['property_id'] == 'youngs_modulus')
        self.assertEqual({'minimum': 107e9, 'maximum': 122e9, 'unit': 'Pa'}, modulus['result']['canonical'])
        self.assertIsNone(modulus['state_id'])
        self.assertIn('texture', modulus['notes'])
        ti6246 = self.records['ti-6al-2sn-4zr-6mo']['observations']
        heat = next(o for o in ti6246 if o['property_id'] == 'specific_heat')
        self.assertNotIn('temperature_K', heat['conditions'])
        sta = next(o for o in ti6246 if o['property_id'] == 'tensile_yield_strength' and o['state_id'] == 'ti-6246-sta')
        self.assertEqual(1103e6, sta['result']['canonical']['value'])
        self.assertEqual('lower_bound', sta['result']['kind'])
        self.assertIn('≤2.50 in', sta['notes'])
        self.assertIn('water quench or air cool', sta['notes'])

    def test_one_sided_condition_intervals_require_explicit_opt_in(self):
        data = deepcopy(self.data)
        registry = next(c for c in data['conditions'] if c['id'] == 'thickness_m')
        registry['nullable_bounds'] = False
        self.assertTrue(any(d.code == 'CONDITION_VALUE_INVALID' for d in validate(data)))
        registry['nullable_bounds'] = True
        row = next(o for o in data['observations'] if 'thickness_m' in o['conditions'])
        for bounds in [{'minimum': None, 'maximum': None}, {'minimum': .02, 'maximum': .01},
                       {'minimum': 'unknown', 'maximum': .01}]:
            row['conditions']['thickness_m'] = bounds
            self.assertTrue(any(d.severity == 'error' for d in validate(data)), bounds)

    def test_release_rejects_a_changed_canonical_value_without_a_matching_literal(self):
        db = deepcopy(self.database)
        next(m for m in db.materials if m['observations'])['observations'][0]['value'] *= 1.01
        with self.assertRaisesRegex(ValueError, 'Reported/SI mismatch'): adapt(db)

    def test_steel_taxonomy_includes_stainless_without_false_grade_equivalences(self):
        parents = {t['id']: t['primary_parent_id'] for t in self.data['taxa']}
        for family in ('stainless-steels', 'carbon-steels', 'alloy-steels', 'tool-steels'):
            self.assertEqual('steels', parents[family])
        self.assertEqual('alloy-steels', parents['case-hardening-steels'])
        m1020 = self.records['steel-atlas-m1020']['material']
        self.assertNotIn('1020', m1020['aliases'])
        self.assertNotIn('4340', self.records['steel-atlas-6582']['material']['aliases'])
        self.assertEqual([{'system_id':'as', 'value':'M1020'}, {'system_id':'supplier', 'value':'Atlas M1020'}], m1020['designations'])

    def test_steel_reference_minima_are_not_points_or_guaranteed_supply_limits(self):
        carbon = self.records['steel-atlas-1045']
        values = [o for o in carbon['observations'] if o['property_id'] == 'tensile_yield_strength']
        self.assertEqual([540e6, 510e6, 500e6], [o['result']['canonical']['value'] for o in values])
        self.assertTrue(all(o['result']['kind'] == 'lower_bound' and o['basis'] == 'typical' for o in values))
        self.assertIsNone(carbon['summaries']['tensile_yield_strength']['range'])
        self.assertIn('not guaranteed', values[0]['notes'])
        self.assertIn('≤16 mm', values[0]['notes'])
        self.assertNotIn('temperature_K', values[0]['conditions'])
        self.assertEqual({'work_condition':'cold_drawn'}, carbon['states'][0]['fixed_attributes'])
        supplied = self.records['steel-atlas-4140']['observations']
        yield_row = next(o for o in supplied if o['property_id'] == 'tensile_yield_strength')
        self.assertEqual(('lower_bound', 'minimum', 740e6),
                         (yield_row['result']['kind'], yield_row['basis'], yield_row['result']['canonical']['value']))
        self.assertIn('≤180 mm; AS1444 condition U', yield_row['notes'])
        tensile = next(o for o in supplied if o['property_id'] == 'ultimate_tensile_strength')
        self.assertEqual({'minimum':930e6, 'maximum':1080e6, 'unit':'Pa'}, tensile['result']['canonical'])
        self.assertEqual('specified_range', tensile['basis'])

    def test_case_hardened_core_properties_keep_size_and_state_scope(self):
        record = self.records['steel-atlas-8620h']
        self.assertEqual({'heat_treatment':'carburized_hardened_tempered'}, record['states'][0]['fixed_attributes'])
        tensile = [o for o in record['observations'] if o['property_id'] == 'ultimate_tensile_strength']
        self.assertEqual([980e6, 780e6, 690e6], [o['result']['canonical']['minimum'] for o in tensile])
        self.assertTrue(all(o['basis'] == 'typical' and 'core properties' in o['notes'] for o in tensile))
        self.assertIn('diameter 11 mm', tensile[0]['notes'])
        self.assertFalse(any(o['property_id'] == 'tensile_yield_strength' for o in self.records['steel-atlas-6657']['observations']))
        self.assertEqual('thermomechanically_rolled', self.records['steel-atlas-micro900']['states'][0]['fixed_attributes']['work_condition'])

    def test_tool_steel_physical_values_retain_hardness_and_temperature(self):
        arne = self.records['steel-uddeholm-arne']
        self.assertEqual('62 HRC', arne['states'][0]['fixed_attributes']['hardness_condition'])
        self.assertTrue(all(o['state_id'] is not None for o in arne['observations']))
        moduli = {o['conditions']['temperature_K']:o['result']['canonical']['value'] for o in arne['observations'] if o['property_id'] == 'youngs_modulus'}
        self.assertEqual({293.15:190e9, 473.15:185e9, 673.15:170e9}, moduli)
        self.assertEqual([2, 3, 2], [o['result']['reported']['significant_figures']
                                    for o in arne['observations'] if o['property_id'] == 'youngs_modulus'])
        for name, expected in [('orvar-supreme', 140e9), ('dievar', 145e9)]:
            high = next(o for o in self.records['steel-uddeholm-'+name]['observations'] if o['property_id'] == 'youngs_modulus' and o['conditions']['temperature_K'] == 873.15)
            self.assertEqual(expected, high['result']['canonical']['value'])
        stavax = self.records['steel-uddeholm-stavax-esr']['observations']
        self.assertFalse(any(o['property_id'] == 'tensile_yield_strength' for o in stavax))
        thermal = [o for o in stavax if o['property_id'] == 'thermal_conductivity']
        self.assertTrue(all('±15%' in o['notes'] for o in thermal))
        self.assertFalse(any(o['property_id'] == 'thermal_conductivity' and o['conditions'].get('temperature_K') == 293.15 for o in self.records['steel-uddeholm-caldie']['observations']))

    def test_tool_steel_tensile_rows_do_not_inherit_physical_specimen_conditions(self):
        dievar = self.records['steel-uddeholm-dievar']
        bystate = {s['id']:s for s in dievar['states']}
        tensile = [o for o in dievar['observations'] if o['property_id'] == 'ultimate_tensile_strength']
        self.assertEqual({'44 HRC':1480e6, '48 HRC':1640e6, '52 HRC':1900e6},
                         {bystate[o['state_id']]['fixed_attributes']['hardness_condition']:o['result']['canonical']['value'] for o in tensile})
        self.assertTrue(all(o['conditions']['orientation'] == 'ST' and 'temperature_K' not in o['conditions'] for o in tensile))
        self.assertTrue(all('cycles are not supplied' in o['notes'] for o in tensile))
        self.assertTrue(all('615 °C' not in o['notes'] for o in tensile))
        carmo = self.records['steel-uddeholm-carmo']
        states = {s['id']:s['fixed_attributes']['hardness_condition'] for s in carmo['states']}
        for o in carmo['observations']:
            expected = '270 HB' if o['property_id'] in ('ultimate_tensile_strength','tensile_yield_strength','elongation_at_break') else '240–270 HB'
            self.assertEqual(expected, states[o['state_id']])

    def test_release_rejects_unreviewed_result_kinds(self):
        db = deepcopy(self.database)
        next(m for m in db.materials if m['observations'])['observations'][0]['result_kind'] = 'unsupported'
        with self.assertRaisesRegex(ValueError, 'Unreviewed result kind'): adapt(db)

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
        from builder.prepare_source_review import prepare
        with self.assertRaisesRegex(ValueError, 'outside the repository'):
            prepare(ROOT, ROOT / 'private-sources')


if __name__ == '__main__': unittest.main()
