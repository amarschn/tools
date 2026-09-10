export const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
export function significant(value, figures = 3) {
  if (!Number.isFinite(value)) return 'Unreported';
  if (value === 0) return '0';
  const rounded = Number(value.toPrecision(Math.max(1, Math.min(15, figures))));
  const power = Math.floor(Math.log10(Math.abs(rounded)));
  return power >= -4 && power < 12 ? rounded.toFixed(Math.max(0, figures - power - 1)) : rounded.toPrecision(figures);
}
export function unitLabel(unit) {
  return {'1': '', 'kg/m^3': 'kg/m³', 'g/cm^3': 'g/cm³', 'lb/ft^3': 'lb/ft³', 'lb/in^3': 'lb/in³',
    'W/(m*K)': 'W/(m·K)', 'J/(kg*K)': 'J/(kg·K)', 'BTU/(hr*ft*degF)': 'BTU/(h·ft·°F)', 'BTU/(lb*degF)': 'BTU/(lb·°F)',
    degC: '°C', degF: '°F'}[unit] ?? unit;
}
export function displayUnit(property, preference) {
  const override = preference.overrides?.[property.id];
  return property.units.find(u => u.unit === override)
    || (preference.system === 'imperial' && property.units.find(u => u.system === 'imperial'))
    || property.units.find(u => u.unit === property.metric_unit) || property.units[0];
}
export function quantity(value, figures, unit, uncertainty = false) {
  return significant(value * unit.factor + (uncertainty ? 0 : unit.offset), figures);
}
export function thicknessText(interval, system) {
  const factor = system === 'imperial' ? 1 / .0254 : 1000;
  const unit = system === 'imperial' ? 'in' : 'mm';
  const f = value => String(Number((value * factor).toPrecision(6)));
  const {minimum: low, maximum: high} = interval;
  return `${low == null ? '≤ ' + f(high) : high == null ? '≥ ' + f(low) : f(low) + '–' + f(high)} ${unit}`;
}
export function resultText(observation, unit) {
  const result = observation.result;
  if (!result.canonical) return result.kind === 'not_applicable' ? 'Not applicable' : 'Unreported';
  const c = result.canonical, digits = result.reported.significant_figures;
  const f = x => quantity(x, digits, unit);
  let text = result.kind === 'interval' ? `${f(c.minimum)}–${f(c.maximum)}` : `${{lower_bound: '≥ ', upper_bound: '≤ '}[result.kind] || ''}${f(c.value)}`;
  if (observation.uncertainty) text += ` ± ${quantity(observation.uncertainty.canonical.value, observation.uncertainty.reported.significant_figures, unit, true)}`;
  return text + (unitLabel(unit.unit) ? ' ' + unitLabel(unit.unit) : '');
}
export function summarize(observations, property) {
  const pool = observations.filter(o => o.property_id === property && o.status === 'active');
  const measured = pool.filter(o => ['point', 'interval'].includes(o.result.kind));
  const endpoints = measured.flatMap(o => o.result.kind === 'interval' ? [o.result.canonical.minimum, o.result.canonical.maximum] : [o.result.canonical.value]);
  const limits = {};
  for (const kind of ['lower_bound', 'upper_bound']) {
    const rows = pool.filter(o => o.result.kind === kind);
    if (rows.length) limits[kind] = {minimum: Math.min(...rows.map(o => o.result.canonical.value)), maximum: Math.max(...rows.map(o => o.result.canonical.value)), significant_figures: Math.min(...rows.map(o => o.result.reported.significant_figures)), count: rows.length};
  }
  return {range: endpoints.length ? {minimum: Math.min(...endpoints), maximum: Math.max(...endpoints), significant_figures: Math.min(...measured.map(o => o.result.reported.significant_figures))} : null,
    limits, observation_count: pool.length, material_count: new Set(pool.map(o => o.material_id)).size};
}
export function summaryText(summary, unit) {
  if (!summary?.observation_count) return 'Unreported';
  const range = r => {
    const a = quantity(r.minimum, r.significant_figures, unit), b = quantity(r.maximum, r.significant_figures, unit);
    return a === b ? a : `${a}–${b}`;
  };
  const pieces = [];
  if (summary.range) pieces.push(range(summary.range));
  for (const [kind, bounds] of Object.entries(summary.limits)) {
    const label = kind === 'lower_bound' ? 'Minimum limit' : 'Maximum limit';
    pieces.push(bounds.minimum === bounds.maximum && !summary.range ? `${kind === 'lower_bound' ? '≥' : '≤'} ${range(bounds)}` : `${label}${bounds.count > 1 ? 's' : ''}: ${range(bounds)}`);
  }
  return pieces.join(' · ') + (pieces.length && unitLabel(unit.unit) ? ' ' + unitLabel(unit.unit) : '');
}
