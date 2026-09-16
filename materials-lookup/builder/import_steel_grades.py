"""Reviewed steel tables; see docs/steel-batch-review.md for scope and caveats."""
import re

DATE = '2026-09-10'
ATLAS_URL = 'https://www.atlassteels.com.au/documents/Atlas%20Engineering%20Bar%20Handbook%20rev%20Jan%202005-Oct%202011.pdf'
TOOL_SOURCES = [['arne',
  'Arne',
  'https://www.uddeholm.com/app/uploads/sites/240/2024/05/Tech-Uddeholm-Arne-EN.pdf',
  '2019-04'],
 ['rigor',
  'Rigor',
  'https://www.uddeholm.com/app/uploads/sites/216/productdb/api/tech_uddeholm-rigor_en.pdf',
  '2019-04'],
 ['sverker-21',
  'Sverker 21',
  'https://www.uddeholm.com/app/uploads/sites/216/productdb/api/tech_uddeholm-sverker-21_en.pdf',
  '2019-04'],
 ['orvar-supreme',
  'Orvar Supreme',
  'https://www.uddeholm.com/app/uploads/sites/247/2024/09/Tech-Uddeholm-Orvar-Supreme-EN.pdf',
  '2021-06'],
 ['stavax-esr',
  'Stavax ESR',
  'https://www.uddeholm.com/app/uploads/sites/216/productdb/api/tech_uddeholm-stavax-esr_en.pdf',
  '2026-05'],
 ['carmo',
  'Carmo',
  'https://www.uddeholm.com/app/uploads/sites/230/2024/05/Tech-Uddeholm-Carmo.pdf',
  '2019-10'],
 ['caldie',
  'Caldie',
  'https://www.uddeholm.com/app/uploads/sites/216/productdb/api/tech_uddeholm-caldie_en.pdf',
  '2022-03'],
 ['dievar',
  'Dievar',
  'https://www.uddeholm.com/app/uploads/sites/216/productdb/api/tech_uddeholm-dievar_en.pdf',
  '2026-09']]
DOCUMENTS = [
    ('atlas-engineering-bar', 'Technical Handbook of Bar Products', 'Atlas Specialty Metals',
     ATLAS_URL, 'Selected sections 4.1–4.13. Carbon/free-machining and case-hardened core values are typical references, not guaranteed supply minima. Through-hardening and Micro900 supply limits are separately identified. Diameter, gauge-length and heat-treatment qualifications retained. Printed January 2005, edition 1; URL filename also mentions October 2011.', '2005-01'),
] + [
    ('uddeholm-' + key, 'Uddeholm ' + name + ' technical brochure', 'Uddeholm', url,
     'Selected metric physical-property tables and tabulated tensile properties. Heat treatment, hardness, specimen scope and temperatures retained. No compressive strengths substituted for tensile yield; chart-derived values excluded.',
     published) for key, name, url, published in TOOL_SOURCES
]
SOURCE_TYPES = {'atlas-engineering-bar': 'supplier_catalog'}

# Reviewed named-state mappings. Hardness remains the source's named condition,
# not a newly inferred numeric hardness property or conversion between scales.
STATE_ATTRIBUTES = {
    'cold drawn': {'work_condition': 'cold_drawn'},
    'hardened and tempered': {'heat_treatment': 'hardened_tempered'},
    'carburized, hardened and tempered': {'heat_treatment': 'carburized_hardened_tempered'},
    'thermomechanically rolled': {'work_condition': 'thermomechanically_rolled'},
}
HARDNESS_CONDITIONS = ['62 HRC', '50 HRC', '45 ± 1 HRC', '60–61 HRC',
                       '44–46 HRC', '44 HRC', '48 HRC', '52 HRC', '45 HRC',
                       '240–270 HB', '270 HB']
