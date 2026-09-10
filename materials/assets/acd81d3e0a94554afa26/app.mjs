import {createSearch, MAX_RESULTS} from './search.mjs';
import {escapeHtml as h, displayUnit, unitLabel, resultText, summarize, summaryText, significant} from './format.mjs';

const view = document.querySelector('#view'), query = document.querySelector('#query');
const dataPath = document.body.dataset.path, buildId = document.body.dataset.build;
const base = new URL('./', location.href), cache = new Map();
let index, resolve, generation = 0, timer, currentRoute = {}, currentProjection;
let preference = {system: 'metric', overrides: {}};
try {
  const stored = JSON.parse(localStorage.getItem('materials.units.v1'));
  if (stored && ['metric', 'imperial'].includes(stored.system)) preference = {system: stored.system, overrides: stored.overrides || {}};
} catch { /* Preferences also work without persistent storage. */ }
document.querySelector('#unit-system').value = preference.system;
const href = route => './?' + new URLSearchParams(Object.entries(route).filter(([, v]) => v != null && v !== '')).toString();
const link = (route, text, cls = 'action') => `<a class="${cls}" href="${h(href(route))}">${h(text)}</a>`;
const propById = id => index.properties.find(p => p.id === id);
const entity = id => index.entities.find(e => e.id === id);
const category = id => index.taxa.find(t => t.id === id);
const unit = p => displayUnit(p, preference);
const readable = value => String(value).replaceAll('_', ' ');
const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;
const indent = depth => `style="--tree-indent:${depth * 18}px;--tree-indent-narrow:${Math.min(depth, 4) * 10}px"`;

