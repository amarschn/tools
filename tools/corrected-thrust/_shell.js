// Shared shell: builds the input form and wires up calculation.
// Reads from CT_ENGINE. Each prototype provides its own CSS — DOM is identical.
(function(){
'use strict';
const E = window.CT_ENGINE;

// Modeling assumptions behind the affinity-law correction. Shared verbatim by
// the on-page explainer, the printable analysis sheet, and the text export so
// every copy of the result carries the same caveats.
const ASSUMPTIONS = [
  'Fixed geometry, single rotor — identical blades and diameter on both sides, so the D⁴ term cancels and only ρ and N change.',
  'Aerodynamic similarity — the thrust coefficient C_T is held constant. This needs a matched advance ratio (static/hover on both sides, or equal forward speed) and Reynolds-independent flow; it breaks down at low Reynolds number.',
  'Negligible compressibility — tip Mach number is low or unchanged. Large RPM swings that push the tip speed toward transonic will shift C_T and void the scaling.',
  'Rigid blades at fixed pitch — no aeroelastic twist or pitch change with load or speed.',
  'Quasi-steady, fully-developed flow — thrust tracks ρN² instantaneously, with no spool-up transient.',
  'Ideal-gas moist air — density from dry-air + water-vapor partial pressures, saturation pressure from August–Roche–Magnus, and the ISA troposphere model (valid to ~11 km).'
];

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
        <button type="button" class="ct-export-btn" data-export="xlsx">Download Excel</button>
        <button type="button" class="ct-export-btn ct-export-btn--alt" data-export="copy">Copy as text</button>
        <button type="button" class="ct-export-btn ct-export-btn--alt" data-export="print">Print / Save PDF</button>
      </div>
      <div class="ct-export-toast" aria-live="polite"></div>
    </div>
  </section>

  <section class="ct-analysis-sheet" aria-hidden="true"></section>

  <section class="ct-card ct-explain">
    <details>
      <summary>How it works</summary>
      <div class="ct-explain-body">
        <p><strong>1 · Governing relation.</strong> For one fixed-geometry rotor under aerodynamic similarity, thrust follows the affinity law
        <span class="ct-eq-inline">T = C_T · ρ · N² · D⁴</span>. The same blades fix D, and similarity fixes the thrust coefficient C_T, so this collapses to
        <span class="ct-eq-inline">T ∝ ρ · N²</span> — thrust is <strong>linear in air density</strong> but <strong>quadratic in RPM</strong>.</p>

        <p><strong>2 · Calibrate from the test run.</strong> The measured point pins the constant:
        <span class="ct-eq-inline">T_meas = k · ρ_tst · N_test²</span>, so
        <span class="ct-eq-inline">k · ρ_tst = T_meas / N_test²</span>.</p>

        <p><strong>3 · Required RPM (find-RPM mode).</strong> We want the same rotor to make the spec thrust in the <em>target</em> air,
        <span class="ct-eq-inline">T_spec = k · ρ_tgt · N_req²</span>. Substituting k and solving for N_req:</p>
        <p class="ct-eq">N_req² = N_test² · (T_spec / T_meas) · (ρ_tst / ρ_tgt)</p>
        <p class="ct-eq">N_req = N_test · √[ (T_spec / T_meas) · (ρ_tst / ρ_tgt) ]</p>

        <p><strong>Why the density ratio sits inside the √.</strong> Thrust is quadratic in RPM but only linear in density
        (<span class="ct-eq-inline">T ∝ ρN²</span>). Inverting for RPM gives <span class="ct-eq-inline">N ∝ √(T/ρ)</span>, so <em>every</em>
        factor that scales the thrust balance linearly — the thrust ratio you are chasing <em>and</em> the density change between cells —
        emerges under the <em>same</em> square root. Physically: thinner target air (altitude) makes
        <span class="ct-eq-inline">ρ_tst / ρ_tgt &gt; 1</span> and raises N_req, but only as the <em>square root</em> of the density
        deficit, because doubling RPM quadruples thrust.</p>

        <p><strong>4 · Load-cell reading.</strong> At that single N_req the rotor sees two densities, so
        <span class="ct-eq-inline">T_load / T_spec = ρ_tst / ρ_tgt</span>:</p>
        <p class="ct-eq">T_load = T_spec · (ρ_tst / ρ_tgt)</p>
        <p>The cell reads <em>more</em> than the spec whenever the test air is denser than the target air.</p>

        <p><strong>Predict-thrust mode</strong> holds RPM fixed and only swaps environment, so it is purely linear in density — no square root:</p>
        <p class="ct-eq">T_tgt = T_meas · (ρ_tgt / ρ_tst)</p>

        <p><strong>5 · Air density.</strong> Moist air as an ideal mixture of dry air and water vapor:
        <span class="ct-eq-inline">ρ = ((P − P_v)·M_d + P_v·M_v) / (R·T)</span>, with
        <span class="ct-eq-inline">P_v = RH · 610.94·exp(17.625·T_C/(T_C+243.04))</span> Pa (August–Roche–Magnus).
        ISA troposphere (0–11 km): <span class="ct-eq-inline">T(h) = 288.15 − 0.0065h</span>,
        <span class="ct-eq-inline">P(h) = 101325·(1 − 0.0065h/288.15)^5.2558</span>.</p>

        <p><strong>Assumptions &amp; limits.</strong> Every result rides on these — read them before trusting a number:</p>
        <ul class="ct-assume">${ASSUMPTIONS.map(a=>`<li>${a}</li>`).join('')}</ul>
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
      } else if(kind==='xlsx'){
        try {
          const {bytes, filename} = buildXlsx(host._ct_last);
          downloadBytes(bytes, filename, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
          showExportToast(host, 'Excel workbook downloaded');
        } catch(err){
          console.error(err);
          showExportToast(host, 'Excel export failed — see console');
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
  if(ev.RH>0) parts.push(`RH ${f(ev.RH*100)}%, P_v ${E.fmt6(ev.RH*ev.Psat)} Pa`);
  parts.push(`ρ = ${E.fmt6(ev.rho)} kg/m³`);
  return parts.join(' · ');
}

function calculate(host){
  const f = E.fmt, f6 = E.fmt6, rpm = E.fmtRPM;
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
  auditHTML += `<div class="ct-step"><div class="ct-step-name">Density ratio</div><div class="ct-step-eq">ρ_tgt / ρ_tst = ${f6(res.tgt.rho)} / ${f6(res.test.rho)} = <strong>${f6(res.rho_ratio_tgt_tst)}</strong></div></div>`;

  if(mode==='predictThrust'){
    primaryHTML = `
      <div class="ct-primary-label">Predicted thrust at target (same RPM)</div>
      <div class="ct-primary-value">${f(res.T_pred_disp)}<span class="ct-primary-unit">${dispU}</span></div>
      <div class="ct-primary-sub">${f(res.T_sameRPM_N)} N · at ${f(N_test)} RPM</div>`;
    rowsHTML += rowHTML('Predicted thrust @ target, same RPM', `${f(res.T_pred_disp)} ${dispU}`);
    rowsHTML += rowHTML('  (in N)', `${f6(res.T_sameRPM_N)} N`);
    rowsHTML += rowHTML('Density ratio ρ_tgt/ρ_tst', f6(res.rho_ratio_tgt_tst));
    rowsHTML += rowHTML('Test density', `${f6(res.test.rho)} kg/m³`);
    rowsHTML += rowHTML('Target density', `${f6(res.tgt.rho)} kg/m³`);
    auditHTML += `<div class="ct-step"><div class="ct-step-name">Affinity-law (same RPM)</div>
      <div class="ct-step-eq">T_tgt = T_meas · (ρ_tgt / ρ_tst) = ${f6(T_measured_N)} · ${f6(res.rho_ratio_tgt_tst)} = <strong>${f6(res.T_sameRPM_N)} N</strong> (${f(res.T_pred_disp)} ${dispU})</div></div>`;
  } else {
    primaryHTML = `
      <div class="ct-primary-label">Spin at this RPM today</div>
      <div class="ct-primary-value">${rpm(res.N_req)}<span class="ct-primary-unit">RPM</span></div>
      <div class="ct-primary-sub">Load cell should read <strong>${f(res.T_load_disp)} ${dispU}</strong></div>`;
    rowsHTML += rowHTML('Required RPM', `${rpm(res.N_req)} RPM`);
    rowsHTML += rowHTML('Load-cell reading @ N_req', `${f(res.T_load_disp)} ${dispU}`);
    rowsHTML += rowHTML('  (in N)', `${f6(res.T_load_N)} N`);
    rowsHTML += rowHTML('Same-RPM prediction', `${f(res.T_sameRPM_disp)} ${dispU}`);
    rowsHTML += rowHTML('Density ratio ρ_tst/ρ_tgt', f6(res.rho_ratio_tst_tgt));
    rowsHTML += rowHTML('Test density', `${f6(res.test.rho)} kg/m³`);
    rowsHTML += rowHTML('Target density', `${f6(res.tgt.rho)} kg/m³`);
    auditHTML += `<div class="ct-step"><div class="ct-step-name">Required RPM</div>
      <div class="ct-step-eq">N_req = N_test · √[ (T_spec / T_meas) · (ρ_tst / ρ_tgt) ]<br>= ${f6(N_test)} · √[ (${f6(T_spec_N)} / ${f6(T_measured_N)}) · ${f6(res.rho_ratio_tst_tgt)} ] = ${f6(N_test)} · √(${f6(res.ratio_inside_sqrt)}) = ${f6(res.N_req)} ≈ <strong>${rpm(res.N_req)} RPM</strong></div></div>`;
    auditHTML += `<div class="ct-step"><div class="ct-step-name">Load-cell reading</div>
      <div class="ct-step-eq">T_load = T_spec · (ρ_tst / ρ_tgt) = ${f6(T_spec_N)} · ${f6(res.rho_ratio_tst_tgt)} = <strong>${f6(res.T_load_N)} N</strong> (${f(res.T_load_disp)} ${dispU})</div></div>`;
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
  rows.push(['Test RPM',        `${raw.n_test} RPM`]);
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

// ISA barometric exponent gM_d/(RL); ~5.25588. Shown numerically so the
// pressure step is reproducible without re-deriving the constant.
const ISA_EXP = (9.80665*0.0289644)/(8.31446*0.0065);

function sideEqBlock(label, ev){
  const f6 = E.fmt6;
  const Pv = ev.RH>0 ? ev.RH*ev.Psat : 0;
  const Pd = ev.P - Pv;
  let setup = '';
  if(ev.mode==='alt-T'){
    setup = `\\[ P = P_{0}\\left(1 - \\dfrac{Lh}{T_{0}}\\right)^{\\!gM_{d}/(RL)} = 101325\\left(1 - \\dfrac{(0.0065)(${f6(ev.alt)})}{288.15}\\right)^{\\!${f6(ISA_EXP)}} = ${f6(ev.P)}\\ \\text{Pa},\\quad T = ${f6(ev.T-273.15)}\\ {}^{\\circ}\\!\\text{C} \\]`;
  } else if(ev.mode==='PT'){
    setup = `\\[ P = ${f6(ev.P)}\\ \\text{Pa},\\quad T = ${f6(ev.T-273.15)}\\ {}^{\\circ}\\!\\text{C} \\]`;
  } else {
    setup = `\\[ P(h) = 101325\\left(1 - \\dfrac{(0.0065)(${f6(ev.alt)})}{288.15}\\right)^{\\!${f6(ISA_EXP)}} = ${f6(ev.P)}\\ \\text{Pa} \\] \\[ T = T_{\\text{ISA}}(h) + \\Delta T = ${f6(ev.T_isa-273.15)} + ${f6(ev.dT)} = ${f6(ev.T-273.15)}\\ {}^{\\circ}\\!\\text{C} \\]`;
  }
  const humidityRow = ev.RH>0
    ? `\\[ P_{\\text{sat}}(T) = 610.94\\,\\exp\\!\\left(\\dfrac{17.625\\,T_{C}}{T_{C}+243.04}\\right) = ${f6(ev.Psat)}\\ \\text{Pa},\\quad P_{v} = \\phi\\, P_{\\text{sat}} = ${f6(Pv)}\\ \\text{Pa} \\]`
    : `<div class="as-note">Humidity neglected (RH = 0, so \\(P_v = 0\\)).</div>`;
  return `
    <div class="as-side">
      <h4>${label}</h4>
      ${setup}
      ${humidityRow}
      \\[ \\rho = \\dfrac{(P - P_{v})\\,M_{d} + P_{v}\\,M_{v}}{R\\,T} = \\dfrac{(${f6(Pd)})(0.0289644) + (${f6(Pv)})(0.0180153)}{(8.31446)(${f6(ev.T)})} = \\mathbf{${f6(ev.rho)}}\\ \\text{kg/m}^{3} \\]
    </div>`;
}

function methodSection(mode){
  const govern = `<p class="as-note">Fixed-geometry thrust under aerodynamic similarity follows \\( T = C_T\\,\\rho\\,N^{2}D^{4} \\). Identical blades fix \\(D\\) and \\(C_T\\), leaving \\( T \\propto \\rho N^{2} \\) — linear in density, quadratic in RPM. The test run pins the constant: \\( k\\rho_{\\text{tst}} = T_{\\text{meas}}/N_{\\text{test}}^{2} \\).</p>`;
  let body;
  if(mode==='findRPM'){
    body = `${govern}
      \\[ T_{\\text{spec}} = k\\,\\rho_{\\text{tgt}}N_{\\text{req}}^{2} \\;\\Rightarrow\\; N_{\\text{req}} = N_{\\text{test}}\\sqrt{ \\dfrac{T_{\\text{spec}}}{T_{\\text{meas}}} \\cdot \\dfrac{\\rho_{\\text{tst}}}{\\rho_{\\text{tgt}}} } \\]
      <p class="as-note"><strong>Why the density ratio is under the root:</strong> thrust is quadratic in RPM but linear in density, so inverting \\( T \\propto \\rho N^{2} \\) gives \\( N \\propto \\sqrt{T/\\rho} \\) — the thrust ratio and the density change share the <em>same</em> square root. Thinner target air raises \\(N_{\\text{req}}\\) only as the square root of the density deficit. The load cell, spun at \\(N_{\\text{req}}\\) in test air, then reads \\( T_{\\text{load}} = T_{\\text{spec}}\\,\\rho_{\\text{tst}}/\\rho_{\\text{tgt}} \\).</p>`;
  } else {
    body = `${govern}
      <p class="as-note">Holding RPM fixed and changing only the environment makes thrust scale <em>linearly</em> with density — no square root: \\( T_{\\text{tgt}} = T_{\\text{meas}}\\,\\rho_{\\text{tgt}}/\\rho_{\\text{tst}} \\).</p>`;
  }
  return `<div class="as-section"><h3>Method — affinity-law scaling</h3>${body}</div>
    <div class="as-section"><h3>Assumptions &amp; limits</h3>
      <ul class="as-assume">${ASSUMPTIONS.map(a=>`<li>${a}</li>`).join('')}</ul>
    </div>`;
}

function buildAnalysisSheet(inp, res){
  const f = E.fmt, f6 = E.fmt6, rpm = E.fmtRPM;
  const now = new Date();
  const stamp = now.toISOString().slice(0,10) + ' ' + now.toTimeString().slice(0,5);
  const modeTitle = inp.mode==='findRPM' ? 'Required RPM for target thrust spec' : 'Predicted thrust at target (same RPM)';

  let solution = '';
  if(inp.mode==='findRPM'){
    solution = `
      <div class="as-section"><h3>4 — Solve for required RPM</h3>
        \\[ N_{\\text{req}} = N_{\\text{test}} \\sqrt{ \\dfrac{T_{\\text{spec}}}{T_{\\text{meas}}} \\cdot \\dfrac{\\rho_{\\text{tst}}}{\\rho_{\\text{tgt}}} } \\]
        \\[ N_{\\text{req}} = ${f6(inp.N_test)} \\cdot \\sqrt{ \\dfrac{${f6(inp.T_spec_N)}}{${f6(inp.T_measured_N)}} \\cdot ${f6(res.rho_ratio_tst_tgt)} } = ${f6(inp.N_test)} \\cdot \\sqrt{${f6(res.ratio_inside_sqrt)}} = ${f6(res.N_req)} \\approx \\mathbf{${rpm(res.N_req)}\\ \\text{RPM}} \\]
      </div>
      <div class="as-section"><h3>5 — Load-cell reading at that RPM today</h3>
        \\[ T_{\\text{load}} = T_{\\text{spec}} \\cdot \\dfrac{\\rho_{\\text{tst}}}{\\rho_{\\text{tgt}}} = ${f6(inp.T_spec_N)} \\cdot ${f6(res.rho_ratio_tst_tgt)} = \\mathbf{${f6(res.T_load_N)}\\ \\text{N}} = \\mathbf{${f6(res.T_load_disp)}\\ ${inp.dispU}} \\]
      </div>
      <div class="as-final">
        <div class="as-final-label">FINAL — Spin at this RPM today</div>
        <div class="as-final-value">${rpm(res.N_req)} <span class="as-final-unit">RPM</span></div>
        <div class="as-final-sub">Load cell should read <strong>${f(res.T_load_disp)} ${inp.dispU}</strong> (${f6(res.T_load_N)} N)</div>
      </div>`;
  } else {
    solution = `
      <div class="as-section"><h3>4 — Affinity-law solution (same RPM)</h3>
        \\[ T_{\\text{tgt}} = T_{\\text{meas}} \\cdot \\dfrac{\\rho_{\\text{tgt}}}{\\rho_{\\text{tst}}} = ${f6(inp.T_measured_N)} \\cdot ${f6(res.rho_ratio_tgt_tst)} = \\mathbf{${f6(res.T_sameRPM_N)}\\ \\text{N}} = \\mathbf{${f6(res.T_pred_disp)}\\ ${inp.dispU}} \\]
      </div>
      <div class="as-final">
        <div class="as-final-label">FINAL — Predicted thrust at target (same RPM)</div>
        <div class="as-final-value">${f(res.T_pred_disp)} <span class="as-final-unit">${inp.dispU}</span></div>
        <div class="as-final-sub">${f6(res.T_sameRPM_N)} N · at ${rpm(inp.N_test)} RPM</div>
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

    ${methodSection(inp.mode)}

    <footer class="as-foot">
      <div>Affinity laws assume constant geometry and Reynolds-similar flow.</div>
      <div>transparent.tools · corrected-thrust</div>
    </footer>`;
}

// ---------- Text export (markdown-ish, Unicode symbols) ----------
// Every quantity is printed at 6 significant figures and every formula is
// shown symbolically and then with all numbers substituted, so the report
// reproduces on a hand calculator with no hidden rounding or substitutions.
function densityDerivationLines(label, ev){
  const f6 = E.fmt6;
  const Pv = ev.RH>0 ? ev.RH*ev.Psat : 0;
  const Pd = ev.P - Pv;
  const Tc = ev.T - 273.15;
  const lines = [`  ${label}:`];
  if(ev.mode==='alt-T'){
    lines.push(`     P     = 101325·(1 − 0.0065·h/288.15)^${f6(ISA_EXP)}`);
    lines.push(`           = 101325·(1 − 0.0065·${f6(ev.alt)}/288.15)^${f6(ISA_EXP)}`);
    lines.push(`           = ${f6(ev.P)} Pa`);
    lines.push(`     T     = ${f6(Tc)} °C  (${f6(ev.T)} K)`);
  } else if(ev.mode==='PT'){
    lines.push(`     P     = ${f6(ev.P)} Pa`);
    lines.push(`     T     = ${f6(Tc)} °C  (${f6(ev.T)} K)`);
  } else {
    lines.push(`     P     = 101325·(1 − 0.0065·h/288.15)^${f6(ISA_EXP)}`);
    lines.push(`           = 101325·(1 − 0.0065·${f6(ev.alt)}/288.15)^${f6(ISA_EXP)}`);
    lines.push(`           = ${f6(ev.P)} Pa`);
    lines.push(`     T     = T_ISA(h) + ΔT = ${f6(ev.T_isa-273.15)} + ${f6(ev.dT)} = ${f6(Tc)} °C  (${f6(ev.T)} K)`);
  }
  if(ev.RH>0){
    lines.push(`     P_sat = 610.94·exp(17.625·${f6(Tc)}/(${f6(Tc)}+243.04)) = ${f6(ev.Psat)} Pa`);
    lines.push(`     P_v   = RH·P_sat = ${f6(ev.RH)}·${f6(ev.Psat)} = ${f6(Pv)} Pa`);
  } else {
    lines.push(`     P_v   = 0  (humidity neglected, RH = 0)`);
  }
  lines.push(`     ρ     = ((P − P_v)·M_d + P_v·M_v) / (R·T)`);
  lines.push(`           = ((${f6(ev.P)} − ${f6(Pv)})·0.0289644 + ${f6(Pv)}·0.0180153) / (8.31446·${f6(ev.T)})`);
  lines.push(`           = (${f6(Pd)}·0.0289644 + ${f6(Pv)}·0.0180153) / ${f6(8.31446*ev.T)}`);
  lines.push(`           = ${f6(ev.rho)} kg/m³`);
  return lines;
}

function buildTextExport(last){
  const f = E.fmt, f6 = E.fmt6, rpm = E.fmtRPM;
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
  lines.push('2 — AIR DENSITY  (moist air, August–Roche–Magnus vapor pressure)');
  lines.push('  Constants: M_d = 0.0289644, M_v = 0.0180153 kg/mol, R = 8.31446 J/(mol·K)');
  lines.push('             ISA: T0 = 288.15 K, L = 0.0065 K/m, P0 = 101325 Pa, exp = gM_d/(RL) = ' + f6(ISA_EXP));
  for(const [label, ev] of [['Test cell', res.test], ['Target environment', res.tgt]]){
    for(const ln of densityDerivationLines(label, ev)) lines.push(ln);
  }
  lines.push('');
  lines.push('3 — DENSITY RATIO');
  lines.push(`  ρ_tgt / ρ_tst = ${f6(res.tgt.rho)} / ${f6(res.test.rho)} = ${f6(res.rho_ratio_tgt_tst)}`);
  lines.push(`  ρ_tst / ρ_tgt = ${f6(res.test.rho)} / ${f6(res.tgt.rho)} = ${f6(res.rho_ratio_tst_tgt)}`);
  lines.push('');
  if(inp.mode==='findRPM'){
    lines.push('4 — REQUIRED RPM');
    lines.push('  N_req = N_test · √[ (T_spec / T_meas) · (ρ_tst / ρ_tgt) ]');
    lines.push(`        = ${f6(inp.N_test)} · √[ (${f6(inp.T_spec_N)} / ${f6(inp.T_measured_N)}) · ${f6(res.rho_ratio_tst_tgt)} ]`);
    lines.push(`        = ${f6(inp.N_test)} · √(${f6(res.ratio_inside_sqrt)})`);
    lines.push(`        = ${f6(res.N_req)} RPM`);
    lines.push(`        ≈ ${rpm(res.N_req)} RPM`);
    lines.push('');
    lines.push('5 — LOAD-CELL READING AT N_req');
    lines.push('  T_load = T_spec · (ρ_tst / ρ_tgt)');
    lines.push(`         = ${f6(inp.T_spec_N)} · ${f6(res.rho_ratio_tst_tgt)}`);
    lines.push(`         = ${f6(res.T_load_N)} N`);
    lines.push(`         = ${f6(res.T_load_disp)} ${inp.dispU}`);
    lines.push('');
    lines.push(hr);
    lines.push(`FINAL  →  Spin at ${rpm(res.N_req)} RPM today`);
    lines.push(`          Load cell should read ${f6(res.T_load_disp)} ${inp.dispU} (${f6(res.T_load_N)} N)`);
  } else {
    lines.push('4 — AFFINITY-LAW SOLUTION (same RPM)');
    lines.push('  T_tgt = T_meas · (ρ_tgt / ρ_tst)');
    lines.push(`        = ${f6(inp.T_measured_N)} · ${f6(res.rho_ratio_tgt_tst)}`);
    lines.push(`        = ${f6(res.T_sameRPM_N)} N`);
    lines.push(`        = ${f6(res.T_pred_disp)} ${inp.dispU}`);
    lines.push('');
    lines.push(hr);
    lines.push(`FINAL  →  Predicted thrust at target: ${f6(res.T_pred_disp)} ${inp.dispU}  (${f6(res.T_sameRPM_N)} N)`);
    lines.push(`          at the same RPM (${rpm(inp.N_test)} RPM)`);
  }
  lines.push('');
  lines.push(hr);
  lines.push('DERIVATION & ASSUMPTIONS');
  lines.push('  Affinity law (fixed geometry, similar flow):  T = C_T·ρ·N²·D⁴  →  T ∝ ρ·N²');
  lines.push('  Test run pins the constant:  k·ρ_tst = T_meas / N_test²');
  if(inp.mode==='findRPM'){
    lines.push('  Target spec:  T_spec = k·ρ_tgt·N_req²');
    lines.push('     ⇒  N_req = N_test · √[ (T_spec/T_meas) · (ρ_tst/ρ_tgt) ]');
    lines.push('  The density ratio is INSIDE the √ because thrust is quadratic in RPM but only');
    lines.push('  linear in density: inverting T ∝ ρN² gives N ∝ √(T/ρ), so the thrust ratio and');
    lines.push('  the density change come out under the same square root.');
    lines.push('  Load-cell reading at N_req (in test air):  T_load = T_spec · (ρ_tst/ρ_tgt)');
  } else {
    lines.push('  Same rotor, same RPM, only the environment changes ⇒ purely linear in density');
    lines.push('  (no square root):  T_tgt = T_meas · (ρ_tgt/ρ_tst)');
  }
  lines.push('');
  lines.push('  Assumptions & limits:');
  for(let i=0;i<ASSUMPTIONS.length;i++) lines.push(`    ${i+1}. ${ASSUMPTIONS[i]}`);
  lines.push('');
  lines.push(hr);
  lines.push('transparent.tools · corrected-thrust');
  return lines.join('\n');
}

// ---------- Excel (.xlsx) export ----------
// A live workbook: inputs are plain cells and every result is a real Excel
// formula referencing them, so editing an input recomputes the whole chain
// (ISA pressure, moist-air density, affinity-law solve). Built with no
// dependencies — a store-only ZIP of the minimal OOXML parts.

const XLSX_NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main';

function colLetter(c){ let s=''; c++; while(c>0){ const m=(c-1)%26; s=String.fromCharCode(65+m)+s; c=Math.floor((c-1)/26);} return s; }
function a1(r,c){ return colLetter(c)+(r+1); }            // r,c zero-based
function xmlEsc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function numStr(x){ return (isFinite(x) ? x : 0).toString(); }

// Worksheet model: a list of rows; each row is [labelCell?, valueCell?, unit?, note?].
// A value cell is {n:number} | {f:'=…with @names…', cache:number} | {s:'text'} | null.
function buildSheetModel(last){
  const {inp, res} = last;
  const rows = [];           // each: {cells:[{col,kind,...}]}
  const ref = {};            // name -> A1
  let r = 0;

  // helper: push a row of column cells; register names; returns row index
  function row(cells){
    const rec = {r, cells:[]};
    for(const c of cells){
      if(!c || c.v===undefined && c.f===undefined && c.s===undefined) continue;
      rec.cells.push(c);
      if(c.name) ref[c.name] = a1(r, c.col);
    }
    rows.push(rec);
    return r++;
  }
  const L = (col,text)=>({col, s:text});                       // string cell
  const N = (col,value,name)=>({col, v:value, name});          // number cell
  const F = (col,formula,cache,name)=>({col, f:formula, cache, name}); // formula cell
  function blank(){ row([]); }
  function head(text){ row([L(0,text)]); }

  const modeLabel = inp.mode==='findRPM' ? 'Find RPM for target thrust spec'
                                         : 'Predict thrust at target (same RPM)';
  const stamp = new Date().toISOString().slice(0,10) + ' ' + new Date().toTimeString().slice(0,5);

  row([L(0,'Corrected Thrust & RPM — Calculation Workbook')]);
  row([L(0,'Generated'), L(1, stamp)]);
  row([L(0,'Mode'), L(1, modeLabel)]);
  row([L(0,'Edit any INPUT cell (yellow path: SI base units) and results recompute.')]);
  blank();

  head('INPUTS  (SI base units)');
  row([L(0,'Measured thrust  T_meas'), N(1, inp.T_measured_N, 'T_meas'), L(2,'N')]);
  row([L(0,'Test RPM  N_test'),        N(1, inp.N_test, 'N_test'),       L(2,'rev/min')]);
  if(inp.mode==='findRPM')
    row([L(0,'Target thrust spec  T_spec'), N(1, inp.T_spec_N, 'T_spec'), L(2,'N')]);
  blank();

  // Per-side atmosphere + density derivation
  function sideBlock(title, ev, sfx){
    const Pv = ev.RH>0 ? ev.RH*ev.Psat : 0;
    head(title);
    if(ev.mode==='alt-T'){
      row([L(0,'Altitude  h'),       N(1, ev.alt, 'h_'+sfx), L(2,'m')]);
      row([L(0,'Temperature  T'),    N(1, ev.T,   'T_'+sfx), L(2,'K'), L(3,'input')]);
      row([L(0,'Pressure  P (ISA)'), F(1, '=101325*(1-0.0065*@h_'+sfx+'/288.15)^'+numStr(ISA_EXP), ev.P, 'P_'+sfx), L(2,'Pa'),
           L(3,'P0·(1−L·h/T0)^(gM_d/RL)')]);
    } else if(ev.mode==='PT'){
      row([L(0,'Pressure  P'),    N(1, ev.P, 'P_'+sfx), L(2,'Pa')]);
      row([L(0,'Temperature  T'), N(1, ev.T, 'T_'+sfx), L(2,'K')]);
    } else { // ISA
      row([L(0,'Altitude  h'),       N(1, ev.alt, 'h_'+sfx),  L(2,'m')]);
      row([L(0,'ΔT from ISA'),       N(1, ev.dT,  'dT_'+sfx), L(2,'K')]);
      row([L(0,'Pressure  P (ISA)'), F(1, '=101325*(1-0.0065*@h_'+sfx+'/288.15)^'+numStr(ISA_EXP), ev.P, 'P_'+sfx), L(2,'Pa'),
           L(3,'P0·(1−L·h/T0)^(gM_d/RL)')]);
      row([L(0,'Temperature  T'),    F(1, '=(288.15-0.0065*@h_'+sfx+')+@dT_'+sfx, ev.T, 'T_'+sfx), L(2,'K'),
           L(3,'T_ISA(h)+ΔT')]);
    }
    row([L(0,'Relative humidity  RH'), N(1, ev.RH, 'RH_'+sfx), L(2,'fraction 0–1')]);
    row([L(0,'  T in °C'),       F(1, '=@T_'+sfx+'-273.15', ev.T-273.15, 'Tc_'+sfx), L(2,'°C')]);
    row([L(0,'  P_sat(T)'),      F(1, '=610.94*EXP(17.625*@Tc_'+sfx+'/(@Tc_'+sfx+'+243.04))', ev.Psat, 'Psat_'+sfx), L(2,'Pa'),
         L(3,'August–Roche–Magnus')]);
    row([L(0,'  P_v = RH·P_sat'),F(1, '=@RH_'+sfx+'*@Psat_'+sfx, Pv, 'Pv_'+sfx), L(2,'Pa')]);
    row([L(0,'  P_d = P − P_v'), F(1, '=@P_'+sfx+'-@Pv_'+sfx, ev.P-Pv, 'Pd_'+sfx), L(2,'Pa')]);
    row([L(0,'  ρ = (P_d·M_d + P_v·M_v)/(R·T)'),
         F(1, '=(@Pd_'+sfx+'*0.0289644+@Pv_'+sfx+'*0.0180153)/(8.31446*@T_'+sfx+')', ev.rho, 'rho_'+sfx), L(2,'kg/m³')]);
    blank();
  }
  sideBlock('TEST CELL  ('+CMODE_LABEL[inp.test.mode]+')',  res.test, 'test');
  sideBlock('TARGET  ('+CMODE_LABEL[inp.target.mode]+')',    res.tgt,  'tgt');

  head('DENSITY RATIO');
  row([L(0,'ρ_tgt / ρ_tst'), F(1, '=@rho_tgt/@rho_test', res.rho_ratio_tgt_tst, 'rr_tgt_tst')]);
  row([L(0,'ρ_tst / ρ_tgt'), F(1, '=@rho_test/@rho_tgt', res.rho_ratio_tst_tgt, 'rr_tst_tgt')]);
  blank();

  if(inp.mode==='findRPM'){
    head('SOLUTION — Required RPM');
    row([L(0,'Ratio  (T_spec/T_meas)·(ρ_tst/ρ_tgt)'),
         F(1, '=(@T_spec/@T_meas)*@rr_tst_tgt', res.ratio_inside_sqrt, 'ratio')]);
    row([L(0,'Required RPM  N_req = N_test·√ratio'),
         F(1, '=@N_test*SQRT(@ratio)', res.N_req, 'N_req'), L(2,'rev/min')]);
    row([L(0,'Load-cell reading  T_load = T_spec·(ρ_tst/ρ_tgt)'),
         F(1, '=@T_spec*@rr_tst_tgt', res.T_load_N, 'T_load'), L(2,'N')]);
  } else {
    head('SOLUTION — Predicted thrust (same RPM)');
    row([L(0,'T_tgt = T_meas·(ρ_tgt/ρ_tst)'),
         F(1, '=@T_meas*@rr_tgt_tst', res.T_sameRPM_N, 'T_pred'), L(2,'N')]);
  }
  blank();
  row([L(0,'transparent.tools · corrected-thrust')]);

  return {rows, ref};
}

function sheetXml(model){
  const {rows, ref} = model;
  const resolve = f => f.replace(/@([A-Za-z0-9_]+)/g, (m,name)=>{
    if(!ref[name]) throw new Error('xlsx: unresolved cell reference @'+name);
    return ref[name];
  });
  let body = '';
  for(const rec of rows){
    let cellsXml = '';
    for(const c of rec.cells){
      const r = a1(rec.r, c.col);
      if(c.s!==undefined){
        cellsXml += `<c r="${r}" t="inlineStr"><is><t xml:space="preserve">${xmlEsc(c.s)}</t></is></c>`;
      } else if(c.f!==undefined){
        cellsXml += `<c r="${r}"><f>${xmlEsc(resolve(c.f).slice(1))}</f><v>${numStr(c.cache)}</v></c>`;
      } else if(c.v!==undefined){
        cellsXml += `<c r="${r}"><v>${numStr(c.v)}</v></c>`;
      }
    }
    body += `<row r="${rec.r+1}">${cellsXml}</row>`;
  }
  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>`
    + `<worksheet xmlns="${XLSX_NS}">`
    + `<cols><col min="1" max="1" width="40" customWidth="1"/><col min="2" max="2" width="20" customWidth="1"/>`
    + `<col min="3" max="3" width="14" customWidth="1"/><col min="4" max="4" width="30" customWidth="1"/></cols>`
    + `<sheetData>${body}</sheetData></worksheet>`;
}

// --- store-only ZIP writer (CRC32 + local/central headers) ---
const CRC_TABLE = (()=>{ const t=new Uint32Array(256); for(let n=0;n<256;n++){ let c=n; for(let k=0;k<8;k++) c = (c&1)?(0xEDB88320^(c>>>1)):(c>>>1); t[n]=c>>>0;} return t; })();
function crc32(bytes){ let c=0xFFFFFFFF; for(let i=0;i<bytes.length;i++) c = CRC_TABLE[(c^bytes[i])&0xFF]^(c>>>8); return (c^0xFFFFFFFF)>>>0; }

function zipStore(entries){
  const enc = new TextEncoder();
  const chunks = [];
  const central = [];
  let offset = 0;
  const u16 = v => [v&0xFF,(v>>>8)&0xFF];
  const u32 = v => [v&0xFF,(v>>>8)&0xFF,(v>>>16)&0xFF,(v>>>24)&0xFF];
  for(const e of entries){
    const nameBytes = enc.encode(e.name);
    const data = e.data;
    const crc = crc32(data);
    const local = [].concat(
      u32(0x04034b50), u16(20), u16(0), u16(0), u16(0), u16(0),
      u32(crc), u32(data.length), u32(data.length), u16(nameBytes.length), u16(0));
    chunks.push(new Uint8Array(local), nameBytes, data);
    const localLen = local.length + nameBytes.length + data.length;
    central.push({nameBytes, crc, len:data.length, offset});
    offset += localLen;
  }
  const cdStart = offset;
  const cdChunks = [];
  for(const c of central){
    const h = [].concat(
      u32(0x02014b50), u16(20), u16(20), u16(0), u16(0), u16(0), u16(0),
      u32(c.crc), u32(c.len), u32(c.len), u16(c.nameBytes.length), u16(0), u16(0),
      u16(0), u16(0), u32(0), u32(c.offset));
    cdChunks.push(new Uint8Array(h), c.nameBytes);
    offset += h.length + c.nameBytes.length;
  }
  const cdSize = offset - cdStart;
  const eocd = [].concat(
    u32(0x06054b50), u16(0), u16(0), u16(central.length), u16(central.length),
    u32(cdSize), u32(cdStart), u16(0));
  const all = [...chunks, ...cdChunks, new Uint8Array(eocd)];
  let total = 0; for(const a of all) total += a.length;
  const out = new Uint8Array(total);
  let p = 0; for(const a of all){ out.set(a, p); p += a.length; }
  return out;
}

function buildXlsx(last){
  const enc = new TextEncoder();
  const sheet = sheetXml(buildSheetModel(last));
  const parts = {
    '[Content_Types].xml':
      `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>`
      + `<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">`
      + `<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>`
      + `<Default Extension="xml" ContentType="application/xml"/>`
      + `<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>`
      + `<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>`
      + `</Types>`,
    '_rels/.rels':
      `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>`
      + `<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">`
      + `<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>`
      + `</Relationships>`,
    'xl/workbook.xml':
      `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>`
      + `<workbook xmlns="${XLSX_NS}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">`
      + `<sheets><sheet name="Corrected Thrust" sheetId="1" r:id="rId1"/></sheets>`
      + `<calcPr calcId="0" fullCalcOnLoad="1"/>`
      + `</workbook>`,
    'xl/_rels/workbook.xml.rels':
      `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>`
      + `<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">`
      + `<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>`
      + `</Relationships>`,
    'xl/worksheets/sheet1.xml': sheet
  };
  const entries = Object.keys(parts).map(name => ({name, data: enc.encode(parts[name])}));
  const bytes = zipStore(entries);
  const stamp = new Date().toISOString().slice(0,10);
  const filename = `corrected-thrust_${last.inp.mode}_${stamp}.xlsx`;
  return {bytes, filename};
}

function downloadBytes(bytes, filename, mime){
  const blob = new Blob([bytes], {type: mime});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click();
  setTimeout(()=>{ URL.revokeObjectURL(url); a.remove(); }, 0);
}

// Expose pure builders for headless validation/tests.
window.CT_EXPORT = { buildXlsx, buildTextExport, buildAnalysisSheet, buildSheetModel, sheetXml, zipStore, crc32 };

// Boot
document.addEventListener('DOMContentLoaded', ()=>{
  document.querySelectorAll('[data-ct-app]').forEach(buildApp);
});
})();
