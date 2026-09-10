import {createSearch, MAX_RESULTS} from './search.mjs';
import {escapeHtml as h, displayUnit, unitLabel, resultText, summarize, summaryText, significant} from './format.mjs';

const view = document.querySelector('#view'), query = document.querySelector('#query');
const dataPath = document.body.dataset.path, buildId = document.body.dataset.build;
const base = new URL('./', location.href), cache = new Map();
let index, resolve, generation = 0, timer, currentRoute = {}, currentRecord;
let preference = {system: 'metric', overrides: {}};
try {
  const stored = JSON.parse(localStorage.getItem('materials.units.v1'));
  if (stored && ['metric', 'imperial'].includes(stored.system)) preference = {system: stored.system, overrides: stored.overrides || {}};
} catch { /* Storage may be unavailable in private or embedded contexts. */ }
document.querySelector('#unit-system').value = preference.system;
const href = route => './?' + new URLSearchParams(Object.entries(route).filter(([, v]) => v != null && v !== '')).toString();
const link = (route, text, cls = '') => `<a class="${cls}" href="${h(href(route))}">${h(text)}</a>`;
const propById = id => index.properties.find(p => p.id === id);
const entity = id => index.entities.find(e => e.id === id);
const category = id => index.taxa.find(t => t.id === id);
const unit = p => displayUnit(p, preference);
const readable = value => String(value).replaceAll('_', ' ');