async function fetchJSON(path) {
  if (!cache.has(path)) cache.set(path, fetch(new URL(`${dataPath}/${path}`, base), {cache: 'force-cache'})
    .then(async response => {
      if (!response.ok) throw new Error('Could not load the data.');
      const data = await response.json();
      if (data.build_id && data.build_id !== buildId) throw new Error('Catalog versions differ. Reload to update.');
      return data;
    }).catch(error => {cache.delete(path); throw error;}));
  return cache.get(path);
}
function title(text, routeLabel = text) {
  document.title = text === 'Materials' ? text : `${text} — Materials`;
  document.querySelector('#route-label').textContent = routeLabel;
}
function saveUnits() {
  try {localStorage.setItem('materials.units.v1', JSON.stringify(preference));} catch { /* Use session preferences. */ }
}
function unitSelect(p) {
  const automatic = unitLabel(displayUnit(p, {...preference, overrides:{}}).unit) || 'Ratio';
  return `<select data-unit="${h(p.id)}" aria-label="${h(p.name)} unit"><option value="">${h(automatic)} (auto)</option>${p.units.map(u => `<option value="${h(u.unit)}" ${preference.overrides[p.id] === u.unit ? 'selected' : ''}>${h(unitLabel(u.unit) || 'Ratio')}</option>`).join('')}</select>`;
}
function lineage(id) {
  const out = [];
  while (id) {const t = category(id); if (!t) break; out.unshift(t); id = t.primary_parent_id;}
  return out;
}
function breadcrumbs(taxon, property, material, state) {
  const links = lineage(taxon).map(t => link({category:t.id, ...(property ? {property} : {})}, t.name, 'breadcrumb-node'));
  if (material) links.push(link({material:material.id, ...(property ? {property} : {})}, material.name, 'breadcrumb-node'));
  if (state) links.push(link({material:material.id, state:state.id, ...(property ? {property} : {})}, state.name, 'breadcrumb-node'));
  return `<nav class="context breadcrumb" aria-label="Material category path">${links.join('<span class="breadcrumb-separator" aria-hidden="true">›</span>')}</nav>`;
}
function sectionHead(name, path = '', actions = link({}, 'New search')) {
  return `<header class="section-head"><div>${path}<h1>${h(name)}</h1></div><div class="section-actions">${actions}</div></header>`;
}
function counts(s) {
  return s ? `${plural(s.material_count, 'material')} · ${plural(s.observation_count, 'value')}` : '';
}
function renderHome() {
  title('Materials', 'Material datasheet or property overview');
  view.innerHTML = `<div class="idle"><div class="mode-row"><strong>Material datasheet</strong><span>Material or named state</span><div class="examples">${link({q:'6061-T6'}, '6061-T6', 'example')}${link({q:'TECAPEEK'}, 'TECAPEEK', 'example')}</div></div><div class="mode-row"><strong>Property overview</strong><span>Property or category + property</span><div class="examples">${link({q:'tensile strength'}, 'tensile strength', 'example')}${link({q:'plastic tensile strength'}, 'plastic tensile strength', 'example')}</div></div></div>`;
}
function renderSearch(result) {
  if (result.kind === 'comparison') {
    title('Comparison is not supported');
    view.innerHTML = `<div class="notice"><strong>Comparison is not supported.</strong><div class="choices">${link({q:'6061-T6'}, '6061-T6', 'choice')}${link({property:'ultimate_tensile_strength'}, 'Tensile strength', 'choice')}</div></div>`;
  } else if (result.kind === 'clarify') {
    title('Choose a property');
    view.innerHTML = `<div class="notice"><strong>Which strength?</strong><div class="choices">${result.group.member_property_ids.map(id => link({q:result.query, intent:id}, propById(id).name, 'choice')).join('')}</div></div>`;
  } else if (!result.matches.length) {
    title('No matches');
    view.innerHTML = '<div class="empty">No matching material or property.</div>';
  } else {
    title('Materials', `${plural(result.total, 'match')}${result.total > MAX_RESULTS ? ` · first ${MAX_RESULTS}` : ''}${result.property ? ' · ' + propById(result.property).name : ''}`);
    view.innerHTML = `<div class="match-list" aria-label="Material matches">${result.matches.map(e => `<a class="match" data-result-row href="${h(href({...e.route, ...(result.property ? {property:result.property} : {})}))}"><span><strong>${h(e.name)}</strong><small>${h(e.kind === 'category' ? 'Category' : e.kind === 'state' ? 'Named state' : e.kind === 'form' ? 'Product form' : category(e.category_ids[0])?.name || '')}</small></span><span class="match-context">${plural(e.properties.length, 'property').replace('propertys','properties')} · ${plural(e.observation_count, 'value')}</span><span class="open-label">${e.kind === 'category' ? 'Browse' : 'Open datasheet'} →</span></a>`).join('')}</div>`;
  }
}
function mergedSummary(summaries) {
  const result = {range:null, limits:{}, observation_count:0, material_count:0};
  function merge(a,b) {
    return a ? {minimum:Math.min(a.minimum,b.minimum), maximum:Math.max(a.maximum,b.maximum), significant_figures:Math.min(a.significant_figures,b.significant_figures), count:(a.count || 0) + (b.count || 0)} : {...b};
  }
  for (const s of summaries) {
    result.material_count += s.material_count;
    result.observation_count += s.observation_count;
    if (s.range) result.range = merge(result.range, s.range);
    for (const [kind, limit] of Object.entries(s.limits)) result.limits[kind] = merge(result.limits[kind],limit);
  }
  return result;
}
function categoryCount(id) {return index.entities.filter(e => e.kind === 'material' && e.category_ids.includes(id)).length;}
function taxonNode(taxon, depth, property) {
  const p = propById(property), s = currentProjection?.categories[taxon.id];
  return `<details class="taxon" id="taxon-${h(taxon.id)}" data-taxon="${h(taxon.id)}" data-depth="${depth}" ${indent(depth)}><summary><span class="node-name">${h(taxon.name)}<small>Category</small></span><span class="range">${p ? h(summaryText(s,unit(p))) : ''}${s?.mixed_conditions.length ? '<small>Mixed conditions</small>' : ''}</span><span class="counts">${p ? h(counts(s)) : plural(categoryCount(taxon.id),'material')}</span></summary><div class="node-body"></div></details>`;
}
function materialNode(e, depth, property) {
  const route = {...e.route, ...(property ? {property, category:currentRoute.category} : {})};
  if (!property) return `<div class="browse-material" ${indent(depth)}><strong>${h(e.name)}</strong><span>${plural(e.properties.length,'property').replace('propertys','properties')}</span>${link(route,'Open datasheet','action row-action')}</div>`;
  const p = propById(property), s = currentProjection.materials[e.id];
  return `<details class="material-node" id="material-${h(e.id)}" data-material="${h(e.id)}" data-depth="${depth}" ${indent(depth)}><summary><span class="node-name">${h(e.name)}</span><span class="range">${h(summaryText(s,unit(p)))}</span><span class="counts">${plural(s.observation_count,'value')}</span>${link(route,'Open focused record','action row-action')}</summary><div class="material-body"></div></details>`;
}
function taxonChildren(id, depth) {
  const property = currentRoute.property;
  const categories = index.taxa.filter(t => t.primary_parent_id === id && (!property || currentProjection.categories[t.id].observation_count)).sort((a,b) => a.name.localeCompare(b.name));
  const materials = index.entities.filter(e => e.kind === 'material' && e.category_ids[0] === id && (!property || currentProjection.materials[e.id].observation_count)).sort((a,b) => a.name.localeCompare(b.name));
  return categories.map(t => taxonNode(t,depth,property)).join('') + materials.map(m => materialNode(m,depth,property)).join('');
}
async function renderOverview(route, token) {
  const p = propById(route.property), scope = category(route.category);
  if ((route.property && !p) || (route.category && !scope)) throw new Error('Unknown property or category.');
  const projection = p ? await fetchJSON(`properties/${p.id}.json`) : null;
  if (token !== generation) return;
  currentProjection = projection;
  const roots = scope ? [scope] : index.taxa.filter(t => !t.primary_parent_id && (!p || projection.categories[t.id].observation_count));
  roots.sort((a,b) => a.name.localeCompare(b.name));
  const overall = p ? mergedSummary(roots.map(t => projection.categories[t.id])) : null;
  title(p?.name || scope.name, p ? 'Property overview' : 'Category browse');
  view.innerHTML = sectionHead(p?.name || scope.name, breadcrumbs(scope?.id,p?.id)) +
    (p ? `<div class="overview-summary"><div><strong>${h(summaryText(overall,unit(p)))}</strong>${scope ? `<span>${h(scope.name)}</span>` : ''}</div><div class="counts">${h(counts(overall))}</div>${unitSelect(p)}</div>` : '') +
    `<div class="tree" aria-label="${h(p?.name || scope.name)}">${roots.map(t => taxonNode(t,0,p?.id)).join('')}</div>`;
  if (scope) {
    const root = document.getElementById('taxon-' + scope.id);
    root.open = true;
    await expandNode(root);
  }
}
function contextText(o, record) {
  const state = record.states.find(s => s.id === o.state_id);
  const conditions = {...(state?.fixed_attributes || {}), ...o.conditions};
  return Object.entries(conditions).map(([k,v]) => {
    const c = index.conditions.find(c => c.id === k);
    if (k === 'temperature_K') return `${significant(preference.system === 'imperial' ? v*1.8-459.67 : v-273.15,3)} ${preference.system === 'imperial' ? '°F' : '°C'}`;
    if (k === 'product_form' || k === 'temper' || k === 'work_condition') return readable(v);
    if (typeof v === 'object') v = `${v.minimum ?? '…'}–${v.maximum ?? '…'} ${c?.canonical_unit || ''}`;
    return `${c?.name || readable(k)}: ${readable(v)}`;
  }).join(' · ');
}
function observationHTML(o, p, record) {
  const source = record.sources.find(s => s.id === o.source_id), raw = record.source_values[o.id];
  const url = new URL(source.url);
  if (o.source_locator.page) url.hash = 'page=' + o.source_locator.page;
  const basis = {lower_bound:'Minimum',upper_bound:'Maximum',interval:o.basis === 'specified_range' ? 'Specified range' : 'Reported range'}[o.result.kind] || readable(o.basis);
  return `<div class="observation" data-observation="${h(o.id)}"><div class="value">${h(resultText(o,unit(p)))}</div><div>${h([contextText(o,record),basis].filter(Boolean).join(' · '))}<details class="observation-details" id="test-${h(o.id)}"><summary>Test details</summary><div>${h(o.test_method?.reported_label || 'Method not specified')}${o.notes ? '<br>' + h(o.notes) : ''}</div></details></div><div class="citation"><a href="${h(url.href)}" target="_blank" rel="noopener noreferrer">${h(source.organization)} · p. ${o.source_locator.page}</a><details class="observation-details" id="source-${h(o.id)}"><summary>Source details</summary><div>${h(source.title)}<br>${h(o.source_locator.label)}<br><span class="original">Original: ${h(raw.text)} ${h(raw.unit)}</span></div></details></div></div>`;
}
function focusedRecordRows(record, property, depth) {
  const p = propById(property), pool = record.observations.filter(o => o.property_id === property);
  let result = pool.filter(o => !o.state_id).map(o => observationHTML(o,p,record)).join('');
  for (const state of record.states) {
    const rows = pool.filter(o => o.state_id === state.id);
    if (!rows.length) continue;
    result += `<details class="state-node" id="state-${h(state.id)}" ${indent(depth+1)}><summary><strong>${h(state.name)}</strong><span class="state-range">${h(summaryText(summarize(rows,property),unit(p)))}</span><span class="counts">${plural(rows.length,'value')}</span>${link({material:record.material.id,state:state.id,property,category:currentRoute.category},'Open focused state','action row-action')}</summary>${rows.map(o => observationHTML(o,p,record)).join('')}</details>`;
  }
  return result || '<div class="empty">Unreported</div>';
}
async function expandNode(node) {
  if (!node.open) return;
  const body = node.querySelector(':scope > .node-body, :scope > .material-body');
  if (!body || body.dataset.loaded) return;
  body.dataset.loaded = 'true';
  if (node.dataset.taxon) {
    body.innerHTML = taxonChildren(node.dataset.taxon, Number(node.dataset.depth)+1);
  } else if (node.dataset.material) {
    const token = generation, property = currentRoute.property;
    body.textContent = 'Loading…';
    try {
      const record = await fetchJSON(`records/${node.dataset.material}.json`);
      if (token === generation && node.isConnected && node.open) body.innerHTML = focusedRecordRows(record,property,Number(node.dataset.depth));
    } catch(error) {
      if (token === generation && node.isConnected) {
        delete body.dataset.loaded;
        body.innerHTML = `<div class="notice" role="alert">${h(error.message)} <button class="action" data-retry-node>Retry</button></div>`;
      }
    }
  }
}
function recordHTML(route, record) {
  const m = record.material, state = record.states.find(s => s.id === route.state), p = propById(route.property);
  if (route.state && !state) throw new Error('Unknown state for this material.');
  if (route.property && !p) throw new Error('Unknown property.');
  let pool = record.observations.filter(o => !route.state || o.state_id === route.state);
  if (route.form) pool = pool.filter(o => o.conditions.product_form === route.form && (route.state || o.state_id === null));
  const forms = [...new Set(record.observations.filter(o => route.state ? o.state_id === route.state : !o.state_id).map(o => o.conditions.product_form).filter(Boolean))].sort();
  if (route.form && !forms.includes(route.form)) throw new Error('Product form not reported.');
  const name = m.name + (state ? ' · ' + state.name : '');
  title(name, p && !route.all ? 'Property-focused datasheet' : 'Complete material datasheet');
  const shared = {material:m.id, property:p?.id, category:route.category};
  const actions = (p ? link({property:p.id,category:route.category},'Back to overview') : '') + `<a class="action" href="${h(dataPath)}/records/${h(m.id)}.json" download>JSON</a>` + link({},'New search');
  let html = sectionHead(name,breadcrumbs(m.primary_taxon_id,p?.id,state ? m : null),actions);
  const designations = m.designations.map(d => `${d.system_id.toUpperCase()} ${d.value}`);
  html += `<div class="record-meta">${h(designations.join(' · '))}</div>`;
  if (record.states.length) html += `<div class="record-navigation"><span>State</span><div class="choices">${link(shared,'All','choice' + (!state ? ' selected' : ''))}${record.states.map(s => link({...shared,state:s.id},s.name,'choice' + (state?.id === s.id ? ' selected' : ''))).join('')}</div></div>`;
  if (forms.length) html += `<div class="record-navigation"><span>Form</span><div class="choices">${route.form ? link({...route,form:''},'All','choice') : ''}${forms.map(f => link({...route,form:f},readable(f),'choice' + (route.form === f ? ' selected' : ''))).join('')}</div></div>`;
  if (p) html += `<div class="focus-bar"><strong>${h(route.all ? 'All properties' : p.name)}</strong>${link({...route,all:route.all ? '' : '1'},route.all ? 'Show focused property only' : 'Show all properties','action primary')}</div>`;
  const properties = p && !route.all ? [p] : index.properties.filter(property => pool.some(o => o.property_id === property.id));
  html += properties.map(property => {
    const rows = pool.filter(o => o.property_id === property.id);
    return `<section class="property-section" id="property-${h(property.id)}"><div class="property-heading"><h2>${h(property.name)}</h2><div class="property-tools"><span>${plural(rows.length,'value')}</span>${rows.length > 1 ? `<span class="property-range">${h(summaryText(summarize(rows,property.id),unit(property)))}</span>` : ''}${unitSelect(property)}</div></div>${rows.length ? rows.map(o => observationHTML(o,property,record)).join('') : '<div class="empty">Unreported</div>'}</section>`;
  }).join('');
  return html;
}
async function renderSources(token) {
  const sources = await fetchJSON('sources.json');
  if (token !== generation) return;
  title('Sources');
  view.innerHTML = sectionHead('Sources') + sources.map(s => `<section class="source-card"><h2><a href="${h(s.url)}" target="_blank" rel="noopener noreferrer">${h(s.organization)} — ${h(s.title)}</a></h2><div class="context">${h(s.publication_date || 'Undated')} · ${h(s.revision || '')} · Retrieved ${h(s.retrieved_date)}</div><details class="observation-details"><summary>Details</summary><div>${h(s.notes)}<br>${h(s.license)}${s.sha256 ? '<br><code>SHA-256 ' + h(s.sha256) + '</code>' : ''}</div></details></section>`).join('');
}