for hardness in HARDNESS_CONDITIONS:
    STATE_ATTRIBUTES['hardened and tempered (' + hardness + ')'] = {
        'heat_treatment': 'hardened_tempered', 'hardness_condition': hardness}

# Carbon rows: only the explicitly cold-drawn supply form. The source labels
# these numbers "min" but explicitly disclaims guaranteed mechanical values.
# Grade, PDF page, section, largest diameter, UTS / yield / A50 vectors.
CARBON = [
    ('M1020', 31, '4.1.4', 100, '480 460 430', '380 370 340', '12 12 13'),
    ('M1030', 33, '4.2.4', 100, '560 540 520', '440 430 410', '10 11 12'),
    ('1045', 35, '4.3.4', 80, '690 650 640', '540 510 500', '8 8 9'),
    ('1214FM', 38, '4.4.4', 100, '480 430 400', '350 330 290', '7 8 9'),
    ('12L14FM', 40, '4.5.4', 100, '480 430 400', '350 330 290', '7 8 9'),
]
# Grade, PDF page, section, designations, diameter / UTS / Rp0.2 / elongation.
THROUGH = [
    ('4140', 42, '4.6.4', {'AS': '4140'}, [
        ('≤180 mm; AS1444 condition U', '930–1080', '740', '12'),
        ('>180 to ≤250 mm; AS1444 condition T', '850–1000', '665', '13'),
        ('>250 to ≤450 mm; AS1444 condition T', '850–1000', '665', '13')]),
    ('6582', 45, '4.7.4', {'EN': '34CrNiMo6', 'DIN': '1.6582'}, [
        ('≤40 mm', '1100–1300', '900', '10'),
        ('>40 to ≤100 mm', '1000–1200', '800', '11'),
        ('>100 to ≤160 mm', '900–1100', '700', '12'),
        ('>160 to ≤250 mm', '800–950', '600', '13'),
        ('>250 to ≤500 mm', '750–900', '540', '14')]),
    ('4340', 48, '4.8.4', {'AS': '4340'}, [
        ('≤60 mm', '1000–1150', '835', '12'),
        ('>60 to ≤100 mm', '930–1080', '740', '12'),
        ('>100 to ≤178 mm', '930–1080', '720', '14'),
        ('>178 to ≤240 mm', '900–1000', '690', '14')]),
    ('6580', 51, '4.9.4', {'EN': '30CrNiMo8', 'DIN': '1.6580'}, [
        ('≤40 mm', '1300–1450', '1100', '9'),
        ('>40 to ≤100 mm', '1200–1300', '1020', '10'),
        ('>100 to ≤160 mm', '1100–1200', '925', '11'),
        ('>160 to ≤250 mm', '1000–1100', '820', '12'),
        ('>250 to ≤500 mm', '900–1000', '700', '12')]),
]
CASE = [
    ('8620H', 55, '4.10.6', {'AS': '8620H'}, [
        ('11', '980–1270', '785', '9'), ('30', '780–1080', '590', '10'),
        ('63', '690–930', '490', '11')]),
    ('6587', 56, '4.11.6', {'EN': '18CrNiMo7-6', 'DIN': '1.6587'}, [
        ('11', '1180–1420', '835', '7'), ('30', '1080–1320', '785', '8'),
        ('63', '980–1270', '685', '8')]),
    ('6657', 59, '4.12.6', {'EN': '14NiCrMo13-4', 'DIN': '1.6657'}, [
        ('11', '1230–1480', None, '9'), ('30', '1030–1330', None, '10'),
        ('63', '880–1180', None, '11')]),
]