async function fetchJSON(path) {
  if (!cache.has(path)) cache.set(path, fetch(new URL(`${dataPath}/${path}`, base), {cache: 'force-cache'})
    .then(async response => {
      if (!response.ok) throw new Error('The catalog file could not be loaded.');
      const data = await response.json();
      if (data.build_id && data.build_id !== buildId) throw new Error('The site and catalog versions differ.');
      return data;
    }).catch(error => {cache.delete(path); throw error;}));
  return cache.get(path);
}
function title(text, routeLabel = text) {
  document.title = `${text} — Materials`;
  document.querySelector('#route-label').textContent = routeLabel;
}
function saveUnits() {
  try {localStorage.setItem('materials.units.v1', JSON.stringify(preference));} catch { /* Display preferences still work for this visit. */ }
}
function unitSelect(p) {
  return `<label class="unit-label">Display unit <select data-unit="${h(p.id)}" aria-label="${h(p.name)} unit"><option value="">System default</option>${p.units.map(u => `<option value="${h(u.unit)}" ${preference.overrides[p.id] === u.unit ? 'selected' : ''}>${h(unitLabel(u.unit) || 'Ratio')}</option>`).join('')}</select></label>`;
}
function lineage(id) {
  const out = [];
  while (id) {const t = category(id); if (!t) break; out.unshift(t); id = t.primary_parent_id;}
  return out;
}
function breadcrumbs(taxon, property, material, state) {
  const links = [link({}, 'All materials'), ...lineage(taxon).map(t => link({category: t.id, ...(property ? {property} : {})}, t.name))];
  if (material) links.push(link({material: material.id, ...(property ? {property} : {})}, material.name));
  if (state) links.push(link({material: material.id, state: state.id, ...(property ? {property} : {})}, state.name));
  return `<nav class="breadcrumb" aria-label="Breadcrumb">${links.join('<span class="sep" aria-hidden="true">/</span>')}</nav>`;
}
function directory(rows, headings = ['Material / category', 'Property coverage', 'Values']) {
  return `<div class="directory"><div class="directory-head">${headings.map(t => `<span>${h(t)}</span>`).join('')}</div>${rows.join('')}</div>`;
}
function directoryRow(e, property, s) {
  const p = propById(property), route = {...e.route, ...(property ? {property} : {})};
  const secondary = e.kind === 'category' ? 'Category' : e.kind === 'state' ? 'Named state' : e.kind === 'form' ? 'Product form' : category(e.category_ids[0])?.name || 'Material';
  const eligible = e.kind === 'category' ? index.entities.filter(m => m.kind === 'material' && m.category_ids.includes(e.id)).length : 1;
  const coverage = p && s ? `${s?.material_count || 0}/${eligible} ${eligible === 1 ? 'material' : 'materials'}<br>` : '';
  const mixed = s?.mixed_conditions?.length ? ' · Mixed conditions' : '';
  return `<a class="directory-row" data-result-row href="${h(href(route))}"><span><span class="row-name">${h(e.name)} <span class="row-arrow" aria-hidden="true">↗</span></span><span class="row-sub">${h(secondary + mixed)}</span></span><span class="row-value">${p ? (s ? h(summaryText(s, unit(p))) : (e.properties.includes(p.id) ? 'Reported' : 'Unreported')) : `${e.properties.length} properties`}</span><span class="row-count">${coverage}${p && s ? s.observation_count : e.observation_count} values</span></a>`;
}
function renderHome() {
  title('Reference lookup', 'Browse the reference catalog');
  const roots = index.entities.filter(e => e.kind === 'category' && !category(e.id).primary_parent_id).sort((a,b) => a.name.localeCompare(b.name));
  view.innerHTML = `<div class="intro"><div><p class="eyebrow">Material lookup</p><h2>Start with a name or designation</h2><p>Open a complete datasheet, then narrow to a named state or product form.</p><div class="chips">${['6061-T6', 'TECAPEEK', '316L'].map(q => link({q}, q, 'chip')).join('')}</div></div><div><p class="eyebrow">Property reference</p><h2>Explore a property by category</h2><p>See reported ranges and coverage, with individual sources a click away.</p><div class="chips">${['density', 'thermal conductivity', 'plastic strength'].map(q => link({q}, q, 'chip')).join('')}</div></div></div><div class="browse-heading"><h2>Browse materials</h2><span>Alphabetical categories</span></div>${directory(roots.map(e => directoryRow(e)))}<div class="browse-heading"><h2>Properties in this catalog</h2><span>${index.properties.length} registered properties</span></div><div class="chips">${index.properties.map(p => link({property: p.id}, p.name, 'chip')).join('')}</div>`;
}
function renderSearch(result) {
  title('Search', 'Search results');
  if (result.kind === 'comparison') {
    view.innerHTML = `<div class="empty-panel"><h1>Look up a material or a property</h1><p>This catalog provides published reference data. It does not rank materials or choose one for an application.</p><div class="chips">${link({q:'6061-T6'}, 'Open a material', 'chip')}${link({property:'ultimate_tensile_strength'}, 'Browse tensile strength', 'chip')}</div></div>`;
  } else if (result.kind === 'clarify') {
    view.innerHTML = `<div class="empty-panel"><p class="eyebrow">Choose a property</p><h1>Which kind of strength?</h1><p>The reported values describe different tests. Choose the property you want to look up.</p><div class="chips">${result.group.member_property_ids.map(id => link({q: result.query, intent: id}, propById(id).name, 'chip')).join('')}</div></div>`;
  } else if (!result.matches.length) {
    view.innerHTML = `<div class="empty-panel"><h1>No matching material found</h1><p>Try a designation, supplier grade or category. This reference slice covers aluminium 6061, selected stainless steels, engineering plastics and ceramics.</p>${link({}, 'Browse the catalog', 'button')}</div>`;
  } else {
    view.innerHTML = `<h1>Choose a material or category</h1><p class="description">${result.total} matches${result.property ? ' for ' + h(propById(result.property).name.toLowerCase()) : ''}. ${result.total > MAX_RESULTS ? `Showing the first ${MAX_RESULTS}; refine your search for more specific results.` : ''}</p>${directory(result.matches.map(e => directoryRow(e, result.property)))}`;
  }
}
async function renderOverview(route, token) {
  const p = propById(route.property), scope = category(route.category);
  if ((route.property && !p) || (route.category && !scope)) throw new Error('That property or category is not in this catalog.');
  const projection = p ? await fetchJSON(`properties/${p.id}.json`) : null;
  if (token !== generation) return;
  const taxonId = scope?.id || null;
  const nodes = index.entities.filter(e => e.kind === 'category' ? category(e.id).primary_parent_id === taxonId : e.kind === 'material' && e.category_ids[0] === taxonId)
    .sort((a, b) => (a.kind === b.kind ? a.name.localeCompare(b.name) : a.kind === 'category' ? -1 : 1));
  const page = Math.max(0, Math.min(Math.floor(Number(route.page) || 0), Math.max(0, Math.ceil(nodes.length / MAX_RESULTS) - 1)));
  const sliced = nodes.slice(page * MAX_RESULTS, (page + 1) * MAX_RESULTS);
  title(p ? `${scope ? scope.name + ' · ' : ''}${p.name}` : scope.name, p ? 'Property reference · Category ranges' : 'Category · Material directory');
  view.innerHTML = breadcrumbs(scope?.id, p?.id) + `<h1>${h(p?.name || scope.name)}</h1><p class="description">${p ? h(p.definition) : `Supplier grades and named materials in ${h(scope.name.toLowerCase())}.`}</p>${p ? `<div class="note">Ranges summarize published values across different materials and test conditions. Specified minimum and maximum limits are listed separately; they are not measured endpoints.${scope ? '<br><strong>' + h(scope.name) + ':</strong> ' + h(summaryText(projection.categories[scope.id], unit(p))) : ''}</div>` : ''}<div class="overview-controls"><h2>${h(scope?.name || 'All categories')}</h2>${p ? unitSelect(p) : ''}</div>${nodes.length ? directory(sliced.map(e => directoryRow(e, p?.id, projection?.[e.kind === 'category' ? 'categories' : 'materials'][e.id])), ['Material / category', p ? 'Reported range / limit' : 'Property coverage', 'Values']) : '<p class="empty">No materials are reported in this category.</p>'}${nodes.length > MAX_RESULTS ? `<div class="paging"><span>${page * MAX_RESULTS + 1}–${Math.min((page + 1) * MAX_RESULTS, nodes.length)} of ${nodes.length}</span><div>${page ? link({...route, page:page-1}, 'Previous', 'button') : ''} ${((page+1)*MAX_RESULTS < nodes.length) ? link({...route, page:page+1}, 'Next', 'button') : ''}</div></div>` : ''}`;
}
function contextText(o, record) {
  const state = record.states.find(s => s.id === o.state_id);
  const conditions = {...(state?.fixed_attributes || {}), ...o.conditions};
  const labels = Object.entries(conditions).map(([k,v]) => {
    const c = index.conditions.find(c => c.id === k);
    if (k === 'temperature_K') return `Test temperature: ${significant(preference.system === 'imperial' ? v*1.8-459.67 : v-273.15, 3)} ${preference.system === 'imperial' ? '°F' : '°C'}`;
    if (typeof v === 'object') v = `${v.minimum ?? 'unspecified'}–${v.maximum ?? 'unspecified'} ${c?.canonical_unit || ''}`;
    return `${c?.name || readable(k)}: ${readable(v)}`;
  });
  return labels.length ? labels.join(' · ') : 'No test conditions specified';
}
function observationHTML(o, p, record) {
  const source = record.sources.find(s => s.id === o.source_id), raw = record.source_values[o.id];
  const url = new URL(source.url);
  if (o.source_locator.page) url.hash = 'page=' + o.source_locator.page;
  return `<article class="observation" data-observation="${h(o.id)}"><div><div class="observation-value">${h(resultText(o, unit(p)))}</div><span class="basis">${h(o.result.kind === 'lower_bound' ? 'Specified minimum' : o.result.kind === 'upper_bound' ? 'Specified maximum' : readable(o.basis))}</span></div><div><p class="context">${h(contextText(o, record))}${o.notes ? '<br>' + h(o.notes) : ''}<br><strong>Method:</strong> ${h(o.test_method?.reported_label || 'Not specified')}</p><div class="citation"><a href="${h(url.href)}" target="_blank" rel="noopener noreferrer">${h(source.organization)} — ${h(source.title)} ↗</a><p>${h(o.source_locator.label)}</p><p class="original">As published: ${h(raw.text)} ${h(raw.unit)} · ${raw.significant_figures} significant figures</p></div></div></article>`;
}
function recordHTML(route, record) {
  const m = record.material, state = record.states.find(s => s.id === route.state), p = propById(route.property);
  if (route.state && !state) throw new Error('That named state does not belong to this material.');
  if (route.property && !p) throw new Error('That property is not in this catalog.');
  let pool = record.observations.filter(o => !route.state || o.state_id === route.state);
  if (route.form) pool = pool.filter(o => o.conditions.product_form === route.form && (route.state || o.state_id === null));
  const forms = [...new Set(record.observations.filter(o => route.state ? o.state_id === route.state : !o.state_id).map(o => o.conditions.product_form).filter(Boolean))].sort();
  if (route.form && !forms.includes(route.form)) throw new Error('That product form is not reported at this level.');
  title(m.name + (state ? ' · ' + state.name : ''), 'Material datasheet' + (p ? ' · Focused property' : ' · Complete record'));
  const stateChip = s => {
    const observations = record.observations.filter(o => o.state_id === s.id);
    const suffix = p ? summaryText(summarize(observations, p.id), unit(p)) : `${observations.length} values`;
    return `<a class="chip ${s.id === route.state ? 'active' : ''}" href="${h(href({material:m.id, state:s.id, ...(p ? {property:p.id} : {})}))}">${h(s.name)} <small>${h(suffix)}</small></a>`;
  };
  const shownCount = p && !route.all ? pool.filter(o => o.property_id === p.id).length : pool.length;
  const sections = (p && !route.all ? [p] : index.properties).map(property => {
    const observations = pool.filter(o => o.property_id === property.id);
    const aggregate = summarize(pool, property.id);
    return `<details class="property-section" id="property-${h(property.id)}" ${p?.id === property.id ? 'open' : ''}><summary><span>${h(property.name)}<small class="row-sub">${observations.length} reported ${observations.length === 1 ? 'value' : 'values'}</small></span><span class="summary-value">${h(summaryText(aggregate, unit(property)))}</span></summary><div class="property-body"><div class="property-meta"><p>${h(property.definition)}</p>${unitSelect(property)}</div>${observations.length ? observations.map(o => observationHTML(o, property, record)).join('') : '<p class="empty">This property is unreported at the selected level. Missing values are not zero.</p>'}</div></details>`;
  }).join('');
  return breadcrumbs(m.primary_taxon_id, p?.id, m, state) + `<div class="record-header"><div><p class="eyebrow">${state ? 'Named state · ' + h(state.name) : 'Material datasheet'}${route.form ? ' · ' + h(readable(route.form)) : ''}</p><h1>${h(m.name)}${state ? ' · ' + h(state.name) : ''}</h1></div><a class="button" href="${h(dataPath)}/records/${h(m.id)}.json" download>Record JSON ↓</a></div><div class="designations">${m.designations.map(d => `<span>${h(d.system_id.toUpperCase())} <b>${h(d.value)}</b></span>`).join('') || '<span>Identified by supplier grade name</span>'}</div><p class="description">${h(m.notes)}</p>${record.states.length ? `<div class="navigation-block"><p class="eyebrow">Named states</p><div class="chips">${link({material:m.id, ...(p ? {property:p.id} : {})}, 'All states & grade data', 'chip ' + (!route.state ? 'active' : ''))}${record.states.map(stateChip).join('')}</div></div>` : ''}${forms.length ? `<div class="navigation-block"><p class="eyebrow">Product form${!route.state && record.states.length ? ' · Direct grade data' : ''}</p><div class="chips">${route.form ? link({...route, form:''}, 'All forms', 'chip') : ''}${forms.map(f => link({...route, form:f}, readable(f), 'chip ' + (f === route.form ? 'active' : ''))).join('')}</div></div>` : ''}${route.state && record.observations.some(o => !o.state_id) ? `<p class="note">Additional properties are reported for the grade without a named state. ${link({material:m.id}, 'View grade-level data')}.</p>` : ''}<div class="focused-heading"><span>${p && !route.all ? h(p.name) : 'Properties'} · ${shownCount} reported ${shownCount === 1 ? 'value' : 'values'}</span>${p ? link({...route, all: route.all ? '' : '1'}, route.all ? 'Focus property' : 'Show all properties') : ''}</div>${sections}`;
}
async function renderSources(token) {
  const sources = await fetchJSON('sources.json');
  if (token !== generation) return;
  title('Sources & provenance', 'Catalog · Sources & provenance');
  view.innerHTML = `${breadcrumbs()}<h1>Sources & provenance</h1><p class="description">Values link to their source document and page. Revisions and retrieval dates identify the snapshots used to build this catalog. Manufacturer documents are linked, not redistributed.</p>${sources.map(s => `<article class="source-card"><p class="eyebrow">${h(s.organization)}</p><h2><a href="${h(s.url)}" target="_blank" rel="noopener noreferrer">${h(s.title)} ↗</a></h2><p>Revision: ${h(s.revision || 'Not stated')} · Published: ${h(s.publication_date || 'Not stated')} · Retrieved: ${h(s.retrieved_date)}</p><p>${h(s.notes)}</p><p>${h(s.license)}</p>${s.sha256 ? '<code>SHA-256: ' + h(s.sha256) + '</code>' : ''}</article>`).join('')}`;
}
async function render() {
  if (!index) return;
  const token = ++generation;
  currentRoute = Object.fromEntries(new URLSearchParams(location.search));
  const route = currentRoute;
  query.value = route.q || '';
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
      currentRecord = record;
      view.innerHTML = recordHTML(target, record);
    } else if (target.property || target.category) await renderOverview(target, token);
    else if (target.view === 'sources') await renderSources(token);
    else renderHome();
  } catch (error) {
    if (token !== generation) return;
    title('Unable to open this view');
    view.innerHTML = `<div class="empty-panel" role="alert"><h1>Unable to open this view</h1><p>${h(error.message)} If the site was updated, reload to get the latest catalog.</p><button data-retry>Try again</button> <button data-reload>Reload catalog</button> ${link({}, 'Back to browse', 'button')}</div>`;
  } finally {
    if (token === generation) {view.setAttribute('aria-busy', 'false'); document.querySelector('#live').textContent = document.querySelector('#route-label').textContent;}
  }
}
function navigate(route, replace = false) {
  history[replace ? 'replaceState' : 'pushState']({}, '', href(route));
  render();
}
document.querySelector('#search-form').addEventListener('submit', event => {event.preventDefault(); clearTimeout(timer); navigate({q: query.value});});
query.addEventListener('input', () => {clearTimeout(timer); const value = query.value; timer = setTimeout(() => navigate({q:value}, true), 160);});
query.addEventListener('keydown', event => {if (event.key === 'Escape') {clearTimeout(timer); navigate({});}});
document.addEventListener('click', event => {
  if (event.target.closest('[data-retry]')) {render(); return;}
  if (event.target.closest('[data-reload]')) {location.reload(); return;}
  const anchor = event.target.closest('a');
  if (!anchor || anchor.hasAttribute('download') || anchor.target || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return;
  const url = new URL(anchor.href);
  if (url.origin === base.origin && url.pathname === base.pathname && !url.hash) {
    event.preventDefault(); clearTimeout(timer); history.pushState({}, '', url); render();
  }
});
document.addEventListener('change', event => {
  if (event.target.id === 'unit-system') {preference = {system: event.target.value, overrides: {}};}
  else if (event.target.dataset.unit) {
    const id = event.target.dataset.unit, p = propById(id);
    if (p.units.some(u => u.unit === event.target.value)) preference.overrides[id] = event.target.value;
    else delete preference.overrides[id];
  } else return;
  const open = [...view.querySelectorAll('.property-section[open]')].map(e => e.id);
  saveUnits();
  if (currentRoute.material && currentRecord) {
    view.innerHTML = recordHTML(currentRoute, currentRecord);
    for (const id of open) {const detail = document.getElementById(id); if (detail) detail.open = true;}
  } else render();
});
addEventListener('popstate', () => {clearTimeout(timer); render();});
try {
  index = await fetchJSON('index.json');
  if (index.version !== '1.0.0-rc.1' || index.contract_version !== '0.1.0') throw new Error('Unsupported catalog version.');
  resolve = createSearch(index);
  await render();
} catch (error) {
  view.setAttribute('aria-busy', 'false');
  view.innerHTML = `<div class="empty-panel" role="alert"><h1>The catalog could not be loaded</h1><p>${h(error.message)}</p><button data-reload>Reload catalog</button></div>`;
}