async function render() {
  if (!index) return;
  const token = ++generation;
  currentRoute = Object.fromEntries(new URLSearchParams(location.search));
  const route = currentRoute;
  if (route.q !== undefined) query.value = route.q;
  else if (!location.search) query.value = '';
  document.querySelector('#clear-search').hidden = !location.search;
  view.setAttribute('aria-busy', 'true');
  try {
    let target = route;
    if (route.q) {
      const start = performance.now(), result = resolve(route.q, propById(route.intent)?.id);
      document.querySelector('#timing').textContent = `${(performance.now() - start).toFixed(1)} ms`;
      if (result.kind === 'route') target = result.route;
      else {result.kind === 'home' ? renderHome() : renderSearch(result); return;}
    }
    if (target.property) target = {...target, property: index.property_aliases[target.property] || target.property};
    currentRoute = target;
    if (target.material) {
      const material = entity(target.material);
      if (!material || material.kind !== 'material') throw new Error('That material is not in this catalog.');
      const record = await fetchJSON(`records/${material.id}.json`);
      if (token !== generation) return;
      view.innerHTML = recordHTML(target, record);
    } else if (target.property || target.category) await renderOverview(target, token);
    else if (target.view === 'sources') await renderSources(token);
    else renderHome();
  } catch (error) {
    if (token !== generation) return;
    title('Could not load');
    view.innerHTML = `<div class="notice" role="alert"><strong>${h(error.message)}</strong><div class="choices"><button class="action" data-retry>Try again</button><button class="action" data-reload>Reload</button>${link({}, 'New search')}</div></div>`;
  } finally {
    if (token === generation) {view.setAttribute('aria-busy', 'false'); document.querySelector('#live').textContent = document.querySelector('#route-label').textContent;}
  }
}
function navigate(route, replace = false) {
  history[replace ? 'replaceState' : 'pushState']({}, '', href(route));
  render();
}
document.querySelector('#search-form').addEventListener('submit', event => {event.preventDefault(); clearTimeout(timer); navigate({q: query.value});});
document.querySelector('#clear-search').addEventListener('click', () => {clearTimeout(timer); navigate({}); query.focus();});
query.addEventListener('input', () => {clearTimeout(timer); const value = query.value; timer = setTimeout(() => navigate({q:value}, true), 160);});
query.addEventListener('keydown', event => {if (event.key === 'Escape') {clearTimeout(timer); navigate({});}});
document.addEventListener('click', event => {
  const retryNode = event.target.closest('[data-retry-node]');
  if (retryNode) {expandNode(retryNode.closest('[data-material]')); return;}
  if (event.target.closest('[data-retry]')) {render(); return;}
  if (event.target.closest('[data-reload]')) {location.reload(); return;}
  const anchor = event.target.closest('a');
  if (!anchor || anchor.hasAttribute('download') || anchor.target || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return;
  const url = new URL(anchor.href);
  if (url.origin === base.origin && url.pathname === base.pathname && !url.hash) {
    event.preventDefault(); clearTimeout(timer); history.pushState({}, '', url); render();
  }
});
view.addEventListener('toggle', event => {
  const node = event.target;
  if (!node.matches('[data-taxon], [data-material]')) return;
  if (node.open) expandNode(node);
  else {
    const body = node.querySelector(':scope > .node-body, :scope > .material-body');
    body.innerHTML = '';
    delete body.dataset.loaded;
  }
}, true);
async function restoreOpen(ids, token) {
  for (const id of ids) {
    if (token !== generation) return;
    const node = document.getElementById(id);
    if (node) {node.open = true; await expandNode(node);}
  }
}
document.addEventListener('change', async event => {
  if (event.target.id === 'unit-system') {preference = {system: event.target.value, overrides: {}};}
  else if (event.target.dataset.unit) {
    const id = event.target.dataset.unit, p = propById(id);
    if (p.units.some(u => u.unit === event.target.value)) preference.overrides[id] = event.target.value;
    else delete preference.overrides[id];
  } else return;
  const open = [...view.querySelectorAll('details[open][id]')].map(e => e.id);
  const focusedUnit = event.target.dataset.unit;
  saveUnits();
  const pendingRender = render(), token = generation;
  await pendingRender;
  if (token !== generation) return;
  await restoreOpen(open,token);
  if (focusedUnit) [...view.querySelectorAll('[data-unit]')].find(el => el.dataset.unit === focusedUnit)?.focus();
});
addEventListener('popstate', () => {clearTimeout(timer); render();});
try {
  index = await fetchJSON('index.json');
  if (index.version !== '1.0.0-rc.1' || index.contract_version !== '0.1.0') throw new Error('Unsupported catalog version.');
  resolve = createSearch(index);
  await render();
} catch (error) {
  view.setAttribute('aria-busy', 'false');
  view.innerHTML = `<div class="notice" role="alert"><strong>${h(error.message)}</strong><div class="choices"><button class="action" data-reload>Reload</button></div></div>`;
}
