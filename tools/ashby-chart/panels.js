/* Materials list, inspector, ranking, results table, Compare and CSV. */
const { Axis, formatValue, clamp, FAMILY_COLORS, FAMILY_NAMES } = window.AshbyEngine;

export function setupPanels(ctx) {
  const { $, el, options, db, state, tags, precise } = ctx;
  const refresh = (...args) => ctx.refresh(...args);
  const PANES = ['show', 'browse', 'inspect', 'rank'];
  ctx.pane = 'show';

  /* ---------- tabs ---------- */
  function setPane(name) {
    ctx.pane = name;
    for (const pane of PANES) {
      $(pane + '-pane').hidden = pane !== name;
      $('tab-' + pane).setAttribute('aria-selected', String(pane === name));
      $('tab-' + pane).tabIndex = pane === name ? 0 : -1;
    }
    if ($('side').hidden) ctx.toggleSide(true);
    ctx.renderBrowser();
    ctx.syncHighlight();
  }
  ctx.setPane = setPane;
  for (const pane of PANES) $('tab-' + pane).addEventListener('click', () => setPane(pane));
  document.querySelector('.side-tabs').addEventListener('keydown', e => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(e.key)) return;
    e.preventDefault();
    const at = PANES.indexOf(ctx.pane), next = e.key === 'Home' ? 0 : e.key === 'End' ? PANES.length - 1 : (at + (e.key === 'ArrowRight' ? 1 : PANES.length - 1)) % PANES.length;
    setPane(PANES[next]); $('tab-' + PANES[next]).focus();
  });

  /* ---------- value text ---------- */
  const resultPrecise = o => db.resultText(o, precise);
  function conditionText(conditions) {
    return Object.entries(conditions).map(([key, value]) => {
      if (key === 'temperature_K') return precise(value - 273.15) + ' °C';
      if (key === 'thickness_m') {
        const lo = value.minimum == null ? 'unspecified' : precise(value.minimum * 1000);
        const hi = value.maximum == null ? 'unspecified' : precise(value.maximum * 1000);
        return `thickness ${lo} to ${hi} mm`;
      }
      if (key === 'moisture_content_1') return precise(value * 100) + '% moisture';
      if (key === 'orientation') return ({ L: 'longitudinal (0°)', LT: 'transverse (90°)', ST: 'through thickness', isotropic: 'isotropic' })[value] || value;
      return String(value).replaceAll('_', ' ');
    }).join(' · ') || 'Conditions not stated';
  }
  function sourceText(details, o) {
    const item = details.observations[o], source = details.sources[item.source];
    return [source?.organization, source?.title, source?.revision, item.locator].filter(Boolean).join('. ');
  }
  /* Merged condition text for a point: differing room temperatures are stated, never hidden. */
  function pointCondition(details, point) {
    const merged = {};
    for (const o of point.obs) Object.assign(merged, details.observations[o].conditions);
    if (point.temperatures_K.length > 1) {
      delete merged.temperature_K;
      return 'Room-temperature comparison: ' + point.temperatures_K.map(t => precise(t - 273.15) + ' °C').join(' / ') + (Object.keys(merged).length ? ' · ' + conditionText(merged) : '');
    }
    return conditionText(merged);
  }
  function scoreBasis(point) {
    if (point.hasBounds) return 'uses a reported bound; check each source basis';
    if (point.obs.some(o => db.isInterval(o))) return 'uses an interval midpoint';
    return [...new Set(point.obs.map(o => db.basisName(o)))].join(' / ');
  }

  /* ---------- inspector ---------- */
  let cardToken = 0;
  function datasheetLink(material, stateId) {
    const target = new URL('../materials/', location.href);
    target.searchParams.set('material', material.id);
    if (stateId) target.searchParams.set('state', stateId);
    return target.href;
  }
  async function fillCard(point) {
    const token = ++cardToken;
    $('detail-card').hidden = false;
    $('inspector-empty').hidden = true;
    $('card-name').textContent = ctx.pointName(point);
    $('card-meta').textContent = point.m.sub_family;
    const stateId = point.stateIndex >= 0 ? db.states[point.stateIndex].id : null;
    $('card-datasheet').href = datasheetLink(point.m, stateId);
    $('card-index').textContent = '';
    let details;
    try {
      if (!ctx.details) $('card-props').replaceChildren(el('caption', { class: 'inspector-loading' }, 'Loading sources…'));
      details = await ctx.ensureDetails();
    } catch (error) {
      if (token === cardToken) $('card-props').replaceChildren(el('caption', { class: 'inspector-loading' }, 'Could not load the sources. ' + error.message));
      return;
    }
    if (token !== cardToken) return;
    $('card-meta').textContent = point.m.sub_family + ' · ' + pointCondition(details, point);
    $('card-props').replaceChildren(...point.obs.map(o => {
      const item = details.observations[o], scope = db.obsState[o] >= 0 ? db.stateName(db.obsState[o]) : 'Grade-level value';
      const details_ = el('details', { class: 'source-citation' }, el('summary', {}, 'Test method & source'), el('span', { class: 'source-detail' }, item.method), el('span', { class: 'source-detail' }, sourceText(details, o)));
      return el('tr', {}, el('th', {}, db.propertyOf(o).label), el('td', {},
        el('span', { class: 'property-value' }, resultPrecise(o)),
        el('span', { class: 'result-kind' }, `${db.kindName(o).replaceAll('_', ' ')} · ${db.basisName(o)}`),
        el('span', { class: 'source-detail' }, `${scope}. ${conditionText(item.conditions)}.`),
        item.notes ? el('span', { class: 'source-detail' }, item.notes) : null, details_));
    }));
    const index = db.indices[state.index], score = index ? db.score(index, point.row, ctx.allow()) : NaN;
    if (index && Number.isFinite(score)) {
      let substitution = index.expression;
      for (const variable of index.variables) {
        const value = db.si[point.row.obs[db.propIndex.get(variable.property)]];
        substitution = substitution.replaceAll(variable.symbol, '(' + precise(value) + ')');
      }
      $('card-index').textContent = `M = ${index.expression} = ${substitution} = ${precise(score)} using SI values; ${scoreBasis(point)}.`;
    }
    ctx.syncUrl();
  }
  ctx.showCard = point => {
    ctx.selected = point;
    setPane('inspect');
    fillCard(point);
    ctx.syncHighlight();
    ctx.syncUrl();
  };
  function clearCard() {
    cardToken++;
    ctx.selected = null;
    $('detail-card').hidden = true;
    $('inspector-empty').hidden = false;
    ctx.syncHighlight();
    ctx.syncUrl();
  }
  /* Keep an open card current as filters change, and close it if its point leaves. */
  ctx.refreshCard = () => {
    if (!ctx.selected) return;
    const fresh = ctx.rowByKey.get(ctx.selected.key);
    if (!fresh || fresh.dim) { clearCard(); return; }
    ctx.selected = fresh.point;
    if (ctx.pane === 'inspect') fillCard(fresh.point);
  };
  function showMissing(material) {
    cardToken++;
    ctx.selected = null;
    setPane('inspect');
    $('detail-card').hidden = false;
    $('inspector-empty').hidden = true;
    $('card-name').textContent = material.name;
    $('card-meta').textContent = 'No compatible value for the current axes and filters.';
    const rows = db.rowsByMaterial.get(material.id) || [];
    const names = [...new Set(rows.flatMap(row => row.list.map(o => db.propertyOf(o).label)))];
    $('card-index').textContent = 'Available properties: ' + names.join(', ') + '.';
    const view = ctx.compatibleView(material);
    $('card-props').replaceChildren();
    if (view) {
      $('card-props').append(el('caption', {}, el('button', { type: 'button', onclick: () => {
        state.temperature = 'all'; state.basis = 'all'; ctx.syncControls();
        ctx.applyView(view);
        const row = ctx.plotted.find(r => r.m.id === material.id);
        if (row) ctx.showCard(row.point);
      } }, 'Show ' + view.name.toLowerCase() + ' chart')));
    }
    $('card-datasheet').href = datasheetLink(material, null);
    ctx.syncUrl();
  }
  $('card-close').addEventListener('click', () => { clearCard(); setPane('browse'); });
  ctx.openParallelPoint = (point, at) => ctx.openPointCard(point, at);
  ctx.closeParallelPoint = () => ctx.closePointCard();

  /* ---------- materials list ---------- */
  ctx.renderBrowser = () => {
    if (ctx.pane !== 'browse') return;
    const query = state.find;
    const byMaterial = new Map();
    for (const row of ctx.plotted) if (!byMaterial.has(row.m.id)) byMaterial.set(row.m.id, row);
    const list = db.materials.filter(m => state.families.has(m.family) && (byMaterial.has(m.id) || !query || m.search.includes(query)))
      .sort((a, b) => Number(byMaterial.has(b.id)) - Number(byMaterial.has(a.id)) || a.name.localeCompare(b.name));
    $('browse-count').textContent = list.length ? `${byMaterial.size.toLocaleString()} plotted · ${(list.length - byMaterial.size).toLocaleString()} need other axes or filters` : 'No matching materials. Clear the search or show all families.';
    const yAxis = ctx.yA;
    $('material-list').replaceChildren(...list.map(m => {
      const row = byMaterial.get(m.id);
      const value = row ? ctx.axisText(yAxis, row.point.row) : 'View available properties →';
      return el('li', {}, el('button', { type: 'button', class: ctx.selected?.m.id === m.id ? 'selected' : '', onclick: () => (row ? ctx.showCard(row.point) : showMissing(m)) },
        el('strong', {}, m.name), el('small', {}, `${FAMILY_NAMES[m.family]} · ${value}`)));
    }));
  };

  /* ---------- ranking ---------- */
  const plainProps = () => [db.bySym[state.x]?.id, db.bySym[state.y]?.id];
  ctx.populateIndices = () => {
    const [x, y] = plainProps();
    const fits = Object.entries(db.indices).filter(([, i]) => x && y && ((i.x === x && i.y === y) || (i.x === y && i.y === x)));
    const select = $('perf-index');
    options(select, [['', '(none)'], ...fits.map(([key, i]) => [key, `${i.name} (${i.expression})`])]);
    if (!fits.some(([key]) => key === state.index)) state.index = '';
    select.value = state.index;
    $('index-hint').textContent = fits.length ? 'Available indices use these two properties.' : 'No ranking index is defined for these axes.';
  };
  $('perf-index').onchange = e => { state.index = e.target.value; resetSort(); refresh(); };
  $('top-n').value = state.topN;
  $('top-n').onchange = e => { state.topN = clamp(Math.round(Number(e.target.value) || 5), 1, 20); e.target.value = state.topN; refresh(); };
  $('top-n').addEventListener('keydown', e => e.stopPropagation());
  ctx.updateRanking = () => {
    const index = db.indices[state.index], allow = ctx.allow();
    const body = $('ranking-body');
    ctx.ranked = [];
    ctx.lines = [];
    if (!index || !index.exponents) { $('ranking-section').hidden = true; return; }
    const scored = ctx.plotted.map(r => ({ point: r.point, row: r, score: db.score(index, r.point.row, allow) })).filter(r => Number.isFinite(r.score))
      .sort((a, b) => (index.maximize ? -1 : 1) * (a.score - b.score) || a.row.name.localeCompare(b.row.name));
    const top = scored.slice(0, state.topN);
    ctx.ranked = top.map(r => r.point);
    $('ranking-section').hidden = top.length === 0;
    $('ranking-title').textContent = `Top ${top.length}: ${index.name}`;
    $('index-equation').textContent = 'Equation (1): M = ' + index.expression;
    $('index-variables').textContent = 'M: reference index; ' + index.variables.map(v => {
      const p = db.props[db.propIndex.get(v.property)];
      return `${v.symbol}: ${p.label}${p.unit ? ' (' + p.unit + ')' : ''}`;
    }).join('; ') + '.';
    $('index-derivation').textContent = index.derivation;
    $('index-scope').textContent = index.scope;
    $('index-source').textContent = index.source;
    body.replaceChildren(...top.map((r, i) => el('tr', {}, el('td', { class: 'rank-num' }, i + 1),
      el('td', {}, el('button', { type: 'button', class: 'material-button', onclick: () => ctx.showCard(r.point) }, r.row.name), el('span', { class: 'source-detail' }, scoreBasis(r.point))),
      el('td', {}, precise(r.score)))));
    // Lines of equal index through the best, middle and last ranked materials.
    const [x] = plainProps();
    if (index.slope && state.xLog && state.yLog && ctx.xA.prop && ctx.yA.prop) {
      const slope = index.x === x ? index.slope : 1 / index.slope;
      const chosen = [top[0], top[Math.floor(top.length / 2)], top[top.length - 1]].filter(Boolean);
      const seen = new Set();
      for (const r of chosen) {
        if (seen.has(r.score)) continue;
        seen.add(r.score);
        ctx.lines.push({ slope, c: r.row.ty - slope * r.row.tx, label: 'M = ' + precise(r.score), score: r.score });
      }
    }
  };

  /* ---------- results and compare ---------- */
  let columns = ['Sy', 'UTS', 'k'], sortKey = 'auto', sortDir = -1, resultTab = 'results';
  const resetSort = () => { sortKey = 'auto'; sortDir = -1; };
  ctx.resetSort = resetSort;
  ctx.setResults = open => {
    state.resultsOpen = open;
    $('results-box').hidden = !open;
    $('results-btn').classList.toggle('on', open);
    $('results-btn').setAttribute('aria-pressed', String(open));
    if (open) ctx.renderResults();
    ctx.syncUrl();
  };
  $('results-btn').onclick = () => ctx.setResults(!state.resultsOpen);
  $('tab-results').onclick = () => { resultTab = 'results'; ctx.renderResults(); };
  $('tab-compare').onclick = () => { resultTab = 'compare'; ctx.renderResults(); };
  options($('add-col'), [['', '+ Column'], ...db.props.map(p => [p.symbol, p.label])]);
  $('add-col').onchange = e => { if (e.target.value && !columns.includes(e.target.value)) columns.push(e.target.value); e.target.value = ''; ctx.renderResults(); };
  const passingMaterials = () => [...new Set(ctx.passing.filter(ctx.rowLive).map(r => r.m.id))];
  $('tag-apply').onclick = () => { const input = $('tag-input'), name = input.value.trim(); const ids = passingMaterials(); if (name && ids.length) { input.value = ''; tags.add(name, ids); } };
  $('tag-input').addEventListener('keydown', e => { e.stopPropagation(); if (e.key === 'Enter') $('tag-apply').click(); });
  function setSort(key) { if (sortKey === key) sortDir = -sortDir; else { sortKey = key; sortDir = key === 'name' ? 1 : -1; } ctx.renderResults(); }
  ctx.togglePin = point => {
    if (ctx.pinned.has(point.key)) ctx.pinned.delete(point.key);
    else ctx.pinned.set(point.key, { name: ctx.pointName(point), row: point.row });
    ctx.renderResults();
  };
  ctx.renderResults = () => {
    if (!state.resultsOpen) return;
    $('tab-results').classList.toggle('on', resultTab === 'results');
    $('tab-compare').classList.toggle('on', resultTab === 'compare');
    $('results-tools').hidden = resultTab !== 'results';
    $('tab-compare').textContent = ctx.pinned.size ? `Compare ${ctx.pinned.size}` : 'Compare';
    if (resultTab === 'compare') { renderCompare(); return; }
    const allow = ctx.allow(), index = db.indices[state.index];
    const axes = [ctx.yA, ctx.xA].filter(a => a.prop).map(a => a.expr);
    const cols = [...new Set([...axes, ...columns])].filter(c => db.bySym[c]);
    const props = cols.map(c => db.bySym[c].index);
    // One line per distinct set of values in these columns, so a grade with many rows lists each once.
    const lines = new Map();
    for (const row of ctx.passing) {
      if (!ctx.rowLive(row)) continue;
      const key = row.m.i + '|' + props.map(p => { const o = row.obs[p]; return o >= 0 && (!allow || allow(o)) ? o : '-'; }).join(':');
      if (!lines.has(key)) lines.set(key, row);
    }
    const list = [...lines.values()].map(row => ({ row, score: index ? db.score(index, row, allow) : NaN }));
    const best = index ? Math.max(0, ...list.map(l => l.score).filter(Number.isFinite)) : 0;
    const key = sortKey === 'auto' ? (index ? 'score' : axes[0] || cols[0]) : sortKey;
    const read = l => {
      if (key === 'score') return l.score;
      const o = l.row.obs[db.bySym[key]?.index];
      return o >= 0 && (!allow || allow(o)) ? db.display[o] : NaN;
    };
    list.sort((a, b) => {
      if (key === 'name') return sortDir * a.row.m.name.localeCompare(b.row.m.name);
      const va = read(a), vb = read(b), okA = Number.isFinite(va), okB = Number.isFinite(vb);
      if (!okA || !okB) return okA ? -1 : okB ? 1 : 0;
      return sortDir * (va - vb);
    });
    const materials = new Set(list.map(l => l.row.m.i)).size;
    const plotted = new Set(ctx.plotted.map(r => r.m.i)).size;
    $('result-count').textContent = `${materials.toLocaleString()} materials, ${plotted.toLocaleString()} on this chart` + (list.length > 150 ? ', first 150 listed' : '');
    const headButton = (text, onclick, title) => el('button', { type: 'button', title, onclick }, text);
    const head = el('tr', {}, el('th', {}, headButton('Material', () => setSort('name'))),
      index ? el('th', {}, headButton('Index, % of best', () => setSort('score'), 'Performance index as a percentage of the best result')) : null,
      cols.map(c => el('th', {}, headButton(db.bySym[c].display_unit ? `${db.bySym[c].label} (${db.bySym[c].display_unit})` : db.bySym[c].label, e => { if (e.shiftKey) { columns = columns.filter(k => k !== c); ctx.renderResults(); } else setSort(c); }, 'Sort. Shift+click removes the column.'))),
      el('th', { 'aria-label': 'Compare' }));
    const pointFor = row => ctx.plotted.find(r => r.point.rows.includes(row))?.point || null;
    const body = list.slice(0, 150).map(({ row, score }) => {
      const stateIndex = row.list.map(o => db.obsState[o]).find(s => s >= 0) ?? -1;
      const name = row.m.name + (stateIndex >= 0 ? ' · ' + db.stateName(stateIndex) : '');
      const open = () => { const point = pointFor(row); if (point) ctx.openPointCard(point); else showMissing(row.m); };
      const pinKey = row.i;
      return el('tr', { class: ctx.popM?.row === row ? 'sel' : '', onclick: open },
        el('td', {}, el('span', { class: 'dot', style: `background:${FAMILY_COLORS[row.m.family]}` }), el('button', { type: 'button', class: 'row-open', onclick: e => { e.stopPropagation(); open(); } }, name)),
        index ? el('td', {}, Number.isFinite(score) && best ? Math.round(score / best * 100) + '%' : '–') : null,
        props.map(p => { const o = row.obs[p]; return el('td', {}, o >= 0 && (!allow || allow(o)) ? db.resultText(o).replace(/\s\S+$/, m => (db.propertyOf(o).display_unit ? '' : m)) : '–'); }),
        el('td', { class: 'pin' }, el('button', { type: 'button', class: 'ghost', 'aria-label': ctx.pinned.has('r' + pinKey) ? 'Remove from comparison' : 'Add to comparison', title: 'Compare', onclick: e => {
          e.stopPropagation();
          if (ctx.pinned.has('r' + pinKey)) ctx.pinned.delete('r' + pinKey); else ctx.pinned.set('r' + pinKey, { name, row });
          ctx.renderResults();
        } }, ctx.pinned.has('r' + pinKey) ? '✓' : '+')));
    });
    $('results-scroll').replaceChildren(el('table', { class: 'results' }, el('thead', {}, head), el('tbody', {}, body)));
  };
  function renderCompare() {
    const host = $('results-scroll'), list = [...ctx.pinned.values()];
    $('result-count').textContent = '';
    if (!list.length) { host.replaceChildren(el('p', { class: 'compare-empty' }, 'Click a point and choose Compare, or use + in the results.')); return; }
    const props = db.props.filter((p, i) => list.some(item => item.row.obs[i] >= 0));
    const lowerBetter = new Set(['density']);
    host.replaceChildren(
      el('div', { class: 'compare-acts' },
        el('button', { type: 'button', onclick: () => tags.add('Compared', list.map(item => item.row.m.id)) }, 'Save as tag "Compared"'),
        el('button', { type: 'button', class: 'ghost', onclick: () => { ctx.pinned.clear(); ctx.renderResults(); } }, 'Clear')),
      el('table', { class: 'compare' }, el('thead', {}, el('tr', {}, el('th', {}), list.map(item => el('th', { title: item.name }, item.name)))),
        el('tbody', {}, props.map(p => {
          const i = db.propIndex.get(p.id);
          const values = list.map(item => item.row.obs[i]).filter(o => o >= 0).map(o => db.display[o]);
          const top = lowerBetter.has(p.id) ? Math.min(...values) : Math.max(...values);
          return el('tr', {}, el('td', {}, p.display_unit ? `${p.label} (${p.display_unit})` : p.label), list.map(item => {
            const o = item.row.obs[i];
            return el('td', { class: list.length > 1 && o >= 0 && db.display[o] === top ? 'best' : '' }, o >= 0 ? db.resultText(o) : '–');
          }));
        }))),
      el('p', { class: 'compare-note' }, 'Bold marks the highest value, or the lowest density. It does not make a material better for your design.'));
  }

  /* ---------- CSV: SI values, kinds, ranges, citations and the build ID ---------- */
  function downloadCsv(name, header, records) {
    const csv = [header, ...records].map(record => record.map(value => '"' + String(value ?? '').replaceAll('"', '""') + '"').join(',')).join('\r\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const anchor = el('a', { href: url, download: name });
    anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  $('export-csv').addEventListener('click', async () => {
    const details = await ctx.ensureDetails();
    const parallel = state.view === 'parallel';
    const axes = parallel ? state.paxes.map(s => new Axis(db, s)) : [ctx.xA, ctx.yA];
    const allow = ctx.allow();
    const used = [...new Set(axes.flatMap(a => a.used))];
    const plain = !parallel && ctx.xA.prop && ctx.yA.prop && ctx.xA.expr !== ctx.yA.expr;
    const prefix = p => (plain ? (p === ctx.xA.prop.index ? 'X ' : 'Y ') : db.props[p].symbol + ' ');
    const columnNames = ['observation', 'property', 'value (SI)', 'unit', 'kind', 'minimum', 'maximum', 'basis', 'state', 'conditions', 'test method', 'notes', 'source'];
    const ordered = plain ? [ctx.xA.prop.index, ctx.yA.prop.index] : used;
    const points = parallel
      ? db.points(ctx.passing.filter(ctx.rowLive), axes, allow).filter(ctx.passesBasis)
      : ctx.plotted.map(r => r.point);
    const fields = o => {
      const item = details.observations[o];
      return [item.id, db.propertyOf(o).id, item.value, item.unit, db.kindName(o), item.minimum ?? '', item.maximum ?? '', db.basisName(o), db.obsState[o] >= 0 ? db.stateName(db.obsState[o]) : 'Grade-level value', conditionText(item.conditions), item.method, item.notes, sourceText(details, o)];
    };
    const formula = !parallel && !plain;
    const header = ['Material', 'State', 'Conditions', ...(formula ? [`Chart X: ${ctx.xA.pretty}`, `Chart Y: ${ctx.yA.pretty}`] : []), ...ordered.flatMap(p => columnNames.map(name => prefix(p) + name)), 'Index', 'Reference score', 'Materials build'];
    const records = points.map(point => [
      point.m.name, point.stateIndex >= 0 ? db.stateName(point.stateIndex) : '', pointCondition(details, point),
      ...(formula ? [ctx.xA.value(point.row, allow), ctx.yA.value(point.row, allow)] : []),
      ...ordered.flatMap(p => fields(point.row.obs[p])),
      state.index, db.indices[state.index] ? (Number.isFinite(db.score(db.indices[state.index], point.row, allow)) ? db.score(db.indices[state.index], point.row, allow) : '') : '', db.core.source_build_id,
    ]);
    downloadCsv('materials-ashby.csv', header, records);
  });
}