# Metric cells in physical-property tables. Spacing and decimal commas are
# normalized; written significant digits are preserved. '-' = unreported.
# key, PDF page, hardness, temperatures, density, modulus, conductivity, heat.
TOOLS = [
    ('arne', 3, '62 HRC', [20, 200, 400], '7800 7750 7700', '190000 185000 170000', '32 33 34', '460 - -'),
    ('rigor', 4, '62 HRC', [20, 200, 400], '7750 7700 7650', '190000 185000 170000', '26.0 27.0 28.5', '460 - -'),
    ('sverker-21', 3, '62 HRC', [20, 200, 400], '7700 7650 7600', '210000 200000 180000', '20.0 21.0 23.0', '460 - -'),
    ('orvar-supreme', 4, '45 ± 1 HRC', [20, 400, 600], '7800 7700 7600', '210000 180000 140000', '25 29 30', '- - -'),
    ('stavax-esr', 4, '50 HRC', [20, 200, 400], '7800 7750 7700', '210000 200000 185000', '16 20 24', '460 - -'),
    ('carmo', 4, '240–270 HB', [20, 200, 400], '7780 7730 7660', '204000 196000 185000', '- - -', '460 - -'),
    ('caldie', 3, '60–61 HRC', [20, 200, 400], '7820 - -', '213000 192000 180000', '- 24 28', '460 - -'),
    ('dievar', 4, '44–46 HRC', [20, 400, 600], '7800 7700 7600', '210000 180000 145000', '- 31 32', '- - -'),
]
TOOL_DESIGNATIONS = {
    'arne': {'AISI': 'O1', 'DIN': '1.2510'},
    'rigor': {'AISI': 'A2', 'DIN': '1.2363'},
    'sverker-21': {'AISI': 'D2', 'DIN': '1.2379'},
    'orvar-supreme': {'AISI': 'H13', 'NADCA': '207 Grade B'},
    'stavax-esr': {'AISI': '420 modified'},
    'carmo': {'DIN': '1.2358'},
    'caldie': {}, 'dievar': {},
}
TOOL_NOTES = {
    'orvar-supreme': 'Specimens from the centre of a 407 × 127 mm bar; hardened 30 min at 1025 °C, air quenched, tempered 2 + 2 h at 610 °C; 45 ± 1 HRC.',
    'caldie': 'Samples from the centre of 203 × 80 mm and diameter 102 mm bars; hardened at 1025 °C, vacuum gas quenched, tempered twice at 525 °C for 2 h; 60–61 HRC.',
    'dievar': 'Samples from the centre of a 610 × 203 mm bar; hardened at 1025 °C, oil quenched, tempered twice at 615 °C for 2 h; 44–46 HRC.',
}


