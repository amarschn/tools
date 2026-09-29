"""Reviewed nonferrous batch: selected facts from pinned supplier tables.

See docs/nonferrous-batch-review.md for scope and excluded ambiguous rows.
PDFs are development inputs kept outside the repository and public build.
"""
import re

DATE = '2026-09-10'
HYDRO_BASE = 'https://www.hydro.com/globalassets/01-products--services/extruded-profiles/americas/ena-resources/alloy-data-sheets/'
HYDRO_DOCS = [
    ('1xxx', '1xxx', 'hydro_2019_data_sheet_1xxx.pdf', '2019-02'),
    ('6005-6105', '6005/6105', 'hydro_2019_data_sheet_6005_6105.pdf', '2019-02'),
    ('6005a', '6005A', 'hydro_2019_data_sheet_6005a_revise_1.pdf', '2019-03'),
    ('6063', '6063', 'hydro_2026_data_sheet_6063-rev-062026.pdf', '2026-06'),
    ('6042', '6042', 'hydro_2019_data_sheet_6042.pdf', '2019-02'),
    ('6082', '6082', 'hydro_2019_data_sheet_6082_revise_1.pdf', '2019-03'),
    ('6101', '6101', 'hydro_2019_data_sheet_6101.pdf', '2019-02'),
    ('6262', '6262', 'hydro_2019_data_sheet_6262.pdf', '2019-02'),
]
DOCUMENTS = [
    ('hydro-' + key, 'Alloy ' + title + ' datasheet', 'Hydro', HYDRO_BASE + filename,
     'Selected standard extrusion tempers from page 2; alloy-wide density separately scoped. Mechanical limits use the printed MPa values; thickness uses the inches column. Thermal conductivity is typical at 25 °C. Elongation exemptions retained. Comparison grades, cold-finished and special tempers excluded; conflicting thickness rows deferred.', published)
    for key, title, filename, published in HYDRO_DOCS
] + [
    ('copper-alloys-guide', 'Copper and Alloys guide', 'thyssenkrupp Materials NA — Copper and Brass Sales',
     'https://ucpcdn.thyssenkrupp.com/_legacy/UCPthyssenkruppBAMXNA/assets.files/tkmna_com/products/collateral/copper-and-alloys-guide.pdf',
     'Physical Properties, printed page 74 (PDF page 76): selected density, thermal conductivity and specific heat at 68 °F. Supplier reference values, not design allowables; no mechanical temper is implied. C18200 conductivity over 68–212 °F excluded. Commercial-only names and missing cells excluded.', None),
    ('timet-6-4', 'TIMETAL 6-4, 6-4 ELI and 6-4-.1Ru datasheet', 'TIMET',
     'https://www.timet.com/documents/datasheets/alpha-and-beta-alloys/timetal-6-4.pdf',
     'Page 1 Table 2 physical values, assigned to the base Ti-6Al-4V grade only. Conductivity is explicitly mill annealed; modulus intervals depend on texture and heat treatment. ELI and Ru variants are not separate imported identities. Chart-derived strength values excluded.', None),
    ('timet-6246', 'TIMETAL 6-2-4-6 datasheet', 'TIMET',
     'https://www.timet.com/documents/datasheets/alpha-and-beta-alloys/timetal-6246.pdf',
     'Page 1 Table 2 physical values, except conductivity over a temperature interval. Table 3 minimum tensile rows for duplex annealed material ≤2.00 in and solution treated and aged material ≤2.50 in; size, temperature and heat-treatment footnotes retained. No temperature inferred for specific heat.', None),
]
SOURCE_TYPES = {'copper-alloys-guide': 'supplier_catalog'}

# Alloy, source suffix, density (lb/in³), density page.
ALUMINUM = [
    ('1060', '1xxx', '0.0975', 1), ('1100', '1xxx', '0.098', 1),
    ('1350', '1xxx', '0.0975', 1), ('6005', '6005-6105', '0.097', 1),
    ('6105', '6005-6105', '0.097', 1), ('6005A', '6005a', '0.098', 1),
    ('6063', '6063', '0.097', 1), ('6042', '6042', '0.098', 2),
    ('6082', '6082', '0.098', 1), ('6101', '6101', '0.097', 2),
    ('6262', '6262', '0.098', 1),
]

