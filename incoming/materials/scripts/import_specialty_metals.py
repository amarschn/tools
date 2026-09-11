"""Reviewed September 10 batch; numerical cells come from pinned PDF tables."""
import re

DATE = '2026-09-10'
DOCUMENTS = [
    ('outokumpu-forta', 'Forta Duplex range datasheet', 'Outokumpu',
     'https://www.outokumpu.com/-/media/files/products/forta/outokumpu-forta-range-datasheet.pdf',
     'Table 5: cold rolled coil limits; EDX 2304 follows MDS-D35 and reports A5 instead of A80. Table 9: grade-wide metric physical values. Generic duplex Table 11 and comparison grades excluded.', None),
    ('outokumpu-therma', 'Therma range datasheet', 'Outokumpu',
     'https://www.outokumpu.com/-/media/files/products/therma/outokumpu_therma_range_datasheet.pdf',
     'Table 14: metric physical values at the stated temperatures. Tables 5 and 7: elevated-temperature minimum Rp0.2 and Rm, Outokumpu values based on EN 10028-7. Guidance-only maximum application temperatures, creep tables and imperial duplicates excluded.', None),
    ('outokumpu-ultra', 'Ultra range datasheet', 'Outokumpu',
     'https://www.outokumpu.com/-/media/files/products/ultra/outokumpu_ultra_range_datasheet.pdf',
     'Table 13: metric physical values. Table 10: cold rolled values, with ISO 6208 and revision footnotes retained. Ultra 725LN has physical data only in this batch. Ultra 317L is not assigned the conditional plate designation EN 1.4438. Alloy 825 is a nickel alloy.', None),
]

# Identity columns checked visually against Table 1 in each document. These
# commercial grades remain distinct even when their standard numbers overlap.
THERMA = {
    'Therma 253 MA': ('1.4835', '', 'S30815'),
    'Therma 310S/4845': ('1.4845', '310S', 'S31008'),
    'Therma 304H/4948': ('1.4948', '304H', 'S30409'),
    'Therma 321H/4878': ('1.4878', '321H', ''),
    'Therma 347H': ('', '347H', 'S34709'),
    'Therma 4828': ('1.4828', '', ''),
    'Therma 309S/4833': ('1.4833', '309S', 'S30908'),
    'Therma 314/4841': ('1.4841', '314', 'S31400'),
    'Therma 4713': ('1.4713', '', ''),
    'Therma 4724': ('1.4724', '', ''),
}
ULTRA = {
    'Ultra 904L': ('1.4539', '904L', 'N08904'),
    'Ultra 254 SMO': ('1.4547', '', 'S31254'),
    'Ultra Alloy 825': ('', '', 'N08825'),
    'Ultra 317L': ('', '317L', 'S31703'),
    'Ultra 725LN': ('1.4466', '310MoLN2', 'S31050'),
    'Ultra 6XN': ('1.4529', '', 'N08926 / N08367'),
    'Ultra 654 SMO': ('1.4652', '', 'S32654'),
}


def table(text, number, following=None):
    result = re.split(r'\bTable\s+' + str(number) + r'\b', text, maxsplit=1)
    if len(result) != 2:
        raise ValueError(f'Missing Table {number}')
    return re.split(r'\bTable\s+' + str(following) + r'\b', result[1], maxsplit=1)[0] if following else result[1]


def rows(text, prefix, columns):
    result = {}
    for line in text.splitlines():
        fields = re.split(r'\s{2,}', line.strip())
        if not fields[0].startswith(prefix + ' '):
            continue
        if len(fields) != columns:
            raise ValueError(f'{prefix}: unexpected table row {fields}')
        name = re.sub(r'\s+\d\)$', '', fields[0])
        if name in result:
            raise ValueError(f'Duplicate table row {name}')
        result[name] = fields[1:]
    return result