def import_steel_grades(pages, records, *, obs, record, pair, slug):
    for rid, name, parent, aliases in [
        ('steels', 'Steels', 'metals', ['steel', 'steels']),
        ('carbon-steels', 'Carbon steels', 'steels', ['carbon steel', 'carbon steels', 'free machining steel']),
        ('alloy-steels', 'Alloy steels', 'steels', ['alloy steel', 'alloy steels']),
        ('case-hardening-steels', 'Case-hardening steels', 'alloy-steels', ['case hardening steel', 'case hardening steels']),
        ('tool-steels', 'Tool steels', 'steels', ['tool steel', 'tool steels']),
    ]:
        records.append(record(rid, name, 'family', parent, ['metal', 'steel'],
                              'Steel grades with reviewed source tables.', aliases=aliases))

    def checked(prop, raw, source, page, column, row, **kwargs):
        # Pins protect the complete table; this check also catches transcription
        # mistakes that introduce a numeric literal absent from the reviewed page.
        normalized = re.sub(r'\s+', '', pages[source][page - 1]).replace(',', '.')
        for number in raw.split('–'):
            if number not in normalized:
                raise ValueError(f'Steel source literal missing: {source}, p. {page}, {number}')
        value = obs(prop, raw, source, page, column, row, **kwargs)
        if prop == 'youngs_modulus' and source.startswith('uddeholm-'):
            # Whole MPa entries such as 210 000 do not establish six measured
            # significant figures. Keep the literal, but use the conservative
            # precision so conversion to GPa does not display 210.000.
            figures = len(raw.rstrip('0'))
            value['source_value']['significant_figures'] = figures
            value['uncertainty']['sigfigs'] = figures
        return value

    def mechanical(grade, page, section, rows, typical, *, core=False, carbon=False):
        result = []
        for diameter, tensile, yield_value, elongation in rows:
            diameter_label = diameter + ' mm' if core else diameter
            scope = ('Core of test section, diameter ' if core else 'Bar diameter ') + diameter_label
            note = scope + '. '
            if typical:
                note += 'Typical reference values; not guaranteed supply requirements. Printed minimum labels are retained as typical lower bounds. '
            if core:
                note += 'After carburizing, hardening and tempering; these are core properties, not case/surface values.'
            if carbon:
                note += 'Cold drawn. The source does not define the yield offset.'
            for prop, raw, label in [
                ('tensile_strength', tensile, 'Tensile strength'),
                ('yield_strength', yield_value, 'Yield stress' if carbon or core else '0.2% proof stress'),
                ('elongation_at_break', elongation, 'Elongation in 50 mm' if carbon or grade == '4140' else 'Elongation A%' if grade != 'Micro900' else 'Elongation %'),
            ]:
                if raw is None: continue
                interval = '–' in raw
                basis = 'typical' if typical else 'specified_range' if interval else 'minimum'
                value = checked(prop, raw, 'atlas-engineering-bar', page,
                    'Atlas ' + grade + ', ' + scope,
                    section + ', ' + label + (', printed min' if not interval else ''),
                    method='Atlas handbook section ' + section,
                    conditions={'product_form': 'bar', 'material_state': note.strip()}, basis=basis)
                if not interval: value['result_kind'] = 'lower_bound'
                result.append(value)
        return result

    def atlas_grade(grade, parent, observations, condition, designations, aliases=()):
        title = 'Steel Atlas ' + grade
        pair(records, 'steel-atlas-' + slug(grade), title, parent, ['metal', 'steel'],
            'Atlas bar reference; properties apply only to the stated supply condition and size.',
            observations, condition=condition,
            aliases=sorted(set([grade, 'Atlas ' + grade, *aliases, *designations.values()])),
            designations=dict(designations, Supplier='Atlas ' + grade))

    for grade, page, section, max_diameter, ultimate, yield_values, elongations in CARBON:
        diameters = ['≤16 mm', '>16 to ≤38 mm', f'>38 to ≤{max_diameter} mm']
        rows = list(zip(diameters, ultimate.split(), yield_values.split(), elongations.split()))
        aliases = ['12L14'] if grade == '12L14FM' else ['1214'] if grade == '1214FM' else []
        # M1020/M1030 are merchant grades, not aliases for SAE 1020/1030.
        atlas_grade(grade, 'carbon-steels', mechanical(grade, page, section, rows, True, carbon=True),
                    'cold drawn', {'AS': grade}, aliases)
    for grade, page, section, designations, rows in THROUGH:
        atlas_grade(grade, 'alloy-steels', mechanical(grade, page, section, rows, False),
                    'hardened and tempered', designations)
    for grade, page, section, designations, rows in CASE:
        atlas_grade(grade, 'case-hardening-steels', mechanical(grade, page, section, rows, True, core=True),
                    'carburized, hardened and tempered', designations)
    atlas_grade('Micro900', 'alloy-steels',
        mechanical('Micro900', 60, '4.13.4.1', [('≤150 mm', '850–1000', '600', '13')], False),
        'thermomechanically rolled', {'EN': '38MnSiVS5', 'DIN': '1.1303'})

    for key, page, hardness, temperatures, density, modulus, conductivity, heat in TOOLS:
        source = 'uddeholm-' + key
        name = next(name for sid, name, _, _ in TOOL_SOURCES if sid == key)
        mid = 'steel-' + source
        designations = dict(TOOL_DESIGNATIONS[key], Supplier='Uddeholm ' + name)
        aliases = sorted(set([name, 'Uddeholm ' + name, *designations.values()]))
        records.append(record(mid, 'Tool steel Uddeholm ' + name, 'grade', 'tool-steels',
            ['metal', 'steel', 'tool-steel'], 'Uddeholm tool steel; each property retains its hardness and heat-treatment condition.',
            aliases=aliases, designations=designations))
        states = {}

        def add(hardness_label, value):
            states.setdefault('hardened and tempered (' + hardness_label + ')', []).append(value)

        for prop, values, unit, factor in [
            ('density', density, 'kg/m³', 1),
            ('youngs_modulus', modulus, 'N/mm²' if key in ('arne', 'rigor', 'stavax-esr') else 'MPa', 1e6),
            ('thermal_conductivity', conductivity, 'W/(m·°C)', 1),
            ('specific_heat', heat, 'J/(kg·°C)', 1),
        ]:
            for temp, raw in zip(temperatures, values.split(), strict=True):
                if raw == '-': continue
                note = TOOL_NOTES.get(key, 'Hardened and tempered to ' + hardness + '.')
                if key == 'carmo': note = 'Delivery condition: prehardened to 240–270 HB.'
                if key == 'stavax-esr' and prop == 'thermal_conductivity':
                    note += ' Source footnote: measurement scatter can be as high as ±15%; no statistical distribution specified.'
                add(hardness, checked(prop, raw, source, page, 'Physical properties, ' + hardness,
                    prop + f' at {temp} °C', method='Uddeholm physical-property table',
                    conditions={'temperature_K': temp + 273.15, 'material_state': note},
                    raw_unit=unit, factor=factor, basis='reference'))

        # Room temperature is not converted to an invented numeric test temperature.
        tensile_rows = {
            'orvar-supreme': [('52 HRC', '1820', '1520', None), ('45 HRC', '1420', '1280', None)],
            'stavax-esr': [('50 HRC', '1780', None, None), ('45 HRC', '1420', None, None)],
            'carmo': [('270 HB', '870', '670', '15')],
            'dievar': [('44 HRC', '1480', '1210', '13'), ('48 HRC', '1640', '1380', '13'), ('52 HRC', '1900', '1560', '12.5')],
        }.get(key, [])
        for measured_hardness, ultimate, yield_value, elongation in tensile_rows:
            for prop, raw, label in [('tensile_strength', ultimate, 'Tensile strength Rm'),
                                    ('yield_strength', yield_value, '0.2% proof strength Rp0.2'),
                                    ('elongation_at_break', elongation, 'Elongation A5')]:
                if raw is None: continue
                conditions = {'material_state': 'Room temperature (not quantified); hardness ' + measured_hardness + '.'}
                if key == 'stavax-esr':
                    conditions.update(product_form='bar', orientation='L')
                    conditions['material_state'] += ' Samples from 25 mm diameter bar in the rolling direction; oil hardened from 1025 ±10 °C and tempered twice to the indicated hardness.'
                if key == 'dievar':
                    conditions.update(product_form='bar', orientation='ST')
                    conditions['material_state'] += ' Samples from the centre of 610 × 203 mm bar; short transverse direction. Hardness-specific tempering cycles are not supplied in this table.'
                add(measured_hardness, checked(prop, raw, source, page,
                    'Tensile properties at room temperature, ' + measured_hardness, label,
                    method='Uddeholm tabulated tensile properties',
                    conditions=conditions, basis='typical' if key == 'carmo' else 'reference'))
        for condition, values in states.items():
            state_id = mid + '-' + slug(condition)
            records.append(record(state_id, 'Uddeholm ' + name + ' — ' + condition, 'variant', mid,
                ['metal', 'steel', 'tool-steel'], 'Source-specified heat treatment and hardness.',
                condition=condition, observations=values, aliases=[name + ' ' + condition]))
