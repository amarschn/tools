(function (root) {
  "use strict";

  var corpus = root.MaterialsPrototypeCorpus;
  if (!corpus) throw new Error("synthetic-corpus.js must load before search-core.js");

  var MAX_RESULTS = 40;
  var propertyById = new Map();
  var groupById = new Map();
  var taxonById = new Map();
  var materialById = new Map();
  var stateById = new Map();
  var observationsByMaterial = new Map();
  var observationsByState = new Map();
  var statesByMaterial = new Map();
  var taxaByMaterial = new Map();

  corpus.properties.forEach(function (item) { propertyById.set(item.id, item); });
  corpus.property_groups.forEach(function (item) { groupById.set(item.id, item); });
  corpus.taxa.forEach(function (item) { taxonById.set(item.id, item); });
  corpus.materials.forEach(function (item) {
    materialById.set(item.id, item);
    statesByMaterial.set(item.id, []);
    observationsByMaterial.set(item.id, []);
  });
  corpus.states.forEach(function (item) {
    stateById.set(item.id, item);
    statesByMaterial.get(item.material_id).push(item);
    observationsByState.set(item.id, []);
  });
  corpus.observations.forEach(function (item) {
    observationsByMaterial.get(item.material_id).push(item);
    if (item.state_id) observationsByState.get(item.state_id).push(item);
  });

  function normalize(value) {
    return String(value == null ? "" : value)
      .normalize("NFKD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .replace(/&/g, " and ")
      .replace(/[×·]/g, " ")
      .replace(/[_/\\(),.%]+/g, " ")
      .replace(/([a-z])([0-9])/g, "$1 $2")
      .replace(/([0-9])([a-z])/g, "$1 $2")
      .replace(/[^a-z0-9+\-]+/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function compact(value) {
    return normalize(value).replace(/[^a-z0-9]+/g, "");
  }

  function unique(values) {
    return Array.from(new Set(values.filter(Boolean)));
  }

  function taxonLineage(id) {
    var result = [];
    var current = taxonById.get(id);
    var guard = 0;
    while (current && guard < 30) {
      result.push(current.id);
      current = current.parent_id ? taxonById.get(current.parent_id) : null;
      guard += 1;
    }
    return result;
  }

  corpus.materials.forEach(function (material) {
    var all = [];
    material.taxon_ids.forEach(function (id) {
      all = all.concat(taxonLineage(id));
    });
    taxaByMaterial.set(material.id, unique(all));
  });

  function taxonName(id) {
    var item = taxonById.get(id);
    return item ? item.name : id;
  }

  function materialTaxonNames(material) {
    return material.taxon_ids.map(taxonName);
  }

  function observationCountForMaterial(materialId) {
    return observationsByMaterial.get(materialId).length;
  }

  function buildEntities() {
    var result = [];
    corpus.materials.forEach(function (material) {
      var childStates = statesByMaterial.get(material.id);
      var directObservations = observationsByMaterial
        .get(material.id)
        .filter(function (item) { return !item.state_id; });
      var baseAliases = unique(
        material.aliases.concat(material.designations || [])
      );

      result.push(prepareEntity({
        id: material.id,
        kind: "material",
        name: material.name,
        label: material.name,
        material_id: material.id,
        state_id: null,
        aliases: baseAliases,
        designations: material.designations || [],
        taxon_ids: taxaByMaterial.get(material.id),
        taxon_names: materialTaxonNames(material),
        identity_kind: material.identity_kind,
        notes: material.notes,
        state_count: childStates.length,
        observation_count: directObservations.length,
        has_direct_data: directObservations.length > 0
      }));

      childStates.forEach(function (state) {
        var stateTaxa = unique(
          taxaByMaterial.get(material.id).concat(
            (state.taxon_ids || []).reduce(function (all, id) {
              return all.concat(taxonLineage(id));
            }, [])
          )
        );
        var combinedDesignations = [];
        (material.designations || []).forEach(function (designation) {
          combinedDesignations.push(designation + " " + state.label);
        });
        result.push(prepareEntity({
          id: state.id,
          kind: "state",
          name: material.name + " — " + state.label,
          label: state.label,
          material_id: material.id,
          state_id: state.id,
          parent_name: material.name,
          aliases: unique(
            state.aliases
              .concat(material.aliases || [])
              .concat(combinedDesignations)
          ),
          designations: combinedDesignations,
          taxon_ids: stateTaxa,
          taxon_names: materialTaxonNames(material),
          identity_kind: material.identity_kind,
          notes: material.notes,
          state_count: 0,
          observation_count: observationsByState.get(state.id).length,
          has_direct_data: true,
          fixed_conditions: state.fixed_conditions
        }));
      });
    });
    return result;
  }

  function prepareEntity(entity) {
    var identityStrings = unique(
      [entity.name, entity.label, entity.id.replace(/^synthetic-/, "")]
        .concat(entity.aliases || [])
        .concat(entity.designations || [])
    );
    entity._identity_strings = identityStrings.map(normalize);
    entity._identity_compacts = identityStrings.map(compact);
    entity._tokens = unique(
      entity._identity_strings.join(" ").split(" ").filter(function (term) {
        return term.length > 0;
      })
    );
    return entity;
  }

  var entities = buildEntities();
  var entityById = new Map();
  entities.forEach(function (item) { entityById.set(item.id, item); });

  var taxonAliasEntries = [];
  corpus.taxa.forEach(function (item) {
    [item.name].concat(item.aliases || []).forEach(function (phrase) {
      taxonAliasEntries.push({
        phrase: normalize(phrase),
        target: item
      });
    });
  });

  var propertyAliasEntries = [];
  corpus.properties.forEach(function (item) {
    [item.name].concat(item.aliases || []).forEach(function (phrase) {
      propertyAliasEntries.push({
        phrase: normalize(phrase),
        target: item
      });
    });
  });

  var groupAliasEntries = [];
  corpus.property_groups.forEach(function (item) {
    [item.name].concat(item.aliases || []).forEach(function (phrase) {
      groupAliasEntries.push({
        phrase: normalize(phrase),
        target: item
      });
    });
  });

  function sortAliasEntries(entries) {
    entries.sort(function (a, b) {
      var wordDifference = b.phrase.split(" ").length - a.phrase.split(" ").length;
      if (wordDifference) return wordDifference;
      return b.phrase.length - a.phrase.length;
    });
  }

  sortAliasEntries(taxonAliasEntries);
  sortAliasEntries(propertyAliasEntries);
  sortAliasEntries(groupAliasEntries);

  function phrasePattern(phrase) {
    return new RegExp(
      "(^|\\s)" +
        phrase
          .split(" ")
          .map(function (part) {
            return part.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
          })
          .join("\\s+") +
        "(?=\\s|$)",
      "g"
    );
  }

  function matchLongestNamespace(text, entries) {
    var bestLength = -1;
    var matches = [];
    entries.forEach(function (entry) {
      var pattern = phrasePattern(entry.phrase);
      if (!pattern.test(text)) return;
      var length = entry.phrase.split(" ").length * 1000 + entry.phrase.length;
      if (length > bestLength) {
        bestLength = length;
        matches = [entry];
      } else if (length === bestLength) {
        matches.push(entry);
      }
    });
    var targets = [];
    var seen = new Set();
    matches.forEach(function (entry) {
      if (seen.has(entry.target.id)) return;
      seen.add(entry.target.id);
      targets.push(entry.target);
    });
    return {
      phrase: matches.length ? matches[0].phrase : "",
      targets: targets
    };
  }

  function removePhrase(text, phrase) {
    if (!phrase) return text;
    return text
      .replace(phrasePattern(phrase), " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function isInScope(entity, scopeId) {
    return !scopeId || entity.taxon_ids.indexOf(scopeId) !== -1;
  }

  function identityRank(entity, materialTerms) {
    var query = normalize(materialTerms);
    var queryCompact = compact(query);
    var tokens = query.split(" ").filter(Boolean);
    var exactCompact = entity._identity_compacts.indexOf(queryCompact);
    if (exactCompact !== -1) return [0, entity.kind === "material" ? 0 : 1];

    var exact = entity._identity_strings.indexOf(query);
    if (exact !== -1) return [1, entity.kind === "material" ? 0 : 1];

    var prefix = entity._identity_strings.some(function (value) {
      return value.indexOf(query) === 0;
    });
    if (prefix) return [2, entity.kind === "material" ? 0 : 1];

    var compactPrefix = entity._identity_compacts.some(function (value) {
      return value.indexOf(queryCompact) === 0;
    });
    if (compactPrefix) return [3, entity.kind === "material" ? 0 : 1];

    var allTokens = tokens.length && tokens.every(function (term) {
      return entity._tokens.some(function (candidate) {
        return candidate === term || candidate.indexOf(term) === 0;
      });
    });
    if (allTokens) return [4, entity.kind === "material" ? 0 : 1];

    var substring = query.length >= 2 && entity._identity_strings.some(function (value) {
      return value.indexOf(query) !== -1;
    });
    if (substring) return [5, entity.kind === "material" ? 0 : 1];
    return null;
  }

  function diceCoefficient(a, b) {
    if (a === b) return 1;
    if (a.length < 2 || b.length < 2) return 0;
    var counts = new Map();
    var matches = 0;
    var index;
    for (index = 0; index < a.length - 1; index += 1) {
      var pair = a.slice(index, index + 2);
      counts.set(pair, (counts.get(pair) || 0) + 1);
    }
    for (index = 0; index < b.length - 1; index += 1) {
      var candidate = b.slice(index, index + 2);
      var count = counts.get(candidate) || 0;
      if (count) {
        matches += 1;
        counts.set(candidate, count - 1);
      }
    }
    return (2 * matches) / (a.length + b.length - 2);
  }

  function fuzzyRank(entity, materialTerms) {
    var query = compact(materialTerms);
    var best = 0;
    entity._identity_compacts.forEach(function (candidate) {
      best = Math.max(best, diceCoefficient(query, candidate));
    });
    return best >= 0.58 ? [6, -best] : null;
  }

  function compareRanked(a, b) {
    if (a.rank[0] !== b.rank[0]) return a.rank[0] - b.rank[0];
    if (a.rank[1] !== b.rank[1]) return a.rank[1] - b.rank[1];
    return a.entity.name.localeCompare(b.entity.name, undefined, {
      numeric: true,
      sensitivity: "base"
    }) || a.entity.id.localeCompare(b.entity.id);
  }

  function observationsForEntity(entity) {
    if (!entity) return [];
    if (entity.state_id) return observationsByState.get(entity.state_id).slice();
    return observationsByMaterial
      .get(entity.material_id)
      .filter(function (item) { return !item.state_id; });
  }

  function descendantObservationsForEntity(entity) {
    if (!entity) return [];
    if (entity.state_id || entity.has_direct_data) return observationsForEntity(entity);
    return observationsByMaterial.get(entity.material_id).slice();
  }

  function availabilityFor(entity, propertyIds) {
    var observations = descendantObservationsForEntity(entity);
    var counts = Object.create(null);
    propertyIds.forEach(function (id) { counts[id] = 0; });
    observations.forEach(function (item) {
      if (Object.prototype.hasOwnProperty.call(counts, item.property_id)) {
        counts[item.property_id] += 1;
      }
    });
    return counts;
  }

  function stateChildren(entity) {
    if (!entity || entity.kind !== "material") return [];
    return statesByMaterial.get(entity.material_id).map(function (state) {
      return entityById.get(state.id);
    });
  }

  function taxonRecordCount(taxonId) {
    var seen = new Set();
    entities.forEach(function (entity) {
      if (entity.kind === "state" || entity.has_direct_data) {
        if (isInScope(entity, taxonId)) seen.add(entity.id);
      }
    });
    return seen.size;
  }

  function analyze(query, options) {
    var started = performance.now();
    var rawQuery = String(query || "");
    var normalized = normalize(rawQuery);
    var selectedPropertyId =
      options && propertyById.has(options.propertyId) ? options.propertyId : null;
    var selectedScopeId =
      options && taxonById.has(options.scopeId) ? options.scopeId : null;
    var comparisonIntent = /\b(strongest|lightest|best|compare|versus|vs)\b/.test(
      normalized
    );

    if (!normalized) {
      return finish({
        query: rawQuery,
        normalized_query: normalized,
        state: "idle",
        scope: null,
        scope_options: [],
        property_intent: null,
        material_terms: "",
        comparison_intent: false,
        results: corpus.materials
          .slice()
          .sort(function (a, b) {
            return a.name.localeCompare(b.name, undefined, { numeric: true });
          })
          .slice(0, 14)
          .map(function (material) { return entityById.get(material.id); }),
        total: corpus.materials.length
      }, started);
    }

    var working = normalized;
    var propertyMatch = matchLongestNamespace(working, propertyAliasEntries);
    var propertyIntent = null;
    if (selectedPropertyId) {
      propertyIntent = {
        kind: "property",
        id: selectedPropertyId,
        ids: [selectedPropertyId],
        label: propertyById.get(selectedPropertyId).name,
        phrase: propertyMatch.phrase || ""
      };
      if (propertyMatch.phrase) working = removePhrase(working, propertyMatch.phrase);
      var selectedGroupMatch = matchLongestNamespace(working, groupAliasEntries);
      if (
        selectedGroupMatch.targets.some(function (group) {
          return group.member_ids.indexOf(selectedPropertyId) !== -1;
        })
      ) {
        working = removePhrase(working, selectedGroupMatch.phrase);
      }
    } else if (propertyMatch.targets.length === 1) {
      propertyIntent = {
        kind: "property",
        id: propertyMatch.targets[0].id,
        ids: [propertyMatch.targets[0].id],
        label: propertyMatch.targets[0].name,
        phrase: propertyMatch.phrase
      };
      working = removePhrase(working, propertyMatch.phrase);
    }

    if (!propertyIntent) {
      var groupMatch = matchLongestNamespace(working, groupAliasEntries);
      if (groupMatch.targets.length === 1) {
        var group = groupMatch.targets[0];
        propertyIntent = {
          kind: group.member_ids.length === 1 ? "property" : "group",
          id: group.member_ids.length === 1 ? group.member_ids[0] : group.id,
          ids: group.member_ids.slice(),
          label: group.name,
          phrase: groupMatch.phrase
        };
        working = removePhrase(working, groupMatch.phrase);
      }
    }

    var scopeMatch = matchLongestNamespace(working, taxonAliasEntries);
    var scope = selectedScopeId
      ? taxonById.get(selectedScopeId)
      : (scopeMatch.targets.length === 1 ? scopeMatch.targets[0] : null);
    if (scopeMatch.phrase) working = removePhrase(working, scopeMatch.phrase);
    var materialTerms = working;

    var candidates = entities.filter(function (entity) {
      return !scope || isInScope(entity, scope.id);
    });

    var ranked = [];
    if (materialTerms) {
      candidates.forEach(function (entity) {
        var rank = identityRank(entity, materialTerms);
        if (rank) ranked.push({ entity: entity, rank: rank });
      });
      if (!ranked.length) {
        candidates.forEach(function (entity) {
          var rank = fuzzyRank(entity, materialTerms);
          if (rank) ranked.push({ entity: entity, rank: rank });
        });
      }
    } else if (scope) {
      candidates.forEach(function (entity) {
        if (entity.kind === "material") ranked.push({ entity: entity, rank: [7, 0] });
      });
    }

    ranked.sort(compareRanked);
    var resultEntities = ranked.slice(0, MAX_RESULTS).map(function (item) {
      return item.entity;
    });

    var state = "results";
    if (comparisonIntent) state = "unsupported-comparison";
    else if (!selectedScopeId && scopeMatch.targets.length > 1) state = "choose-scope";
    else if (propertyIntent && !materialTerms && !scope) state = "needs-material";
    else if (propertyIntent && propertyIntent.kind === "group") state = "choose-property";
    else if (scope && !materialTerms && !propertyIntent) state = "browse-scope";
    else if (!resultEntities.length) state = "no-match";

    var intentPropertyIds = propertyIntent ? propertyIntent.ids : [];
    return finish({
      query: rawQuery,
      normalized_query: normalized,
      state: state,
      scope: scope,
      scope_options: selectedScopeId ? [scope] : scopeMatch.targets,
      property_intent: propertyIntent,
      material_terms: materialTerms,
      comparison_intent: comparisonIntent,
      results: resultEntities,
      total: ranked.length,
      availability: resultEntities.reduce(function (map, entity) {
        map[entity.id] = availabilityFor(entity, intentPropertyIds);
        return map;
      }, {})
    }, started);
  }

  function finish(result, started) {
    result.duration_ms = performance.now() - started;
    return result;
  }

  function formatNumber(value, significantDigits) {
    if (!Number.isFinite(value)) return "—";
    return Number(value).toLocaleString(undefined, {
      maximumSignificantDigits: significantDigits || 4,
      useGrouping: Math.abs(value) >= 10000
    });
  }

  function formatObservation(observation) {
    var property = propertyById.get(observation.property_id);
    if (!property) return "—";
    var value = observation.value;
    var displayValue;
    if (property.id === "max_service_temperature") {
      displayValue = formatNumber(value - 273.15, 4);
    } else if (property.display_scale === 0.01) {
      displayValue = formatNumber(value / 0.01, 4);
    } else {
      displayValue = formatNumber(value / property.display_scale, 4);
    }
    return displayValue + " " + property.display_unit;
  }

  function formatConditionValue(key, value) {
    if (key === "temperature_K" && typeof value === "number") {
      return formatNumber(value - 273.15, 4) + " °C";
    }
    if (key === "moisture_content_1" && typeof value === "number") {
      return formatNumber(value * 100, 3) + "% moisture";
    }
    if (key === "fiber_mass_fraction_1" && typeof value === "number") {
      return formatNumber(value * 100, 3) + "% fiber by mass";
    }
    if (key === "fiber_volume_fraction_1" && typeof value === "number") {
      return formatNumber(value * 100, 3) + "% fiber by volume";
    }
    if (key === "thickness_m" && Array.isArray(value)) {
      return value.map(function (item) {
        return formatNumber(item * 1000, 3);
      }).join("–") + " mm";
    }
    if (Array.isArray(value)) return value.join("–");
    return String(value).replace(/_/g, " ");
  }

  function conditionSummary(observation) {
    var conditions = observation && observation.conditions
      ? observation.conditions
      : {};
    var parts = [];
    Object.keys(conditions).forEach(function (key) {
      if (key === "temperature_K" && Math.abs(conditions[key] - 293.15) < 0.1) return;
      parts.push(formatConditionValue(key, conditions[key]));
    });
    return parts.length ? parts.join(" · ") : "nominal room conditions";
  }

  function entityContext(entity) {
    if (!entity) return "";
    if (entity.kind === "state") {
      return entity.parent_name + " · named state";
    }
    if (entity.state_count) {
      return entity.state_count + " named state" + (entity.state_count === 1 ? "" : "s");
    }
    return entity.taxon_names[0] || "material";
  }

  var dataBearingCount = entities.filter(function (entity) {
    return entity.kind === "state" || entity.has_direct_data;
  }).length;

  root.MaterialsPrototypeSearch = {
    corpus: corpus,
    stats: {
      material_count: corpus.materials.length,
      state_count: corpus.states.length,
      lookup_record_count: dataBearingCount,
      observation_count: corpus.observations.length,
      category_count: corpus.taxa.length,
      empty_category_count: corpus.taxa.filter(function (taxon) {
        return taxonRecordCount(taxon.id) === 0;
      }).length
    },
    normalize: normalize,
    compact: compact,
    search: analyze,
    getEntity: function (id) { return entityById.get(id) || null; },
    getMaterial: function (id) { return materialById.get(id) || null; },
    getState: function (id) { return stateById.get(id) || null; },
    getProperty: function (id) { return propertyById.get(id) || null; },
    getGroup: function (id) { return groupById.get(id) || null; },
    getTaxon: function (id) { return taxonById.get(id) || null; },
    getTaxonRecordCount: taxonRecordCount,
    getObservations: observationsForEntity,
    getDescendantObservations: descendantObservationsForEntity,
    getStateChildren: stateChildren,
    getAvailability: availabilityFor,
    formatObservation: formatObservation,
    conditionSummary: conditionSummary,
    entityContext: entityContext,
    taxonName: taxonName
  };
})(window);