def import_specialty_metals(pages, records, *, obs, record, pair, slug):
    records.append(record('nickel-alloys', 'Nickel alloys', 'family', 'metals',
                          ['metal', 'nickel-alloy'], 'Nickel-based alloys with manufacturer references.',
                          aliases=['nickel', 'nickel alloy']))

    def physical(name, values, source, page, number, columns, method):
        result = []
        for prop, column, temperature, label in columns:
            raw = values[column]
            if raw == '–':
                continue
            this_method = method
            if raw.endswith(' 2)'):
                if (source, name, prop) != ('outokumpu-ultra', 'Ultra 654 SMO', 'thermal_conductivity'):
                    raise ValueError(f'Unreviewed footnote {name}/{prop}')
                raw = raw[:-3]
                this_method = 'Outokumpu value (Table 13 footnote 2)'
            conditions = {} if temperature is None else {'temperature_K':temperature + 273.15}
            result.append(obs(prop, raw, source, page, name, f'Table {number}, {label}',
                method=this_method, conditions=conditions,
                factor=1e9 if prop == 'youngs_modulus' else None,
                raw_unit='GPa' if prop == 'youngs_modulus' else 'kg/dm³' if prop == 'density' else None))
        return result

    standard_physical = [('density',0,None,'Density'),
        ('youngs_modulus',1,20,'Modulus of elasticity at 20 °C'),
        ('thermal_conductivity',3,20,'Thermal conductivity at 20 °C'),
        ('specific_heat',4,20,'Thermal capacity at 20 °C')]

    forta = rows(table(pages['outokumpu-forta'][11],9,10),'Forta',10)
    mechanical = rows(table(pages['outokumpu-forta'][8],5),'Forta',8)
    if len(forta) != 7 or forta.keys() != mechanical.keys():
        raise ValueError('Forta table identities differ from reviewed batch')
    for name, cells in forta.items():
        en, astm, uns = cells[:3]
        observations = physical(name,cells[3:],'outokumpu-forta',12,9,standard_physical,'EN 10088-1')
        mech_en, mech_uns, form, strength, tensile, elong_a, elong_80 = mechanical[name]
        if (mech_en,mech_uns) != (en,uns) or not form.startswith('Cold rolled coil (C)'):
            raise ValueError(f'Forta identity/form mismatch: {name}')
        edx = name == 'Forta EDX 2304'
        for prop,raw,label in [('yield_strength',strength,'Rp0.2'),('tensile_strength',tensile,'Rm'),
                              ('elongation_at_break',elong_a if edx else elong_80,'A5, gauge length 5.65√S0' if edx else 'A80, gauge length 80 mm')]:
            observations.append(obs(prop,raw,'outokumpu-forta',9,name+', '+form,'Table 5, '+label,
                method='Outokumpu MDS-D35 (footnote 2)' if edx else 'EN 10088-2',
                conditions={'product_form':'coil','material_state':'Cold rolled coil (C); datasheet delivery condition'},
                basis='specified_range' if '–' in raw else 'minimum'))
        designations = {k:v for k,v in {'EN':en,'ASTM':astm,'UNS':uns,'Supplier':name}.items() if v != '–'}
        pair(records,slug('stainless '+name),'Stainless steel '+name,'stainless-steels',
             ['metal','steel','stainless-steel','duplex'],
             'Outokumpu duplex grade. Cold rolled coil limits and grade-wide physical values.',
             observations,condition='cold rolled coil',aliases=sorted(set([name,name.removeprefix('Forta '),*designations.values(),'duplex'])),designations=designations)

    therma = rows(table(pages['outokumpu-therma'][10],14,15),'Therma',13)
    hot = {prop: rows(table(pages['outokumpu-therma'][7],number,following),'Therma',10)
           for prop,number,following in [('yield_strength',5,6),('tensile_strength',7,None)]}
    if therma.keys() != THERMA.keys() or any(set(values) != set(list(THERMA)[:8]) for values in hot.values()):
        raise ValueError('Therma identities differ from reviewed batch')
    thermal_columns = [('density',0,20,'Density at 20 °C'),
        *[('youngs_modulus',i+1,t,f'Modulus of elasticity at {t} °C') for i,t in enumerate([20,600,1000])],
        *[('thermal_conductivity',i+7,t,f'Thermal conductivity at {t} °C') for i,t in enumerate([20,500,800])],
        ('specific_heat',10,20,'Thermal capacity at 20 °C')]
    for name,cells in therma.items():
        observations = physical(name,cells,'outokumpu-therma',11,14,thermal_columns,'Outokumpu values and European standards (Table 14)')
        for prop,values in hot.items():
            for temperature,raw in zip(range(50,451,50),values.get(name,[])):
                if raw == '–':
                    continue
                number,label = (5,'Rp0.2') if prop == 'yield_strength' else (7,'Rm')
                observations.append(obs(prop,raw,'outokumpu-therma',8,name+f', {temperature} °C',f'Table {number}, {label}',
                    method='Outokumpu values based on EN 10028-7 (footnote 1)',basis='minimum',conditions={'temperature_K':temperature+273.15}))
        designations = {k:v for k,v in zip(('EN','ASTM','UNS'),THERMA[name]) if v}
        designations['Supplier'] = name
        family = 'ferritic' if name in ('Therma 4713','Therma 4724') else 'austenitic'
        pair(records,slug('stainless '+name),'Stainless steel '+name,'stainless-steels',
             ['metal','steel','stainless-steel',family], 'Outokumpu heat-resistant grade; properties at explicitly stated temperatures.',
             observations,aliases=sorted(set([name,name.removeprefix('Therma '),*designations.values(),'heat resistant'])),designations=designations)

    ultra = rows(table(pages['outokumpu-ultra'][13],13,14),'Ultra',8)
    mechanical = rows(table(pages['outokumpu-ultra'][11],10,11),'Ultra',6)
    if ultra.keys() != ULTRA.keys() or ultra.keys() != mechanical.keys():
        raise ValueError('Ultra identities differ from reviewed batch')
    for name,cells in ultra.items():
        observations = physical(name,cells,'outokumpu-ultra',14,13,standard_physical,'EN 10088-1 (Table 13)')
        form,strength,_strength10,tensile,elong = mechanical[name]
        if not form.startswith('Cold rolled'):
            raise ValueError(f'Ultra form mismatch: {name}')
        added_mechanical = False
        for prop,raw,label in [('yield_strength',strength,'Rp0.2'),('tensile_strength',tensile,'Rm'),('elongation_at_break',elong,'A')]:
            if raw == '–':
                continue
            note = 'Cold rolled; product form not further specified in Table 10.'
            method = 'EN 10088-2'
            if name == 'Ultra Alloy 825':
                method = 'ISO 6208 (Table 10 footnote 3)'
                if raw.endswith(' 3)'): raw = raw[:-3]
            elif prop == 'elongation_at_break':
                note += ' Footnote 2: thickness < 3 mm uses A80 (80 mm); thickness ≥ 3 mm uses A (5.65√S0).'
            if name == 'Ultra 6XN':
                method = 'Outokumpu Table 10 (footnote 4: planned EN 10088-2 revision 2022/23)'
            observations.append(obs(prop,raw,'outokumpu-ultra',12,name+', '+form,'Table 10, '+label,
                method=method,conditions={'temperature_K':293.15,'material_state':note},
                basis='specified_range' if '–' in raw else 'minimum'))
            added_mechanical = True
        designations = {k:v for k,v in zip(('EN','ASTM','UNS'),ULTRA[name]) if v}
        designations['Supplier'] = name
        nickel = name == 'Ultra Alloy 825'
        if nickel: designations['DIN'] = '2.4858'
        aliases = [name,name.removeprefix('Ultra '),*designations.values()]
        if name == 'Ultra 6XN': aliases += ['N08926','N08367']
        pair(records,slug(('nickel ' if nickel else 'stainless ')+name),
             ('Nickel alloy ' if nickel else 'Stainless steel ')+name,
             'nickel-alloys' if nickel else 'stainless-steels',
             ['metal','nickel-alloy'] if nickel else ['metal','steel','stainless-steel','austenitic'],
             'Outokumpu grade. Physical values and available cold rolled limits remain separately scoped.',observations,
             condition='cold rolled' if added_mechanical else 'supplier reference state',aliases=sorted(set(aliases)),designations=designations)
