// Search resolves identity and property intent without downloading observations.
export const MAX_RESULTS = 50;
export function normalize(value) {
  return String(value ?? '').normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
    .replace(/['’]/g, '').replace(/([a-z])(\d)/g, '$1 $2').replace(/(\d)([a-z])/g, '$1 $2')
    .replace(/[^a-z0-9]+/g, ' ').trim();
}
const compact = value => normalize(value).replaceAll(' ', '');
const phrase = (text, term) => (` ${text} `).includes(` ${term} `);

function editDistance(a, b) {
  let previous = Array.from({length: b.length + 1}, (_, i) => i);
  for (let i = 1; i <= a.length; i++) {
    const next = [i];
    for (let j = 1; j <= b.length; j++) next[j] = Math.min(next[j-1] + 1, previous[j] + 1, previous[j-1] + (a[i-1] !== b[j-1]));
    previous = next;
  }
  return previous[b.length];
}

export function createSearch(index) {
  const entities = index.entities.map(e => ({...e, terms: [...new Set([e.name, e.id, ...e.aliases].map(normalize))]}));
  const propertyTerms = index.properties.flatMap(p => [p.name, p.id, ...p.aliases]
    .map(normalize).filter(t => t.length > 1).map(term => ({term, property: p})))
    .sort((a, b) => b.term.length - a.term.length || a.property.id.localeCompare(b.property.id));
  function matchEntities(text, category) {
    const query = normalize(text), tight = compact(query), words = query.split(' ');
    if (!query) return [];
    return entities.filter(e => !category || e.category_ids.includes(category)).map(e => {
      let score = 0, exact = false;
      for (const term of e.terms) {
        if (compact(term) === tight) {score = Math.max(score, 1000); exact = true;}
        else if (term.startsWith(query)) score = Math.max(score, 650);
        else if (phrase(term, query)) score = Math.max(score, 550);
        else if (words.every(w => term.split(' ').some(t => t.startsWith(w)))) score = Math.max(score, 450);
        else if (query.length >= 5 && Math.abs(term.length - query.length) <= 2 && editDistance(query, term) <= (query.length > 9 ? 2 : 1)) score = Math.max(score, 200);
      }
      // Grade names take precedence over forms/states with shared aliases.
      const kindRank = {material: 4, category: 3, state: 2, form: 1}[e.kind];
      return {entity: e, score, exact, kindRank};
    }).filter(x => x.score > 0).sort((a, b) => b.score - a.score || b.kindRank - a.kindRank || a.entity.name.localeCompare(b.entity.name));
  }
  function choose(matches, property) {
    const exact = matches.filter(m => m.exact);
    // A material name can also be the base chemistry category. Only resolve
    // automatically when the best kind contains exactly one exact identity.
    const best = exact.filter(m => m.kindRank === exact[0]?.kindRank);
    if (best.length === 1) return {kind: 'route', route: {...best[0].entity.route, ...(property ? {property} : {})}};
    return {kind: 'matches', total: matches.length, matches: matches.slice(0, MAX_RESULTS).map(m => m.entity), property};
  }
  return function resolve(input, overrideProperty) {
    const query = normalize(input);
    if (!query) return {kind: 'home'};
    if (/\b(strongest|lightest|best|compare|versus|vs|rank|ranking|stiffer|cheapest)\b/.test(query)) return {kind: 'comparison'};
    const whole = matchEntities(query);
    if (!overrideProperty && whole.some(m => m.exact)) return choose(whole);
    const found = propertyTerms.find(p => phrase(query, p.term));
    const property = overrideProperty || found?.property.id;
    let remaining = found ? query.replace(found.term, ' ').trim() : query;
    const group = index.property_groups.find(g => [g.name, ...g.aliases].some(a => phrase(query, normalize(a))));
    if (group && !property) return {kind: 'clarify', group, query: input};
    if (overrideProperty && group) remaining = remaining.replace(normalize(group.name), '').trim();
    if (property) {
      remaining = remaining.replace(/\b(of|for|in|the|a|an)\b/g, '').replace(/\s+/g, ' ').trim();
      if (!remaining) return {kind: 'route', route: {property}};
      const matches = matchEntities(remaining);
      return choose(matches, property);
    }
    return choose(whole);
  };
}
