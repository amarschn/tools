"""Spike: can one table of compatible rows reproduce every published property pair?

Run from anywhere: python3 spike_compatible_rows.py
See plans/2026-10-31_ashby_chart_rebuild.md.
"""
import json, gzip, sys, time, statistics
from pathlib import Path
from collections import defaultdict, Counter
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from pycalcs.material_selection import compatible_observations
d = json.loads((ROOT / 'data/materials/selection.json').read_text())
obs = d['observations']
by = defaultdict(list)
for o in obs.values(): by[o['material_id']].append(o)
def compat(a, b): return a['property_id'] != b['property_id'] and compatible_observations(a, b)
def cliques(items):
    adj = {o['id']: {p['id'] for p in items if p['id'] != o['id'] and compat(o, p)} for o in items}
    out = []
    def bk(r, p, x):
        if not p and not x: out.append(sorted(r)); return
        u = max(p | x, key=lambda n: len(adj[n] & p))
        for v in list(p - adj[u]):
            bk(r | {v}, p & adj[v], x & adj[v]); p = p - {v}; x = x | {v}
    bk(set(), set(adj), set())
    return out
t = time.time(); rows = []; per = Counter()
for mid, items in by.items():
    c = cliques(items); per[mid] = len(c)
    rows += [(mid, r) for r in c]
print('materials', len(by), 'rows', len(rows), 'build s', round(time.time() - t, 2))
print('rows per material: median', statistics.median(per.values()), 'max', max(per.values()), 'top', per.most_common(5))
print('single-row materials', sum(1 for v in per.values() if v == 1))
# Coverage: each published pair must appear in a row, and every pair in a row must be published.
rowsets = defaultdict(list)
for mid, r in rows: rowsets[mid].append(set(r))
missing = extra = 0; pairs = set()
for k, c in d['charts'].items():
    a, b = c['properties']
    if a == b: continue
    for p in c['points']:
        x, y = p['observations']; pairs.add(frozenset((x, y)))
        if not any(x in s and y in s for s in rowsets[p['material_id']]): missing += 1
for mid, r in rows:
    for i, x in enumerate(r):
        for y in r[i+1:]:
            if frozenset((x, y)) not in pairs: extra += 1
print('published pairs', len(pairs), 'missing from rows', missing, 'row pairs not published', extra)
# Compact projection size.
ids = {oid: i for i, oid in enumerate(obs)}
core = {'rows': [[r for r in map(ids.get, ro)] for _, ro in rows]}
print('rows json gzip KB', round(len(gzip.compress(json.dumps(core, separators=(',', ':')).encode())) / 1024))
props = list(d['property_registry']); srcs = list(d['sources'])
compact = [[o['material_id'], o['state_id'], props.index(o['property_id']), float(f"{o['plot_value']:.6g}"), o['result']['kind'][0], o['basis'][:3], o['conditions'].get('temperature_K')] for o in obs.values()]
mats = [[m['id'], m['name'], m['family'], m['sub_family']] for m in d['materials'].values()]
blob = json.dumps({'o': compact, 'm': mats, **core}, separators=(',', ':')).encode()
print('obs+materials+rows raw KB', len(blob) // 1024, 'gzip KB', len(gzip.compress(blob)) // 1024)
# Where does a median-per-property simplification differ from the real pairs?
for k in ['density|youngs_modulus', 'density|ultimate_tensile_strength', 'compressive_strength|density', 'density|tensile_yield_strength']:
    c = d['charts'][k]; print(k, 'points', len(c['points']), 'materials', len({p['material_id'] for p in c['points']}))
fam = Counter(d['materials'][p['material_id']]['family'] for p in d['charts']['density|tensile_yield_strength']['points']); print('yield by family', fam.most_common())
print('non-ambient or unstated temps', Counter('stated-other' if 'temperature_K' in o['conditions'] and not 293.15 <= o['conditions']['temperature_K'] <= 298.15 else 'ambient' if 'temperature_K' in o['conditions'] else 'unstated' for o in obs.values()))
print('with state', sum(1 for o in obs.values() if o['state_id']), 'of', len(obs))
