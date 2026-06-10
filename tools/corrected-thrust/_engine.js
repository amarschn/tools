// Shared engine: units, atmosphere, affinity-law math.
// Used by all prototype shells in this folder.
(function(global){
'use strict';

const M_DRY=0.0289644, M_H2O=0.0180153, R_UNIV=8.31446;
const G0=9.80665, L_RATE=0.0065, T0_ISA=288.15, P0_ISA=101325;
const ISA_EXP=(G0*M_DRY)/(R_UNIV*L_RATE);

const UNITS = {
  thrust: { base:'N', list:[
    {sym:'N',   to:v=>v,                  from:v=>v},
    {sym:'lbf', to:v=>v*4.4482216152605,  from:v=>v/4.4482216152605},
    {sym:'kgf', to:v=>v*9.80665,          from:v=>v/9.80665},
    {sym:'oz',  to:v=>v*0.27801385095378, from:v=>v/0.27801385095378}
  ]},
  altitude: { base:'m', list:[
    {sym:'ft', to:v=>v*0.3048, from:v=>v/0.3048},
    {sym:'m',  to:v=>v,        from:v=>v}
  ]},
  temperature: { base:'K', list:[
    {sym:'°C', to:v=>v+273.15,         from:v=>v-273.15},
    {sym:'°F', to:v=>(v-32)*5/9+273.15,from:v=>(v-273.15)*9/5+32},
    {sym:'K',  to:v=>v,                from:v=>v}
  ]},
  tempDelta: { base:'K', list:[
    {sym:'°C', to:v=>v,     from:v=>v},
    {sym:'K',  to:v=>v,     from:v=>v},
    {sym:'°F', to:v=>v*5/9, from:v=>v*9/5}
  ]},
  pressure: { base:'Pa', list:[
    {sym:'kPa', to:v=>v*1000,      from:v=>v/1000},
    {sym:'Pa',  to:v=>v,           from:v=>v},
    {sym:'hPa', to:v=>v*100,       from:v=>v/100},
    {sym:'inHg',to:v=>v*3386.389,  from:v=>v/3386.389},
    {sym:'psi', to:v=>v*6894.757,  from:v=>v/6894.757}
  ]}
};

function convertToSI(value, kind, sym){
  const u = UNITS[kind].list.find(x=>x.sym===sym);
  return u ? u.to(value) : NaN;
}
function convertFromSI(value, kind, sym){
  const u = UNITS[kind].list.find(x=>x.sym===sym);
  return u ? u.from(value) : NaN;
}

const isaPressure   = h => P0_ISA * Math.pow(1 - L_RATE*h/T0_ISA, ISA_EXP);
const isaTemperature= h => T0_ISA - L_RATE*h;
function satVaporPressure(T_K){
  const Tc = T_K-273.15;
  return 610.94 * Math.exp(17.625*Tc/(Tc+243.04));
}
function moistAirDensity(P_Pa, T_K, RH_frac){
  const Pv = (RH_frac>0 ? RH_frac*satVaporPressure(T_K) : 0);
  const Pd = P_Pa - Pv;
  return (Pd*M_DRY + Pv*M_H2O) / (R_UNIV*T_K);
}

// side: {mode:'alt-T'|'PT'|'ISA', alt_m, T_K, dT_K, P_Pa, RH_frac}
function evaluateSide(side){
  let P,T,alt=null,dT=null,T_isa=null;
  if(side.mode==='alt-T'){ alt=side.alt_m; T=side.T_K; P=isaPressure(alt); }
  else if(side.mode==='PT'){ P=side.P_Pa; T=side.T_K; }
  else if(side.mode==='ISA'){ alt=side.alt_m; dT=side.dT_K; P=isaPressure(alt); T_isa=isaTemperature(alt); T=T_isa+dT; }
  const rho = moistAirDensity(P, T, side.RH_frac||0);
  const Psat = satVaporPressure(T);
  return {mode:side.mode, P, T, rho, RH:side.RH_frac||0, alt, dT, T_isa, Psat};
}

function solve(inp){
  // inp: {mode:'findRPM'|'predictThrust', T_measured_N, T_spec_N, N_test, displayUnit, test:side, target:side}
  const test = evaluateSide(inp.test);
  const tgt  = evaluateSide(inp.target);
  const rho_ratio_tgt_tst = tgt.rho/test.rho;
  const rho_ratio_tst_tgt = test.rho/tgt.rho;
  const T_sameRPM_N = inp.T_measured_N * rho_ratio_tgt_tst;
  const dispU = inp.displayUnit;
  const toDisp = N => convertFromSI(N,'thrust',dispU);

  const out = {test,tgt,rho_ratio_tgt_tst,rho_ratio_tst_tgt,T_sameRPM_N, displayUnit:dispU};

  if(inp.mode==='findRPM'){
    const ratio = (inp.T_spec_N/inp.T_measured_N)*rho_ratio_tst_tgt;
    out.N_req = inp.N_test * Math.sqrt(ratio);
    out.T_load_N = inp.T_spec_N * rho_ratio_tst_tgt;
    out.T_load_disp = toDisp(out.T_load_N);
    out.T_spec_disp = toDisp(inp.T_spec_N);
    out.ratio_inside_sqrt = ratio;
  } else {
    out.T_pred_disp = toDisp(T_sameRPM_N);
  }
  out.T_measured_disp = toDisp(inp.T_measured_N);
  out.T_sameRPM_disp  = toDisp(T_sameRPM_N);
  return out;
}

function fmt(x, sig=4){
  if(!isFinite(x)) return '—';
  if(x===0) return '0';
  const a=Math.abs(x);
  if(a>=1e5 || a<0.001) return x.toExponential(3);
  return parseFloat(x.toPrecision(sig)).toString();
}

// Higher-precision formatter for derivation substitutions, so that
// recomputing a result by hand from the printed intermediates reproduces
// the displayed answer. Used throughout the audit trail, analysis sheet,
// text export, and as cached values in the spreadsheet.
function fmt6(x){ return fmt(x, 6); }

// RPM is always presented the same way everywhere: rounded to a whole
// rev/min with thousands separators. One source of truth avoids the
// "headline says 23,262 but the equation says 23,260" rounding mismatch.
function fmtRPM(x){
  if(!isFinite(x)) return '—';
  return Math.round(x).toLocaleString('en-US');
}

global.CT_ENGINE = { UNITS, convertToSI, convertFromSI, isaPressure, isaTemperature,
  satVaporPressure, moistAirDensity, evaluateSide, solve, fmt, fmt6, fmtRPM };
})(window);