# Temper, original inch bounds, ultimate MPa, 0.2% yield MPa,
# minimum elongation %, typical conductivity W/(m K). Null = unreported.
AL_ROWS = {
    '1060': [('O', None, None, '60–95', '15', '25.0', '234'),
             ('H112', None, None, '60', '15', '25.0', None)],
    '1100': [('O', None, None, '75–105', '20', '25.0', '222'),
             ('H112', None, None, '75', '20', '25.0', None)],
    '1350': [('H111', None, None, '60', '25', None, '234')],
    '6005': [('T1', None, '.500', '170', '105', '16', '180'),
             ('T5', None, '0.124', '260', '240', '8', '188'),
             ('T5', '0.125', '1.000', '260', '240', '10', '188')],
    '6105': [('T1', None, '.500', '170', '105', '16', '176'),
             ('T5', None, '0.124', '260', '240', '8', '193'),
             ('T5', '0.125', '1.000', '260', '240', '10', '193'),
             ('T6', None, '.500', '260', '240', '8', '193')],
    '6005A': [('T1', None, '0.249', '170', '100', '15', '176'),
              ('T5', None, '0.249', '260', '215', '7', '193'),
              ('T5', '.250', '0.999', '260', '215', '9', '193'),
              ('T61', None, '0.249', '260', '240', '8', '188'),
              ('T61', '0.250', '1.000', '260', '240', '10', '188')],
    '6063': [('T1', None, '.500', '115', '60', '12', '193'),
             ('T1', '.501', '1.000', '110', '55', '12', '193'),
             ('T4', None, '.500', '130', '70', '14', '193'),
             ('T4', '.501', '1.000', '125', '60', '14', '193'),
             ('T5', None, '.500', '150', '110', '8', '209'),
             ('T5', '.501', '1.000', '145', '105', '8', '209'),
             ('T6', None, '.124', '205', '170', '8', '201')],
    '6042': [('T5', '.500', None, '290', '240', '10', '167')],
    '6082': [('T5', '0.080', '0.500', '270', '230', '8', None),
             ('T6', '0.200', '0.750', '310', '260', '6', '172'),
             ('T6', '0.751', '6.000', '310', '260', '8', '172'),
             ('T6', '6.001', '8.000', '280', '240', '6', '172')],
    '6101': [('T6', '0.125', '0.500', '200', '170', None, '218'),
             ('T63', '0.125', '1.000', '185', '150', None, '218'),
             ('T64', '0.125', '1.000', '100', '55', None, '226')],
    '6262': [('T6', None, None, '260', '240', '10', '167')],
}

# PDF page 76, selected physical columns. Row identities and headings reviewed
# visually. Retain the publisher's leading decimals and interval endpoints.
COPPER = [
    ('C10100', 'Copper', '.323', '226', '.092'),
    ('C10200', 'Copper', '.323', '226', '.092'),
    ('C11000', 'Copper', '.321–.323', '226', '.092'),
    ('C12200', 'Copper', '.323', '196', '.092'),
    ('C14300', 'Copper', '.323', '218', '.092'),
    ('C14500', 'Copper', '.323', '205', '.092'),
    ('C17200', 'Copper alloy', '.298', '62–75', '.10'),
    ('C17300', 'Copper alloy', '.298', '62–75', '.10'),
    ('C17510', 'Copper alloy', '.319', '144', None),
    ('C18000', 'Copper alloy', '.315', '125', None),
    ('C18200', 'Copper alloy', '.321', None, '.092'),
    ('C18700', 'Copper alloy', '.323', '218', '.092'),
    ('C21000', 'Brass', '.320', '135', '.09'),
    ('C22000', 'Brass', '.318', '109', '.09'),
    ('C23000', 'Brass', '.316', '92', '.09'),
    ('C26000', 'Brass', '.308', '70', '.09'),
    ('C28000', 'Brass', '.303', '71', '.09'),
    ('C33000', 'Leaded brass', '.307', '67', '.09'),
    ('C35300', 'Leaded brass', '.306', '67', '.09'),
    ('C36000', 'Leaded brass', '.307', '67', '.09'),
    ('C36500', 'Leaded brass', '.304', '71', '.09'),
    ('C38500', 'Leaded brass', '.306', '71', None),
    ('C46400', 'Tin brass', '.304', '67', '.09'),
    ('C48500', 'Tin brass', '.305', '67', '.09'),
    ('C51000', 'Phosphor bronze', '.320', '40', '.09'),
    ('C54400', 'Leaded phosphor bronze', '.321', '50', '.09'),
    ('C64200', 'Aluminum silicon bronze', '.278', '26', '.09'),
    ('C65500', 'Silicon bronze', '.308', '21', '.09'),
    ('C71500', 'Copper-nickel', '.323', '17', '.09'),
    ('C75200', 'Nickel silver', '.316', '19', '.09'),
]


