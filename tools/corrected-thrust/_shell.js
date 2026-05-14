// Shared shell: builds the input form and wires up calculation.
// Reads from CT_ENGINE. Each prototype provides its own CSS — DOM is identical.
(function(){
'use strict';
const E = window.CT_ENGINE;

const COND_MODES = {
  'alt-T': {label:'Altitude + T', fields:[
    {key:'alt', label:'Altitude', kind:'altitude', def:550,  defUnit:'ft'},
    {key:'T',   label:'Temperature', kind:'temperature', def:25, defUnit:'°C'}
  ]},
  'PT': {label:'Raw P + T', fields:[
    {key:'P', label:'Pressure', kind:'pressure', def:101.3, defUnit:'kPa'},
    {key:'T', label:'Temperature', kind:'temperature', def:25, defUnit:'°C'}
  ]},
  'ISA': {label:'Altitude + ISA ΔT', fields:[
    {key:'alt', label:'Altitude', kind:'altitude', def:2500, defUnit:'ft'},
    {key:'dT',  label:'ΔT from ISA', kind:'tempDelta', def:30, defUnit:'°C'}
  ]}
};
const SIDE_DEFAULTS = {
  test:  {mode:'alt-T', overrides:{alt:550, T:25}},
  target:{mode:'ISA',  overrides:{alt:2500, dT:30}}
};

function unitOptions(kind){
  return E.UNITS[kind].list.map(u=>`<option>${u.sym}</option>`).join('');
}
function fieldHTML({id, label, hint='', kind, val, defUnit, fullWidth=false}){
  return `
  <div class="ct-field" data-field="${id}">
    <label for="${id}">${label}${hint?` <span class="ct-hint">${hint}</span>`:''}</label>
    <div class="ct-input-row${fullWidth?' ct-input-row--full':''}">
      <input type="number" inputmode="decimal" step="any" id="${id}" value="${val}">
      ${kind ? `<select id="${id}-u" data-kind="${kind}">${unitOptions(kind)}</select>` : ''}
    </div>
  </div>`;
}

function renderSideFields(side){
  const root = document.querySelector(`[data-side="${side}"] .ct-side-fields`);
  const mode = root.dataset.mode || SIDE_DEFAULTS[side].mode;
  root.dataset.mode = mode;
  const def = COND_MODES[mode];
  let html = '';
  for(const f of def.fields){
    const ovr = SIDE_DEFAULTS[side].overrides[f.key];
    const val = (ovr!==undefined ? ovr : f.def);
    html += fieldHTML({id:`${side}-${f.key}`, label:f.label, kind:f.kind, val, defUnit:f.defUnit});
  }
  html += `
    <div class="ct-field ct-field--rh" data-field="${side}-rh">
      <label for="${side}-rh">Relative humidity <span class="ct-hint">optional</span></label>
      <div class="ct-input-row ct-input-row--full">
        <input type="number" inputmode="decimal" step="any" min="0" max="100" id="${side}-rh" value="0" placeholder="0">
        <span class="ct-unit-static">%</span>
      </div>
    </div>`;
  root.innerHTML = html;
  // set default unit selections
  for(const f of def.fields){
    const sel = document.getElementById(`${side}-${f.key}-u`);
    if(sel && f.defUnit) sel.value = f.defUnit;
  }
}

function buildApp(host){
  host.innerHTML = `
  <section class="ct-card ct-mode">
    <h2>Mode</h2>
    <div class="ct-toggle" role="tablist">
      <button type="button" data-mode="findRPM" class="is-active">Find RPM for spec</button>
      <button type="button" data-mode="predictThrust">Predict thrust at target</button>
    </div>
    <p class="ct-mode-desc">Given target thrust spec, find the RPM to spin today &mdash; and what the load cell should read.</p>
  </section>

  <section class="ct-card ct-measure">
    <h2>Test-cell measurement</h2>
    ${fieldHTML({id:'t-measured', label:'Measured thrust', hint:'at test RPM, today', kind:'thrust', val:5.62})}
    ${fieldHTML({id:'n-test', label:'Test RPM', val:20000, fullWidth:true})}
    ${fieldHTML({id:'t-target', label:'Target thrust spec', kind:'thrust', val:6.74})}
  </section>

  <section class="ct-card ct-side" data-side="test">
    <h2>Test-cell conditions</h2>
    <div class="ct-cmode-tabs">
      <button type="button" data-cmode="alt-T" class="is-active">Altitude + T</button>
      <button type="button" data-cmode="PT">Raw P + T</button>
      <button type="button" data-cmode="ISA">Alt + ISA&Delta;T</button>
    </div>
    <div class="ct-side-fields"></div>
  </section>

  <section class="ct-card ct-side" data-side="target">
    <h2>Target conditions</h2>
    <div class="ct-cmode-tabs">
      <button type="button" data-cmode="alt-T">Altitude + T</button>
      <button type="button" data-cmode="PT">Raw P + T</button>
      <button type="button" data-cmode="ISA" class="is-active">Alt + ISA&Delta;T</button>
    </div>
    <div class="ct-side-fields"></div>
  </section>

  <button type="button" class="ct-calc-btn">Calculate</button>

  <section class="ct-results" hidden>
    <div class="ct-primary"></div>
    <div class="ct-card ct-detail">
      <h2>All outputs</h2>
      <div class="ct-rows"></div>
      <details class="ct-audit">
        <summary>Audit trail &mdash; every step</summary>
        <div class="ct-audit-body"></div>
      </details>
    </div>
    <div class="ct-export">
      <h2>Export analysis</h2>
      <div class="ct-export-buttons">
        <button type="button" class="ct-export-btn" data-export="print">Print / Save PDF</button>
        <button type="button" class="ct-export-btn ct-export-btn--alt" data-export="copy">Copy as text</button>
      </div>
      <div class="ct-export-toast" aria-live="polite"></div>
    </div>
  </section>

  <section class="ct-analysis-sheet" aria-hidden="true"></section>

  <section class="ct-card ct-explain">
    <details>
      <summary>How it works</summary>
      <div class="ct-explain-body">
        <p><strong>Affinity laws:</strong> for fixed geometry, thrust scales as <em>ρ N²</em>.
        Solving for required RPM at the test cell to hit a target-environment thrust spec:</p>
        <p class="ct-eq">N_req = N_test · √[ (T_spec / T_meas) · (ρ_tst / ρ_tgt) ]</p>
        <p>Load-cell reading at that RPM today:
        <span class="ct-eq-inline">T_load = T_spec · (ρ_tst / ρ_tgt)</span></p>
        <p>Same-RPM prediction at target:
        <span class="ct-eq-inline">T_tgt = T_meas · (ρ_tgt / ρ_tst)</span></p>
        <p><strong>Moist-air density:</strong>
        <span class="ct-eq-inline">ρ = ((P − P_v)·M_d + P_v·M_v) / (R·T)</span>,
        with P_v = RH · 610.94·exp(17.625·T_C/(T_C+243.04)) Pa (August–Roche–Magnus).</p>
        <p><strong>ISA</strong> troposphere (0–11 km): T(h)=288.15−0.0065h, P(h)=101325·(1−0.0065h/288.15)^5.2561.</p>
        <p><strong>Limits:</strong> assumes constant geometry and Reynolds-similar flow.</p>
      </div>
    </details>
  </section>`;

  // Init side fields
  for(const side of ['test','target']){
    document.querySelector(`[data-side="${side}"] .ct-side-fields`).dataset.mode = SIDE_DEFAULTS[side].mode;
    renderSideFields(side);
  }

  // Mode toggle
  host.querySelectorAll('.ct-toggle button').forEach(b=>{
    b.addEventListener('click', ()=>{
      host.querySelectorAll('.ct-toggle button').forEach(x=>x.classList.remove('is-active'));
      b.classList.add('is-active');
      const m = b.dataset.mode;
      const specField = host.querySelector('[data-field="t-target"]');
      if(specField) specField.style.display = (m==='findRPM') ? '' : 'none';
      host.querySelector('.ct-mode-desc').textContent = (m==='findRPM')
        ? 'Given target thrust spec, find the RPM to spin today — and what the load cell should read.'
        : 'Given the test-cell measurement, predict thrust at the target environment at the same RPM.';
    });
  });

  // Condition mode chips per side
  for(const side of ['test','target']){
    const tabs = host.querySelector(`[data-side="${side}"] .ct-cmode-tabs`);
    tabs.querySelectorAll('button').forEach(btn=>{
      btn.addEventListener('click', ()=>{
        tabs.querySelectorAll('button').forEach(x=>x.classList.remove('is-active'));
        btn.classList.add('is-active');
        const fieldsEl = host.querySelector(`[data-side="${side}"] .ct-side-fields`);
        fieldsEl.dataset.mode = btn.dataset.cmode;
        renderSideFields(side);
      });
    });
  }

  host.querySelector('.ct-calc-btn').addEventListener('click', ()=>calculate(host));

  // Export buttons
  host.querySelectorAll('.ct-export-btn').forEach(btn=>{
    btn.addEventListener('click', ()=>{
      const kind = btn.dataset.export;
      if(!host._ct_last){ return; }
      if(kind==='print'){
        // Ensure analysis sheet is current, typeset, then trigger print
        const sheet = host.querySelector('.ct-analysis-sheet');
        sheet.removeAttribute('aria-hidden');
        const afterTypeset = ()=> setTimeout(()=>window.print(), 80);
        if(window.MathJax && window.MathJax.typesetPromise){
          window.MathJax.typesetPromise([sheet]).then(afterTypeset).catch(afterTypeset);
        } else {
          afterTypeset();
        }
      } else if(kind==='copy'){
        const text = buildTextExport(host._ct_last);
        const done = ok => showExportToast(host, ok ? 'Copied to clipboard' : 'Copy failed — text in console');
        if(navigator.clipboard && navigator.clipboard.writeText){
          navigator.clipboard.writeText(text).then(()=>done(true)).catch(()=>{ console.log(text); done(false); });
        } else {
          // Fallback: temporary textarea
          const ta = document.createElement('textarea'); ta.value = text; document.body.appendChild(ta); ta.select();
          try { document.execCommand('copy'); done(true); } catch(e){ console.log(text); done(false); }
          ta.remove();
        }
      }
    });
  });
}

function showExportToast(host, msg){
  const toast = host.querySelector('.ct-export-toast');
  if(!toast) return;
  toast.textContent = msg;
  toast.classList.add('is-visible');
  clearTimeout(toast._t);
  toast._t = setTimeout(()=>toast.classList.remove('is-visible'), 2200);
}

function readSide(side){
  const fields = document.querySelector(`[data-side="${side}"] .ct-side-fields`);
  const mode = fields.dataset.mode;
  const RH_frac = (parseFloat(document.getElementById(`${side}-rh`).value)||0)/100;
  if(mode==='alt-T'){
    const alt_m = E.convertToSI(parseFloat(document.getElementById(`${side}-alt`).value), 'altitude', document.getElementById(`${side}-alt-u`).value);
    const T_K   = E.convertToSI(parseFloat(document.getElementById(`${side}-T`).value),   'temperature', document.getElementById(`${side}-T-u`).value);
    return {mode, alt_m, T_K, RH_frac};
  }
  if(mode==='PT'){
    const P_Pa = E.convertToSI(parseFloat(document.getElementById(`${side}-P`).value), 'pressure', document.getElementById(`${side}-P-u`).value);
    const T_K  = E.convertToSI(parseFloat(document.getElementById(`${side}-T`).value), 'temperature', document.getElementById(`${side}-T-u`).value);
    return {mode, P_Pa, T_K, RH_frac};
  }
  if(mode==='ISA'){
    const alt_m = E.convertToSI(parseFloat(document.getElementById(`${side}-alt`).value), 'altitude', document.getElementById(`${side}-alt-u`).value);
    const dT_K  = E.convertToSI(parseFloat(document.getElementById(`${side}-dT`).value),  'tempDelta', document.getElementById(`${side}-dT-u`).value);
    return {mode, alt_m, dT_K, RH_frac};
  }
}

function describeSide(label, ev){
  const f = E.fmt;
  let parts = [`<strong>${label}</strong>`];
  if(ev.mode==='alt-T'){ parts.push(`alt ${f(ev.alt)} m, T ${f(ev.T-273.15)} °C, P(ISA) ${f(ev.P/1000)} kPa`); }
  else if(ev.mode==='PT'){ parts.push(`P ${f(ev.P/1000)} kPa, T ${f(ev.T-273.15)} °C`); }
  else { parts.push(`alt ${f(ev.alt)} m, ISA T ${f(ev.T_isa-273.15)} °C, ΔT ${f(ev.dT)} K → T ${f(ev.T-273.15)} °C, P(ISA) ${f(ev.P/1000)} kPa`); }
  if(ev.RH>0) parts.push(`RH ${f(ev.RH*100)}%, P_v ${f(ev.RH*ev.Psat)} Pa`);
  parts.push(`ρ = ${f(ev.rho)} kg/m³`);
  return parts.join(' · ');
}

function calculate(host){
  const f = E.fmt;
  const mode = host.querySelector('.ct-toggle button.is-active').dataset.mode;
  const dispU = document.getElementById('t-measured-u').value;

  const T_measured_N = E.convertToSI(parseFloat(document.getElementById('t-measured').value), 'thrust', dispU);
  const N_test = parseFloat(document.getElementById('n-test').value);
  let T_spec_N = NaN;
  if(mode==='findRPM'){
    const specU = document.getElementById('t-target-u').value;
    T_spec_N = E.convertToSI(parseFloat(document.getElementById('t-target').value), 'thrust', specU);
  }

  const errs = [];
  if(!isFinite(T_measured_N)||T_measured_N<=0) errs.push('Measured thrust must be > 0');
  if(!isFinite(N_test)||N_test<=0) errs.push('Test RPM must be > 0');
  if(mode==='findRPM' && (!isFinite(T_spec_N)||T_spec_N<=0)) errs.push('Target thrust spec must be > 0');
  const test = readSide('test'), tgt = readSide('target');
  const res = E.solve({mode, T_measured_N, T_spec_N, N_test, displayUnit:dispU, test, target:tgt});
  if(!isFinite(res.test.rho)||res.test.rho<=0) errs.push('Could not compute test-cell density');
  if(!isFinite(res.tgt.rho)||res.tgt.rho<=0) errs.push('Could not compute target density');

  const box = host.querySelector('.ct-results');
  const primary = host.querySelector('.ct-primary');
  const rows = host.querySelector('.ct-rows');
  const audit = host.querySelector('.ct-audit-body');
  box.hidden = false;

  if(errs.length){
    primary.innerHTML = `<div class="ct-primary-label">Input error</div><div class="ct-primary-error">${errs.join(' · ')}</div>`;
    rows.innerHTML = ''; audit.innerHTML = '';
    return;
  }

  let primaryHTML='', rowsHTML='', auditHTML='';
  auditHTML += `<div class="ct-step"><div class="ct-step-name">Test conditions</div><div class="ct-step-detail">${describeSide('Test', res.test)}</div></div>`;
  auditHTML += `<div class="ct-step"><div class="ct-step-name">Target conditions</div><div class="ct-step-detail">${describeSide('Target', res.tgt)}</div></div>`;
  auditHTML += `<div class="ct-step"><div class="ct-step-name">Density ratio</div><div class="ct-step-eq">ρ_tgt / ρ_tst = ${f(res.tgt.rho)} / ${f(res.test.rho)} = <strong>${f(res.rho_ratio_tgt_tst)}</strong></div></div>`;

  if(mode==='predictThrust'){
    primaryHTML = `
      <div class="ct-primary-label">Predicted thrust at target (same RPM)</div>
      <div class="ct-primary-value">${f(res.T_pred_disp)}<span class="ct-primary-unit">${dispU}</span></div>
      <div class="ct-primary-sub">${f(res.T_sameRPM_N)} N · at ${f(N_test)} RPM</div>`;
    rowsHTML += rowHTML('Predicted thrust @ target, same RPM', `${f(res.T_pred_disp)} ${dispU}`);
    rowsHTML += rowHTML('  (in N)', `${f(res.T_sameRPM_N)} N`);
    rowsHTML += rowHTML('Density ratio ρ_tgt/ρ_tst', f(res.rho_ratio_tgt_tst));
    rowsHTML += rowHTML('Test density', `${f(res.test.rho)} kg/m³`);
    rowsHTML += rowHTML('Target density', `${f(res.tgt.rho)} kg/m³`);
    auditHTML += `<div class="ct-step"><div class="ct-step-name">Affinity-law (same RPM)</div>
      <div class="ct-step-eq">T_tgt = T_meas · (ρ_tgt / ρ_tst) = ${f(T_measured_N)} · ${f(res.rho_ratio_tgt_tst)} = <strong>${f(res.T_sameRPM_N)} N</strong> (${f(res.T_pred_disp)} ${dispU})</div></div>`;
  } else {
    primaryHTML = `
      <div class="ct-primary-label">Spin at this RPM today</div>
      <div class="ct-primary-value">${Math.round(res.N_req).toLocaleString()}<span class="ct-primary-unit">RPM</span></div>
      <div class="ct-primary-sub">Load cell should read <strong>${f(res.T_load_disp)} ${dispU}</strong></div>`;
    rowsHTML += rowHTML('Required RPM', `${Math.round(res.N_req).toLocaleString()} RPM`);
    rowsHTML += rowHTML('Load-cell reading @ N_req', `${f(res.T_load_disp)} ${dispU}`);
    rowsHTML += rowHTML('  (in N)', `${f(res.T_load_N)} N`);
    rowsHTML += rowHTML('Same-RPM prediction', `${f(res.T_sameRPM_disp)} ${dispU}`);
    rowsHTML += rowHTML('Density ratio ρ_tst/ρ_tgt', f(res.rho_ratio_tst_tgt));
    rowsHTML += rowHTML('Test density', `${f(res.test.rho)} kg/m³`);
    rowsHTML += rowHTML('Target density', `${f(res.tgt.rho)} kg/m³`);
    auditHTML += `<div class="ct-step"><div class="ct-step-name">Required RPM</div>
      <div class="ct-step-eq">N_req = N_test · √[ (T_spec / T_meas) · (ρ_tst / ρ_tgt) ] = ${f(N_test)} · √(${f(res.ratio_inside_sqrt)}) = <strong>${f(res.N_req)} RPM</strong></div></div>`;
    auditHTML += `<div class="ct-step"><div class="ct-step-name">Load-cell reading</div>
      <div class="ct-step-eq">T_load = T_spec · (ρ_tst / ρ_tgt) = ${f(T_spec_N)} · ${f(res.rho_ratio_tst_tgt)} = <strong>${f(res.T_load_N)} N</strong> (${f(res.T_load_disp)} ${dispU})</div></div>`;
  }

  primary.innerHTML = primaryHTML;
  rows.innerHTML = rowsHTML;
  audit.innerHTML = auditHTML;

  // Stash for export & build printable analysis sheet
  const inp = {mode, T_measured_N, T_spec_N, N_test, dispU, test, target:tgt, raw:readRawInputs(host, mode)};
  host._ct_last = {inp, res};
  const sheet = host.querySelector('.ct-analysis-sheet');
  if(sheet){
    sheet.innerHTML = buildAnalysisSheet(inp, res);
    if(window.MathJax && window.MathJax.typesetPromise){
      window.MathJax.typesetPromise([sheet]).catch(()=>{});
    }
  }

  box.scrollIntoView({behavior:'smooth', block:'start'});
}

function readRawInputs(host, mode){
  // capture displayed values+units for the export header
  const get = id => document.getElementById(id);
  const out = {
    t_measured: {val: get('t-measured').value, unit: get('t-measured-u').value},
    n_test: get('n-test').value,
  };
  if(mode==='findRPM'){
    out.t_target = {val: get('t-target').value, unit: get('t-target-u').value};
  }
  for(const side of ['test','target']){
    const fields = document.querySelector(`[data-side="${side}"] .ct-side-fields`);
    const cmode = fields.dataset.mode;
    const s = {cmode, rh: get(`${side}-rh`).value};
    if(cmode==='alt-T'){ s.alt={val:get(`${side}-alt`).value,unit:get(`${side}-alt-u`).value}; s.T={val:get(`${side}-T`).value,unit:get(`${side}-T-u`).value}; }
    if(cmode==='PT'){    s.P={val:get(`${side}-P`).value,unit:get(`${side}-P-u`).value};    s.T={val:get(`${side}-T`).value,unit:get(`${side}-T-u`).value}; }
    if(cmode==='ISA'){   s.alt={val:get(`${side}-alt`).value,unit:get(`${side}-alt-u`).value}; s.dT={val:get(`${side}-dT`).value,unit:get(`${side}-dT-u`).value}; }
    out[side]=s;
  }
  return out;
}

function rowHTML(k,v){ return `<div class="ct-row"><span class="ct-row-k">${k}</span><span class="ct-row-v">${v}</span></div>`; }

// ---------- Analysis sheet (printable HTML + MathJax) ----------
const CMODE_LABEL = {'alt-T':'Altitude + Temperature', 'PT':'Raw Pressure + Temperature', 'ISA':'Altitude + ISA ΔT'};

function inputsTable(raw, mode){
  const rows = [];
  rows.push(['Measured thrust', `${raw.t_measured.val} ${raw.t_measured.unit}`]);
  rows.push(['Test RPM',        `${raw.t_measured && raw.n_test} RPM`]);
  if(mode==='findRPM') rows.push(['Target thrust spec', `${raw.t_target.val} ${raw.t_target.unit}`]);
  for(const side of ['test','target']){
    const s = raw[side];
    rows.push([`${side==='test'?'Test':'Target'} mode`, CMODE_LABEL[s.cmode]]);
    if(s.cmode==='alt-T'){ rows.push([`  altitude`, `${s.alt.val} ${s.alt.unit}`]); rows.push([`  temperature`, `${s.T.val} ${s.T.unit}`]); }
    if(s.cmode==='PT'){    rows.push([`  pressure`, `${s.P.val} ${s.P.unit}`]); rows.push([`  temperature`, `${s.T.val} ${s.T.unit}`]); }
    if(s.cmode==='ISA'){   rows.push([`  altitude`, `${s.alt.val} ${s.alt.unit}`]); rows.push([`  ΔT from ISA`, `${s.dT.val} ${s.dT.unit}`]); }
    rows.push([`  relative humidity`, `${parseFloat(s.rh)||0} %`]);
  }
  return `<table class="as-table">${rows.map(r=>`<tr><td>${r[0]}</td><td>${r[1]}</td></tr>`).join('')}</table>`;
}

function sideEqBlock(label, ev){
  const f = E.fmt;
  const Pv = ev.RH>0 ? ev.RH*ev.Psat : 0;
  const Pd = ev.P - Pv;
  let setup = '';
  if(ev.mode==='alt-T'){
    setup = `\\[ P = P_{0}\\left(1 - \\dfrac{Lh}{T_{0}}\\right)^{\\!gM_{d}/(RL)} = ${f(ev.P)}\\ \\text{Pa},\\quad T = ${f(ev.T-273.15)}\\ {}^{\\circ}\\!\\text{C} \\]`;
  } else if(ev.mode==='PT'){
    setup = `\\[ P = ${f(ev.P)}\\ \\text{Pa},\\quad T = ${f(ev.T-273.15)}\\ {}^{\\circ}\\!\\text{C} \\]`;
  } else {
    setup = `\\[ P(h) = ${f(ev.P)}\\ \\text{Pa},\\quad T = T_{\\text{ISA}}(h) + \\Delta T = ${f(ev.T_isa-273.15)} + ${f(ev.dT)} = ${f(ev.T-273.15)}\\ {}^{\\circ}\\!\\text{C} \\]`;
  }
  const humidityRow = ev.RH>0
    ? `\\[ P_{\\text{sat}}(T) = 610.94\\,\\exp\\!\\left(\\dfrac{17.625\\,T_{C}}{T_{C}+243.04}\\right) = ${f(ev.Psat)}\\ \\text{Pa},\\quad P_{v} = \\phi\\, P_{\\text{sat}} = ${f(Pv)}\\ \\text{Pa} \\]`
    : `<div class="as-note">Humidity neglected (RH = 0).</div>`;
  return `
    <div class="as-side">
      <h4>${label}</h4>
      ${setup}
      ${humidityRow}
      \\[ \\rho = \\dfrac{(P - P_{v})\\,M_{d} + P_{v}\\,M_{v}}{R\\,T} = \\dfrac{(${f(Pd)})(0.028964) + (${f(Pv)})(0.018015)}{(8.31446)(${f(ev.T)})} = \\mathbf{${f(ev.rho)}}\\ \\text{kg/m}^{3} \\]
    </div>`;
}

function buildAnalysisSheet(inp, res){
  const f = E.fmt;
  const now = new Date();
  const stamp = now.toISOString().slice(0,10) + ' ' + now.toTimeString().slice(0,5);
  const modeTitle = inp.mode==='findRPM' ? 'Required RPM for target thrust spec' : 'Predicted thrust at target (same RPM)';

  let solution = '';
  if(inp.mode==='findRPM'){
    solution = `
      <div class="as-section"><h3>4 — Solve for required RPM</h3>
        \\[ N_{\\text{req}} = N_{\\text{test}} \\sqrt{ \\dfrac{T_{\\text{spec}}}{T_{\\text{meas}}} \\cdot \\dfrac{\\rho_{\\text{tst}}}{\\rho_{\\text{tgt}}} } \\]
        \\[ N_{\\text{req}} = ${f(inp.N_test)} \\cdot \\sqrt{ \\dfrac{${f(inp.T_spec_N)}}{${f(inp.T_measured_N)}} \\cdot ${f(res.rho_ratio_tst_tgt)} } = ${f(inp.N_test)} \\cdot \\sqrt{${f(res.ratio_inside_sqrt)}} = \\mathbf{${Math.round(res.N_req).toLocaleString()}\\ \\text{RPM}} \\]
      </div>
      <div class="as-section"><h3>5 — Load-cell reading at that RPM today</h3>
        \\[ T_{\\text{load}} = T_{\\text{spec}} \\cdot \\dfrac{\\rho_{\\text{tst}}}{\\rho_{\\text{tgt}}} = ${f(inp.T_spec_N)} \\cdot ${f(res.rho_ratio_tst_tgt)} = \\mathbf{${f(res.T_load_N)}\\ \\text{N}} = \\mathbf{${f(res.T_load_disp)}\\ ${inp.dispU}} \\]
      </div>
      <div class="as-final">
        <div class="as-final-label">FINAL — Spin at this RPM today</div>
        <div class="as-final-value">${Math.round(res.N_req).toLocaleString()} <span class="as-final-unit">RPM</span></div>
        <div class="as-final-sub">Load cell should read <strong>${f(res.T_load_disp)} ${inp.dispU}</strong> (${f(res.T_load_N)} N)</div>
      </div>`;
  } else {
    solution = `
      <div class="as-section"><h3>4 — Affinity-law solution (same RPM)</h3>
        \\[ T_{\\text{tgt}} = T_{\\text{meas}} \\cdot \\dfrac{\\rho_{\\text{tgt}}}{\\rho_{\\text{tst}}} = ${f(inp.T_measured_N)} \\cdot ${f(res.rho_ratio_tgt_tst)} = \\mathbf{${f(res.T_sameRPM_N)}\\ \\text{N}} = \\mathbf{${f(res.T_pred_disp)}\\ ${inp.dispU}} \\]
      </div>
      <div class="as-final">
        <div class="as-final-label">FINAL — Predicted thrust at target (same RPM)</div>
        <div class="as-final-value">${f(res.T_pred_disp)} <span class="as-final-unit">${inp.dispU}</span></div>
        <div class="as-final-sub">${f(res.T_sameRPM_N)} N · at ${f(inp.N_test)} RPM</div>
      </div>`;
  }

  return `
    <header class="as-head">
      <div class="as-eyebrow">Transparent Tools · Analysis Report</div>
      <h2 class="as-title">Corrected Thrust &amp; RPM</h2>
      <div class="as-sub">${modeTitle}</div>
      <div class="as-meta">Generated ${stamp}</div>
    </header>

    <div class="as-section">
      <h3>1 — Inputs</h3>
      ${inputsTable(inp.raw, inp.mode)}
    </div>

    <div class="as-section">
      <h3>2 — Air density at each operating point</h3>
      <p class="as-note">Moist-air density from partial pressures of dry air and water vapor:
        \\( \\rho = \\dfrac{(P - P_{v})M_{d} + P_{v}M_{v}}{RT} \\),
        with \\( M_{d}{=}0.028964 \\), \\( M_{v}{=}0.018015 \\) kg/mol, \\( R{=}8.31446 \\) J/(mol·K).
        Saturation vapor pressure: August–Roche–Magnus.</p>
      ${sideEqBlock('Test cell', res.test)}
      ${sideEqBlock('Target environment', res.tgt)}
    </div>

    <div class="as-section">
      <h3>3 — Density ratio</h3>
      \\[ \\dfrac{\\rho_{\\text{tgt}}}{\\rho_{\\text{tst}}} = \\dfrac{${f(res.tgt.rho)}}{${f(res.test.rho)}} = ${f(res.rho_ratio_tgt_tst)}, \\qquad \\dfrac{\\rho_{\\text{tst}}}{\\rho_{\\text{tgt}}} = ${f(res.rho_ratio_tst_tgt)} \\]
    </div>

    ${solution}

    <footer class="as-foot">
      <div>Affinity laws assume constant geometry and Reynolds-similar flow.</div>
      <div>transparent.tools · corrected-thrust</div>
    </footer>`;
}

// ---------- Text export (markdown-ish, Unicode symbols) ----------
function buildTextExport(last){
  const f = E.fmt;
  const {inp, res} = last;
  const lines = [];
  const hr = '─'.repeat(60);
  const now = new Date();
  lines.push('CORRECTED THRUST & RPM — Analysis Report');
  lines.push('Transparent Tools · ' + now.toISOString().slice(0,10) + ' ' + now.toTimeString().slice(0,5));
  lines.push(hr);
  lines.push('Mode: ' + (inp.mode==='findRPM' ? 'Find RPM for target spec' : 'Predict thrust at target (same RPM)'));
  lines.push('');
  lines.push('1 — INPUTS');
  lines.push(`  Measured thrust    : ${inp.raw.t_measured.val} ${inp.raw.t_measured.unit}`);
  lines.push(`  Test RPM           : ${inp.raw.n_test} RPM`);
  if(inp.mode==='findRPM') lines.push(`  Target thrust spec : ${inp.raw.t_target.val} ${inp.raw.t_target.unit}`);
  for(const side of ['test','target']){
    const s = inp.raw[side];
    lines.push(`  ${side==='test'?'Test':'Target'} (${CMODE_LABEL[s.cmode]}):`);
    if(s.cmode==='alt-T'){ lines.push(`     altitude    = ${s.alt.val} ${s.alt.unit}`); lines.push(`     temperature = ${s.T.val} ${s.T.unit}`); }
    if(s.cmode==='PT'){    lines.push(`     pressure    = ${s.P.val} ${s.P.unit}`); lines.push(`     temperature = ${s.T.val} ${s.T.unit}`); }
    if(s.cmode==='ISA'){   lines.push(`     altitude    = ${s.alt.val} ${s.alt.unit}`); lines.push(`     ΔT from ISA = ${s.dT.val} ${s.dT.unit}`); }
    lines.push(`     RH          = ${parseFloat(s.rh)||0} %`);
  }
  lines.push('');
  lines.push('2 — AIR DENSITY');
  lines.push('  ρ = ((P − P_v)·M_d + P_v·M_v) / (R·T)');
  lines.push('  P_sat = 610.94 · exp(17.625·T_C / (T_C + 243.04))  [August–Roche–Magnus]');
  for(const [label, ev] of [['Test cell', res.test], ['Target', res.tgt]]){
    const Pv = ev.RH>0 ? ev.RH*ev.Psat : 0;
    lines.push(`  ${label}:`);
    lines.push(`     P  = ${f(ev.P)} Pa`);
    lines.push(`     T  = ${f(ev.T-273.15)} °C  (${f(ev.T)} K)`);
    if(ev.RH>0){
      lines.push(`     RH = ${f(ev.RH*100)} %, P_sat = ${f(ev.Psat)} Pa, P_v = ${f(Pv)} Pa`);
    }
    lines.push(`     ρ  = ${f(ev.rho)} kg/m³`);
  }
  lines.push('');
  lines.push('3 — DENSITY RATIO');
  lines.push(`  ρ_tgt / ρ_tst = ${f(res.tgt.rho)} / ${f(res.test.rho)} = ${f(res.rho_ratio_tgt_tst)}`);
  lines.push(`  ρ_tst / ρ_tgt = ${f(res.rho_ratio_tst_tgt)}`);
  lines.push('');
  if(inp.mode==='findRPM'){
    lines.push('4 — REQUIRED RPM');
    lines.push('  N_req = N_test · √[ (T_spec / T_meas) · (ρ_tst / ρ_tgt) ]');
    lines.push(`        = ${f(inp.N_test)} · √[ (${f(inp.T_spec_N)} / ${f(inp.T_measured_N)}) · ${f(res.rho_ratio_tst_tgt)} ]`);
    lines.push(`        = ${f(inp.N_test)} · √(${f(res.ratio_inside_sqrt)})`);
    lines.push(`        = ${Math.round(res.N_req).toLocaleString()} RPM`);
    lines.push('');
    lines.push('5 — LOAD-CELL READING AT N_req');
    lines.push('  T_load = T_spec · (ρ_tst / ρ_tgt)');
    lines.push(`         = ${f(inp.T_spec_N)} · ${f(res.rho_ratio_tst_tgt)}`);
    lines.push(`         = ${f(res.T_load_N)} N`);
    lines.push(`         = ${f(res.T_load_disp)} ${inp.dispU}`);
    lines.push('');
    lines.push(hr);
    lines.push(`FINAL  →  Spin at ${Math.round(res.N_req).toLocaleString()} RPM today`);
    lines.push(`          Load cell should read ${f(res.T_load_disp)} ${inp.dispU} (${f(res.T_load_N)} N)`);
  } else {
    lines.push('4 — AFFINITY-LAW SOLUTION (same RPM)');
    lines.push('  T_tgt = T_meas · (ρ_tgt / ρ_tst)');
    lines.push(`        = ${f(inp.T_measured_N)} · ${f(res.rho_ratio_tgt_tst)}`);
    lines.push(`        = ${f(res.T_sameRPM_N)} N`);
    lines.push(`        = ${f(res.T_pred_disp)} ${inp.dispU}`);
    lines.push('');
    lines.push(hr);
    lines.push(`FINAL  →  Predicted thrust at target: ${f(res.T_pred_disp)} ${inp.dispU}  (${f(res.T_sameRPM_N)} N)`);
    lines.push(`          at the same RPM (${f(inp.N_test)} RPM)`);
  }
  lines.push(hr);
  lines.push('transparent.tools · corrected-thrust');
  return lines.join('\n');
}

// Boot
document.addEventListener('DOMContentLoaded', ()=>{
  document.querySelectorAll('[data-ct-app]').forEach(buildApp);
});
})();