def import_nonferrous_metals(pages, records, *, obs, record, pair, slug):
    for alloy, suffix, density, density_page in ALUMINUM:
        source = 'hydro-' + suffix
        if density not in pages[source][density_page - 1] or alloy not in ''.join(pages[source]):
            raise ValueError(f'Unreviewed Hydro identity/density: {alloy}')
        mid, name = 'al-' + slug(alloy), 'Aluminium ' + alloy
        family = ['metal', 'aluminium-alloy']
        description = 'Hydro extrusion reference. Alloy-wide density and selected standard temper properties.'
        aliases = [alloy, 'Al ' + alloy, 'Aluminum ' + alloy, 'AA ' + alloy]
        pair(records, mid, name, 'aluminium-alloys', family, description,
             [obs('density', density, source, density_page, 'Alloy ' + alloy,
                  'Density above chemical composition', method='Hydro alloy reference',
                  factor=27679.904710203122, raw_unit='lb/in³', basis='reference')],
             aliases=aliases, designations={'AA': alloy})
        states = {}
        for temper, low, high, ultimate, yield_value, elongation, conductivity in AL_ROWS[alloy]:
            bounds = [None if x is None else float(x) * .0254 for x in (low, high)]
            thickness = 'all thicknesses' if low is high is None else f'{low or "unbounded"} to {high or "unbounded"} in'
            label = f'{alloy}-{temper}, thickness {thickness}'
            method = 'Hydro extrusion property limits'
            if alloy in ('6005A', '6082'): method += ' (Aluminum Association)'
            observations = states.setdefault(temper, [])
            for prop, raw, column in [
                ('tensile_strength', ultimate, 'Ultimate tensile strength'),
                ('yield_strength', yield_value, 'Yield strength, 0.2% offset'),
                ('elongation_at_break', elongation, 'Elongation'),
                ('thermal_conductivity', conductivity, 'Typical thermal conductivity at 25 °C'),
            ]:
                if raw is None: continue
                conditions = {'product_form': 'extrusion'}
                note = 'Thickness follows the source inches column; cross section of the tensile specimen determines the applicable limits.'
                if low is not None or high is not None: conditions['thickness_m'] = bounds[:]
                if prop == 'thermal_conductivity':
                    conditions['temperature_K'] = 298.15
                    basis = 'typical'
                else:
                    basis = 'specified_range' if '–' in raw else 'minimum'
                if prop == 'elongation_at_break':
                    note += ' Elongation testing is not required when a standard specimen cannot be taken or thickness is below .062 in.'
                    if alloy != '6262':
                        column += ', gauge length 2 in or 4 specimen diameters'
                    # The footnote exempts thinner sections: do not project a
                    # minimum elongation onto a thickness with no requirement.
                    conditions['thickness_m'] = [max(bounds[0] or 0, .062 * .0254), bounds[1]]
                conditions['material_state'] = note
                observations.append(obs(prop, raw, source, 2, label, column,
                    method=method, conditions=conditions, basis=basis))
        for temper, observations in states.items():
            records.append(record(mid + '-' + slug(temper), name + ' — ' + temper,
                'variant', mid, family, description, condition=temper,
                aliases=[alloy + '-' + temper, alloy + ' ' + temper], observations=observations))

    for rid, name, parent, aliases in [
        ('copper-alloys', 'Copper and copper alloys', 'metals', ['copper', 'copper alloys']),
        ('brasses', 'Brasses', 'copper-alloys', ['brass']),
        ('bronzes', 'Bronzes', 'copper-alloys', ['bronze']),
        ('titanium-alloys', 'Titanium alloys', 'metals', ['titanium', 'titanium alloy']),
    ]:
        records.append(record(rid, name, 'family', parent, ['metal'],
                              'Grades with cited supplier properties.', aliases=aliases))
    copper_page = pages['copper-alloys-guide'][75]
    for code, kind, density, conductivity, heat in COPPER:
        line = next(line for line in copper_page.splitlines() if line.strip().startswith(code + ' '))
        observations = []
        for prop, raw, unit, factor, column in [
            ('density', density, 'lb/in³', 27679.904710203122, 'Density at 68 °F'),
            ('thermal_conductivity', conductivity, 'Btu/(ft·hr·°F)', 1.730734666295328, 'Thermal conductivity at 68 °F'),
            ('specific_heat', heat, 'Btu/(lb·°F)', 4186.8, 'Specific heat at 68 °F'),
        ]:
            if raw is None: continue
            if raw.replace('–', '-') not in line.replace('–', '-'):
                raise ValueError(f'Copper source literal not found: {code}/{prop}/{raw}')
            observations.append(obs(prop, raw, 'copper-alloys-guide', 76,
                code + ', Physical Properties (printed page 74)', column,
                method='Supplier physical-property reference; test method not stated',
                conditions={'temperature_K': 293.15, 'material_state': 'Supplier reference values; not design allowables. Mechanical temper not specified.'},
                factor=factor, raw_unit=unit, basis='reference'))
        parent = 'brasses' if 'brass' in kind.lower() else 'bronzes' if 'bronze' in kind.lower() else 'copper-alloys'
        pair(records, 'cu-' + code.lower(), kind + ' ' + code, parent,
             ['metal', 'copper-alloy'], 'Supplier physical properties at 20 °C; no mechanical temper specified.',
             observations, aliases=[code, 'UNS ' + code], designations={'UNS': code})

    def titanium(mid, name, source, designations, aliases, values):
        observations = []
        for prop, raw, temp, unit, factor in values:
            conditions = {} if temp is None else {'temperature_K': temp + 273.15}
            if prop == 'youngs_modulus': conditions['material_state'] = 'Depends on texture and heat treatment; Table 2.'
            observations.append(obs(prop, raw, source, 1, name,
                f'Table 2, {prop}' + (f' at {temp} °C' if temp is not None else ''),
                method='TIMET physical-property table; test method not stated',
                conditions=conditions, raw_unit=unit, factor=factor, basis='reference'))
        pair(records, mid, name, 'titanium-alloys', ['metal', 'titanium-alloy'],
             'TIMET reference with temperature-specific physical values.', observations,
             aliases=aliases, designations=designations)

    titanium('ti-6al-4v', 'Titanium Ti-6Al-4V', 'timet-6-4', {'ASTM': 'Grade 5', 'Supplier': 'TIMETAL 6-4'},
        ['Ti6Al4V', 'Ti-6Al-4V', 'Ti64', 'Grade 5 titanium', 'TIMETAL 6-4'], [
            ('density', '4.42', 22, 'g/cm³', 1000),
            ('specific_heat', '0.580', 20, 'J/(g·K)', 1000),
            ('specific_heat', '0.670', 425, 'J/(g·K)', 1000),
            ('specific_heat', '0.930', 870, 'J/(g·K)', 1000),
            ('youngs_modulus', '107–122', 20, 'GPa', 1e9),
            ('youngs_modulus', '95–111', 230, 'GPa', 1e9),
            ('poissons_ratio', '.31', 20, '1', 1),
        ])
    conductivity = [obs('thermal_conductivity', raw, 'timet-6-4', 1,
        'Ti-6Al-4V, mill annealed', f'Table 2, thermal conductivity at {temp} °C',
        method='TIMET physical-property table; test method not stated',
        conditions={'temperature_K': temp + 273.15}, basis='reference') for temp, raw in [(20, '6.6'), (315, '10.6'), (650, '17.5')]]
    records.append(record('ti-6al-4v-mill-annealed', 'Titanium Ti-6Al-4V — Mill annealed',
        'variant', 'ti-6al-4v', ['metal', 'titanium-alloy'], 'Mill annealed conductivity.',
        condition='mill annealed', aliases=['Ti6Al4V mill annealed'], observations=conductivity))
    titanium('ti-6al-2sn-4zr-6mo', 'Titanium Ti-6Al-2Sn-4Zr-6Mo', 'timet-6246',
        {'UNS': 'R56260', 'Supplier': 'TIMETAL 6-2-4-6'},
        ['Ti6246', 'Ti-6246', 'TIMETAL 6-2-4-6', 'R56260'], [
            ('density', '4.64', 22, 'g/cm³', 1000),
            ('specific_heat', '502', None, 'J/(kg·K)', 1),
            ('youngs_modulus', '70–114', 20, 'GPa', 1e9),
            ('youngs_modulus', '107', 315, 'GPa', 1e9),
            ('youngs_modulus', '100', 425, 'GPa', 1e9),
        ])
    for condition, code, size, ultimate, yield_value, cycle in [
        ('duplex annealed', 'DA', '2.00', '1103', '1034', '870–900 °C for 1 h, air cool; 540–593 °C for 8 h, air cool'),
        ('solution treated and aged', 'STA', '2.50', '1172', '1103', '870–925 °C for 2–90 min, water quench or air cool; 480–675 °C for 4–8 h'),
    ]:
        observations = [obs(prop, raw, 'timet-6246', 1,
            f'TIMETAL 6-2-4-6, {code}, rod diameter or thickness ≤{size} in',
            'Table 3, ' + column, method='Mil T-9047G (TIMET Table 3)', basis='minimum',
            conditions={'temperature_K': 293.15, 'material_state':
                f'Rod diameter or thickness ≤{size} in. Applies in any grain direction. Heat treatment: {cycle}.'})
            for prop, raw, column in [('tensile_strength', ultimate, 'UTS'),
                ('yield_strength', yield_value, '0.2% yield strength'), ('elongation_at_break', '10', 'Elongation')]]
        records.append(record('ti-6246-' + code.lower(), 'Titanium Ti-6Al-2Sn-4Zr-6Mo — ' + condition,
            'variant', 'ti-6al-2sn-4zr-6mo', ['metal', 'titanium-alloy'],
            'Size-limited minimum tensile properties.', condition=condition,
            aliases=['Ti6246 ' + code, 'TIMETAL 6-2-4-6 ' + code], observations=observations))
