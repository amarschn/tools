(function (root) {
  "use strict";

  /*
   * Deliberately fabricated prototype data.
   *
   * The names, designations, values, sources, and locators in this file are
   * synthetic. They are plausible-looking only so the UI has realistic lengths,
   * units, missingness, and condition conflicts to render. Nothing here is
   * engineering guidance.
   */

  var VERSION = "synthetic-0.2.0";
  var BUILD = "ui-lab-2026.07.29.1";

  function property(id, name, aliases, unit, displayUnit, scale, groupId) {
    return {
      id: id,
      name: name,
      aliases: aliases || [],
      canonical_unit: unit,
      display_unit: displayUnit || unit,
      display_scale: scale || 1,
      group_id: groupId || null
    };
  }

  var properties = [
    property(
      "tensile_yield_strength",
      "Tensile yield strength",
      ["yield strength", "yield", "proof stress", "yield stress"],
      "Pa",
      "MPa",
      1000000,
      "strength"
    ),
    property(
      "ultimate_tensile_strength",
      "Ultimate tensile strength",
      ["tensile strength", "ultimate strength", "UTS"],
      "Pa",
      "MPa",
      1000000,
      "strength"
    ),
    property(
      "compressive_strength",
      "Compressive strength",
      ["compression strength", "crushing strength"],
      "Pa",
      "MPa",
      1000000,
      "strength"
    ),
    property(
      "flexural_strength",
      "Flexural strength",
      ["bend strength", "bending strength", "modulus of rupture", "MOR"],
      "Pa",
      "MPa",
      1000000,
      "strength"
    ),
    property(
      "notched_impact_strength",
      "Notched impact strength",
      ["impact strength", "notched impact", "izod impact"],
      "J/m",
      "J/m",
      1,
      "strength"
    ),
    property(
      "youngs_modulus",
      "Young's modulus",
      ["elastic modulus", "modulus of elasticity", "Young modulus"],
      "Pa",
      "GPa",
      1000000000,
      "stiffness"
    ),
    property(
      "flexural_modulus",
      "Flexural modulus",
      ["bending modulus"],
      "Pa",
      "GPa",
      1000000000,
      "stiffness"
    ),
    property("density", "Density", ["mass density", "rho"], "kg/m^3", "kg/m³", 1, null),
    property(
      "elongation_at_break",
      "Elongation at break",
      ["elongation", "strain at break", "ductility"],
      "1",
      "%",
      0.01,
      null
    ),
    property(
      "thermal_conductivity",
      "Thermal conductivity",
      ["heat conductivity", "thermal k"],
      "W/(m*K)",
      "W/(m·K)",
      1,
      "conductivity"
    ),
    property(
      "electrical_resistivity",
      "Electrical resistivity",
      ["resistivity", "electrical resistance"],
      "ohm*m",
      "Ω·m",
      1,
      "conductivity"
    ),
    property(
      "max_service_temperature",
      "Maximum service temperature",
      ["service temperature", "continuous use temperature", "max use temperature"],
      "K",
      "°C",
      1,
      "temperature"
    ),
    property(
      "shore_a_hardness",
      "Shore A hardness",
      ["shore hardness", "durometer", "shore a"],
      "1",
      "Shore A",
      1,
      "hardness"
    )
  ];

  var propertyGroups = [
    {
      id: "strength",
      name: "Strength",
      aliases: ["strength", "strong"],
      member_ids: [
        "tensile_yield_strength",
        "ultimate_tensile_strength",
        "compressive_strength",
        "flexural_strength",
        "notched_impact_strength"
      ]
    },
    {
      id: "stiffness",
      name: "Stiffness",
      aliases: ["stiffness", "rigidity", "modulus"],
      member_ids: ["youngs_modulus", "flexural_modulus"]
    },
    {
      id: "conductivity",
      name: "Conductivity",
      aliases: ["conductivity", "conduction"],
      member_ids: ["thermal_conductivity", "electrical_resistivity"]
    },
    {
      id: "temperature",
      name: "Temperature limit",
      aliases: ["temperature limit", "temperature"],
      member_ids: ["max_service_temperature"]
    },
    {
      id: "hardness",
      name: "Hardness",
      aliases: ["hardness", "hard"],
      member_ids: ["shore_a_hardness"]
    }
  ];

  function taxon(id, name, parentId, aliases) {
    return {
      id: id,
      name: name,
      parent_id: parentId || null,
      aliases: aliases || []
    };
  }

  var taxa = [
    taxon("metals", "Metals", null, ["metal", "metallic material"]),
    taxon("aluminium-like-alloys", "Aluminium-like alloys", "metals", [
      "aluminium",
      "aluminum",
      "aluminium alloy",
      "aluminum alloy",
      "light alloy"
    ]),
    taxon("steels", "Steels", "metals", ["steel", "ferrous alloy"]),
    taxon("carbon-steels", "Carbon steels", "steels", [
      "carbon steel",
      "mild steel",
      "plain carbon steel"
    ]),
    taxon("alloy-steels", "Alloy steels", "steels", [
      "alloy steel",
      "low alloy steel",
      "chromoly"
    ]),
    taxon("stainless-steels", "Stainless steels", "steels", [
      "stainless",
      "stainless steel"
    ]),
    taxon("titanium-like-alloys", "Titanium-like alloys", "metals", [
      "titanium",
      "titanium alloy"
    ]),
    taxon("copper-like-alloys", "Copper-like alloys", "metals", [
      "copper",
      "copper alloy"
    ]),

    taxon("polymers", "Polymers and plastics", null, [
      "plastic",
      "plastics",
      "polymer",
      "polymers"
    ]),
    taxon("thermoplastics", "Thermoplastics", "polymers", ["thermoplastic"]),
    taxon("engineering-plastics", "Engineering plastics", "thermoplastics", [
      "engineering plastic",
      "engineering polymer",
      "technical plastic"
    ]),
    taxon("acetals", "Acetals", "engineering-plastics", [
      "acetal",
      "POM",
      "polyoxymethylene"
    ]),
    taxon("peek-like-polymers", "PEEK-like polymers", "engineering-plastics", [
      "PEEK",
      "polyether ether ketone",
      "high temperature plastic"
    ]),
    taxon("nylons", "Nylons", "engineering-plastics", [
      "nylon",
      "polyamide",
      "PA"
    ]),
    taxon("polycarbonates", "Polycarbonates", "engineering-plastics", [
      "polycarbonate",
      "PC"
    ]),
    taxon("commodity-plastics", "Commodity plastics", "thermoplastics", [
      "commodity plastic",
      "polyethylene"
    ]),
    taxon("fluoropolymers", "Fluoropolymers", "engineering-plastics", [
      "fluoropolymer",
      "PTFE"
    ]),
    taxon("elastomers", "Elastomers", "polymers", ["rubber", "elastomer"]),
    taxon("foams", "Polymer foams", "polymers", ["foam", "polymer foam"]),
    taxon("thermosets", "Thermosets", "polymers", [
      "thermoset",
      "thermosetting polymer"
    ]),

    taxon("ceramics", "Ceramics and glasses", null, [
      "ceramic",
      "ceramics",
      "glass"
    ]),
    taxon("technical-ceramics", "Technical ceramics", "ceramics", [
      "advanced ceramic",
      "structural ceramic"
    ]),
    taxon("glasses", "Bulk glasses", "ceramics", ["bulk glass", "glass"]),

    taxon("composites", "Composites", null, [
      "composite",
      "composite material",
      "carbon"
    ]),
    taxon("fiber-reinforced-polymers", "Fiber-reinforced polymers", "composites", [
      "fiber composite",
      "fibre composite",
      "carbon",
      "glass"
    ]),

    taxon("natural-materials", "Natural materials", null, ["natural material"]),
    taxon("woods", "Woods", "natural-materials", ["wood", "timber", "lumber"])
  ];

  var materials = [];
  var states = [];
  var observations = [];
  var observationCounter = 0;
  var propertyById = Object.create(null);

  properties.forEach(function (item) {
    propertyById[item.id] = item;
  });

  function syntheticId(id) {
    return id.indexOf("synthetic-") === 0 ? id : "synthetic-" + id;
  }

  function addMaterial(id, name, identityKind, taxonIds, aliases, designations, notes) {
    var record = {
      id: syntheticId(id),
      name: name,
      identity_kind: identityKind,
      taxon_ids: taxonIds || [],
      aliases: aliases || [],
      designations: designations || [],
      notes: notes || ""
    };
    materials.push(record);
    return record.id;
  }

  function normalizeEntry(raw) {
    if (typeof raw === "number") return { value: raw };
    return raw;
  }

  function addObservations(materialId, stateId, data, inheritedConditions) {
    Object.keys(data || {}).forEach(function (propertyId) {
      var propertyRecord = propertyById[propertyId];
      if (!propertyRecord) {
        throw new Error("Unknown synthetic property: " + propertyId);
      }

      var rawEntries = Array.isArray(data[propertyId])
        ? data[propertyId]
        : [data[propertyId]];

      rawEntries.forEach(function (rawEntry) {
        var entry = normalizeEntry(rawEntry);
        observationCounter += 1;
        observations.push({
          id: "synthetic-obs-" + String(observationCounter).padStart(4, "0"),
          material_id: materialId,
          state_id: stateId || null,
          property_id: propertyId,
          value: entry.value,
          value_min: entry.value_min == null ? null : entry.value_min,
          value_max: entry.value_max == null ? null : entry.value_max,
          unit: propertyRecord.canonical_unit,
          basis: entry.basis || "synthetic_typical",
          conditions: Object.assign(
            { temperature_K: 293.15 },
            inheritedConditions || {},
            entry.conditions || {}
          ),
          source_id: entry.source_id || "synthetic-fixture",
          source_locator:
            entry.source_locator ||
            "Fabricated case " +
              String(observationCounter).padStart(4, "0") +
              " · " +
              propertyId
        });
      });
    });
  }

  function addState(id, materialId, label, aliases, fixedConditions, data, taxonIds) {
    var state = {
      id: syntheticId(id),
      material_id: materialId,
      label: label,
      aliases: aliases || [],
      fixed_conditions: fixedConditions || {},
      taxon_ids: taxonIds || []
    };
    states.push(state);
    addObservations(materialId, state.id, data, fixedConditions);
    return state.id;
  }

  function addDirectData(materialId, data) {
    addObservations(materialId, null, data, {});
  }

  function metalData(density, modulus, yieldStrength, tensileStrength, elongation, thermal, maxTemp, resistivity) {
    return {
      density: density,
      youngs_modulus: modulus,
      tensile_yield_strength: {
        value: yieldStrength,
        basis: "synthetic_minimum"
      },
      ultimate_tensile_strength: {
        value: tensileStrength,
        basis: "synthetic_minimum"
      },
      elongation_at_break: elongation,
      thermal_conductivity: thermal,
      max_service_temperature: maxTemp,
      electrical_resistivity: resistivity
    };
  }

  function polymerData(density, modulus, tensile, flexural, elongation, thermal, maxTemp, impact) {
    return {
      density: density,
      youngs_modulus: modulus,
      ultimate_tensile_strength: tensile,
      flexural_strength: flexural,
      elongation_at_break: elongation,
      thermal_conductivity: thermal,
      max_service_temperature: maxTemp,
      notched_impact_strength: impact
    };
  }

  function ceramicData(density, modulus, flexural, compressive, thermal, maxTemp) {
    return {
      density: density,
      youngs_modulus: modulus,
      flexural_strength: flexural,
      compressive_strength: compressive,
      thermal_conductivity: thermal,
      max_service_temperature: maxTemp
    };
  }

  function compositeData(density, modulus, tensile, compressive, thermal, conditions) {
    return {
      density: density,
      youngs_modulus: {
        value: modulus,
        conditions: conditions
      },
      ultimate_tensile_strength: {
        value: tensile,
        conditions: conditions
      },
      compressive_strength: {
        value: compressive,
        conditions: conditions
      },
      thermal_conductivity: thermal
    };
  }

  function elastomerData(density, tensile, elongation, shoreA, maxTemp) {
    return {
      density: density,
      ultimate_tensile_strength: tensile,
      elongation_at_break: elongation,
      shore_a_hardness: shoreA,
      max_service_temperature: maxTemp
    };
  }

  function foamData(density, compressive, thermal, maxTemp) {
    return {
      density: density,
      compressive_strength: compressive,
      thermal_conductivity: thermal,
      max_service_temperature: maxTemp
    };
  }

  /*
   * Metal-like stress set. AX60/AX61 and T6/T651 are intentionally close.
   */
  var ax60 = addMaterial(
    "synal-ax60",
    "Synal AX60",
    "synthetic_standard_grade",
    ["aluminium-like-alloys"],
    ["AX-60", "Synal 60"],
    ["AX60"],
    "Condition is required before values can be looked up."
  );
  addState("synal-ax60-t4", ax60, "T4", ["AX60 T4", "AX60-T4"], { product_form: "extrusion" },
    metalData(2704, 68.2e9, 118e6, 232e6, 0.18, 154, 423, 4.1e-8));
  addState("synal-ax60-t6", ax60, "T6 · extrusion", ["AX60 T6", "AX60-T6"], { product_form: "extrusion" },
    metalData(2708, 69.1e9, 247e6, 301e6, 0.12, 166, 438, 4.0e-8));
  addState("synal-ax60-t651", ax60, "T651 · plate", ["AX60 T651", "AX60-T651"], { product_form: "plate" },
    metalData(2708, 69.3e9, 254e6, 307e6, 0.11, 164, 438, 4.0e-8));

  var ax61 = addMaterial(
    "synal-ax61",
    "Synal AX61",
    "synthetic_standard_grade",
    ["aluminium-like-alloys"],
    ["AX-61", "Synal 61"],
    ["AX61"],
    "Near-collision with AX60."
  );
  addState("synal-ax61-t6", ax61, "T6 · extrusion", ["AX61 T6", "AX61-T6"], { product_form: "extrusion" },
    metalData(2691, 70.0e9, 228e6, 284e6, 0.14, 181, 430, 3.9e-8));

  var ax70 = addMaterial(
    "synal-ax70",
    "Synal AX70",
    "synthetic_standard_grade",
    ["aluminium-like-alloys"],
    ["AX-70", "Synal 70"],
    ["AX70"],
    "High-strength synthetic alloy with direction-sensitive observations."
  );
  var ax70t6 = addState("synal-ax70-t6", ax70, "T6 · plate", ["AX70 T6", "AX70-T6"], { product_form: "plate" },
    metalData(2814, 71.4e9, 486e6, 548e6, 0.09, 128, 411, 5.4e-8));
  observations.push({
    id: "synthetic-obs-" + String(++observationCounter).padStart(4, "0"),
    material_id: ax70,
    state_id: ax70t6,
    property_id: "tensile_yield_strength",
    value: 451e6,
    value_min: null,
    value_max: null,
    unit: "Pa",
    basis: "synthetic_minimum",
    conditions: {
      temperature_K: 293.15,
      product_form: "plate",
      thickness_m: [0.025, 0.05],
      orientation: "LT"
    },
    source_id: "synthetic-fixture-b",
    source_locator: "Fabricated conflicting case · AX70-T6/LT"
  });
  addState("synal-ax70-t73", ax70, "T73 · plate", ["AX70 T73", "AX70-T73"], { product_form: "plate" },
    metalData(2812, 71.0e9, 409e6, 481e6, 0.13, 132, 421, 5.5e-8));

  var c18 = addMaterial(
    "synsteel-c18",
    "Synsteel C18",
    "synthetic_standard_grade",
    ["carbon-steels"],
    ["C-18", "synthetic mild steel"],
    ["C18"],
    "Low-carbon synthetic steel."
  );
  addState("synsteel-c18-annealed", c18, "annealed", ["C18 annealed"], { material_state: "annealed" },
    metalData(7860, 202e9, 223e6, 401e6, 0.31, 51, 693, 1.7e-7));
  addState("synsteel-c18-cold-drawn", c18, "cold-drawn", ["C18 cold drawn", "C18 CD"], { material_state: "cold_drawn" },
    metalData(7860, 204e9, 381e6, 449e6, 0.17, 49, 653, 1.8e-7));

  var c20 = addMaterial(
    "synsteel-c20",
    "Synsteel C20",
    "synthetic_standard_grade",
    ["carbon-steels"],
    ["C-20"],
    ["C20"],
    "Near-collision with C18."
  );
  addState("synsteel-c20-normalized", c20, "normalized", ["C20 normalized"], { material_state: "normalized" },
    metalData(7851, 205e9, 286e6, 432e6, 0.25, 50, 683, 1.8e-7));

  var q40 = addMaterial(
    "synsteel-q40",
    "Synsteel Q40",
    "synthetic_standard_grade",
    ["alloy-steels"],
    ["Q-40", "synthetic chromoly"],
    ["Q40"],
    "Heat-treatment state changes the mechanical values."
  );
  addState("synsteel-q40-annealed", q40, "annealed", ["Q40 annealed"], { material_state: "annealed" },
    metalData(7840, 207e9, 417e6, 648e6, 0.24, 43, 723, 2.1e-7));
  addState("synsteel-q40-qt550", q40, "QT-550", ["Q40 QT 550", "Q40 QT-550"], { material_state: "quenched_tempered_550" },
    metalData(7842, 208e9, 713e6, 861e6, 0.17, 42, 703, 2.2e-7));
  addState("synsteel-q40-qt700", q40, "QT-700", ["Q40 QT 700", "Q40 QT-700"], { material_state: "quenched_tempered_700" },
    metalData(7844, 208e9, 892e6, 1034e6, 0.12, 42, 683, 2.2e-7));

  var s30 = addMaterial(
    "synstainless-s30",
    "Synstainless S30",
    "synthetic_standard_grade",
    ["stainless-steels"],
    ["S-30", "synthetic austenitic stainless"],
    ["S30"],
    "Cold work is modeled as a named state."
  );
  addState("synstainless-s30-annealed", s30, "annealed", ["S30 annealed"], { material_state: "annealed" },
    metalData(7970, 194e9, 214e6, 532e6, 0.47, 15.8, 713, 7.4e-7));
  addState("synstainless-s30-cw20", s30, "20% cold-worked", ["S30 20 percent cold worked", "S30 CW20"], { material_state: "cold_worked_20_percent" },
    metalData(7980, 196e9, 511e6, 747e6, 0.18, 15.5, 673, 7.6e-7));

  var t5 = addMaterial(
    "syntitan-t5",
    "Syntitan T5",
    "synthetic_standard_grade",
    ["titanium-like-alloys"],
    ["T-5"],
    ["T5"],
    "Synthetic titanium-like grade."
  );
  addState("syntitan-t5-annealed", t5, "annealed", ["T5 annealed"], { material_state: "annealed" },
    metalData(4440, 114e9, 841e6, 932e6, 0.14, 7.1, 693, 1.8e-6));
  addState("syntitan-t5-aged", t5, "solution-treated and aged", ["T5 STA", "T5 aged"], { material_state: "solution_treated_aged" },
    metalData(4443, 116e9, 1008e6, 1091e6, 0.09, 7.0, 663, 1.9e-6));

  var e10 = addMaterial(
    "syncopper-e10",
    "Syncopper E10",
    "synthetic_standard_grade",
    ["copper-like-alloys"],
    ["E-10"],
    ["E10"],
    "Synthetic high-conductivity copper-like grade."
  );
  addState("syncopper-e10-soft", e10, "soft", ["E10 soft", "E10 annealed"], { material_state: "annealed" },
    metalData(8920, 116e9, 71e6, 222e6, 0.42, 389, 473, 1.75e-8));
  addState("syncopper-e10-hard", e10, "hard", ["E10 hard"], { material_state: "cold_worked_hard" },
    metalData(8920, 119e9, 303e6, 347e6, 0.08, 376, 443, 1.83e-8));

  /*
   * Polymer stress set. Generic chemistries are taxa; the lookup materials are
   * fabricated commercial-grade identities.
   */
  var h100 = addMaterial(
    "polydemo-acetal-h100",
    "PolyDemo Acetal H100",
    "synthetic_commercial_grade",
    ["acetals"],
    ["H100", "PolyDemo H100"],
    ["H100"],
    "Commercial-grade-shaped identity with no standard-grade parent."
  );
  addState("polydemo-acetal-h100-unfilled", h100, "unfilled", ["H100 natural"], { formulation: "unfilled" },
    polymerData(1412, 3.15e9, 69e6, 97e6, 0.26, 0.31, 378, 61));

  var c100 = addMaterial(
    "polydemo-acetal-c100",
    "PolyDemo Acetal C100",
    "synthetic_commercial_grade",
    ["acetals"],
    ["C100", "PolyDemo C100"],
    ["C100"],
    "Filled states are cross-classified as composites."
  );
  addState("polydemo-acetal-c100-unfilled", c100, "unfilled", ["C100 natural"], { formulation: "unfilled" },
    polymerData(1401, 2.78e9, 63e6, 88e6, 0.32, 0.29, 369, 74));
  addState("polydemo-acetal-c100-gf20", c100, "20% glass-filled", ["C100 GF20", "C100 20GF"], { reinforcement: "glass_fiber", fiber_mass_fraction_1: 0.20 },
    polymerData(1518, 5.8e9, 86e6, 132e6, 0.055, 0.38, 383, 49), ["fiber-reinforced-polymers"]);
  addState("polydemo-acetal-c100-gf30", c100, "30% glass-filled", ["C100 GF30", "C100 30GF"], { reinforcement: "glass_fiber", fiber_mass_fraction_1: 0.30 },
    polymerData(1592, 7.5e9, 99e6, 151e6, 0.038, 0.44, 391, 43), ["fiber-reinforced-polymers"]);

  var p100 = addMaterial(
    "peakdemo-p100",
    "PeakDemo P100",
    "synthetic_commercial_grade",
    ["peek-like-polymers"],
    ["P100", "Peak Demo 100"],
    ["P100"],
    "PEEK-like synthetic commercial grade."
  );
  addState("peakdemo-p100-unfilled", p100, "unfilled", ["P100 unfilled", "P100 natural"], { formulation: "unfilled" },
    polymerData(1314, 3.8e9, 101e6, 168e6, 0.38, 0.27, 523, 72));
  addState("peakdemo-p100-gf30", p100, "30% glass-filled", ["P100 GF30", "P100 30GF"], { reinforcement: "glass_fiber", fiber_mass_fraction_1: 0.30 },
    polymerData(1511, 11.2e9, 151e6, 235e6, 0.032, 0.43, 533, 48), ["fiber-reinforced-polymers"]);
  addState("peakdemo-p100-cf30", p100, "30% carbon-filled", ["P100 CF30", "P100 30CF"], { reinforcement: "carbon_fiber", fiber_mass_fraction_1: 0.30 },
    polymerData(1417, 18.1e9, 209e6, 278e6, 0.024, 0.91, 538, 39), ["fiber-reinforced-polymers"]);

  var n6 = addMaterial(
    "nylondemo-n6",
    "NylonDemo N6",
    "synthetic_commercial_grade",
    ["nylons"],
    ["N6", "Nylon Demo 6"],
    ["N6"],
    "Near-collision with N66; moisture state changes observations."
  );
  addState("nylondemo-n6-dry", n6, "dry as molded", ["N6 dry"], { moisture_content_1: 0.002 },
    polymerData(1132, 2.9e9, 78e6, 112e6, 0.17, 0.25, 373, 68));
  addState("nylondemo-n6-conditioned", n6, "conditioned", ["N6 conditioned", "wet N6"], { moisture_content_1: 0.025 },
    polymerData(1140, 1.25e9, 49e6, 73e6, 0.61, 0.29, 353, 111));

  var n66 = addMaterial(
    "nylondemo-n66",
    "NylonDemo N66",
    "synthetic_commercial_grade",
    ["nylons"],
    ["N66", "Nylon Demo 66"],
    ["N66"],
    "Near-collision with N6."
  );
  addState("nylondemo-n66-dry", n66, "dry as molded", ["N66 dry"], { moisture_content_1: 0.002 },
    polymerData(1147, 3.15e9, 84e6, 126e6, 0.14, 0.27, 383, 63));
  addState("nylondemo-n66-conditioned", n66, "conditioned", ["N66 conditioned", "wet N66"], { moisture_content_1: 0.022 },
    polymerData(1153, 1.44e9, 55e6, 79e6, 0.48, 0.31, 363, 98));

  var p10 = addMaterial(
    "polydemo-pc-p10",
    "PolyDemo PC-P10",
    "synthetic_commercial_grade",
    ["polycarbonates"],
    ["P10", "PC P10"],
    ["PC-P10"],
    "General-purpose and glass-filled formulations."
  );
  addState("polydemo-pc-p10-unfilled", p10, "unfilled", ["PC-P10 natural", "P10 unfilled"], { formulation: "unfilled" },
    polymerData(1204, 2.35e9, 67e6, 96e6, 0.91, 0.21, 393, 721));
  addState("polydemo-pc-p10-gf20", p10, "20% glass-filled", ["PC-P10 GF20", "P10 GF20"], { reinforcement: "glass_fiber", fiber_mass_fraction_1: 0.20 },
    polymerData(1342, 5.7e9, 101e6, 148e6, 0.067, 0.32, 403, 174), ["fiber-reinforced-polymers"]);

  var a10 = addMaterial(
    "polydemo-abs-a10",
    "PolyDemo ABS-A10",
    "synthetic_commercial_grade",
    ["engineering-plastics"],
    ["A10", "ABS A10"],
    ["ABS-A10"],
    "Single-state synthetic injection grade."
  );
  addState("polydemo-abs-a10-injection", a10, "injection molded", ["A10 molded"], { product_form: "injection_molded" },
    polymerData(1041, 2.2e9, 46e6, 72e6, 0.34, 0.18, 353, 208));

  var f10 = addMaterial(
    "polydemo-ptfe-f10",
    "PolyDemo PTFE-F10",
    "synthetic_commercial_grade",
    ["fluoropolymers"],
    ["F10", "PTFE F10"],
    ["PTFE-F10"],
    "Single-state fluoropolymer-shaped fixture."
  );
  addState("polydemo-ptfe-f10-molded", f10, "compression molded", ["F10 molded"], { product_form: "compression_molded" },
    polymerData(2178, 0.54e9, 27e6, 21e6, 2.6, 0.25, 493, 151));

  var h10 = addMaterial(
    "polydemo-hdpe-h10",
    "PolyDemo HDPE-H10",
    "synthetic_commercial_grade",
    ["commodity-plastics"],
    ["H10", "HDPE H10"],
    ["HDPE-H10"],
    "Commodity-plastic-shaped fixture."
  );
  addState("polydemo-hdpe-h10-extruded", h10, "extruded", ["H10 extruded"], { product_form: "extrusion" },
    polymerData(957, 1.05e9, 31e6, 34e6, 5.2, 0.49, 343, 186));

  /*
   * Ceramics and glasses are direct lookup materials: no artificial “as
   * specified” state is created merely to satisfy a hierarchy.
   */
  var a96 = addMaterial(
    "ceramdemo-a96",
    "CeramDemo A96",
    "synthetic_commercial_grade",
    ["technical-ceramics"],
    ["A96", "96 alumina demo"],
    ["A96"],
    "Direct data-bearing material."
  );
  addDirectData(a96, ceramicData(3720, 302e9, 331e6, 2050e6, 24, 1373));

  var a995 = addMaterial(
    "ceramdemo-a995",
    "CeramDemo A995",
    "synthetic_commercial_grade",
    ["technical-ceramics"],
    ["A995", "99.5 alumina demo"],
    ["A995"],
    "Near-collision with A96."
  );
  addDirectData(a995, ceramicData(3892, 371e9, 386e6, 2480e6, 31, 1473));

  var z3y = addMaterial(
    "ceramdemo-z3y",
    "CeramDemo Z3Y",
    "synthetic_commercial_grade",
    ["technical-ceramics"],
    ["Z3Y", "zirconia demo"],
    ["Z3Y"],
    "Toughened ceramic-shaped fixture."
  );
  addDirectData(z3y, ceramicData(6050, 214e9, 918e6, 2290e6, 2.8, 1273));

  var sics = addMaterial(
    "ceramdemo-sic-s",
    "CeramDemo SiC-S",
    "synthetic_commercial_grade",
    ["technical-ceramics"],
    ["SiC-S", "silicon carbide demo"],
    ["SiC-S"],
    "Thermally conductive ceramic-shaped fixture."
  );
  addDirectData(sics, ceramicData(3165, 419e9, 512e6, 3490e6, 118, 1673));

  var b33 = addMaterial(
    "glassdemo-b33",
    "GlassDemo B33",
    "synthetic_standard_grade",
    ["glasses"],
    ["B33", "borosilicate demo"],
    ["B33"],
    "Bulk glass, not glass-fiber composite."
  );
  addDirectData(b33, ceramicData(2241, 63e9, 68e6, 822e6, 1.18, 723));

  var sl90 = addMaterial(
    "glassdemo-sl90",
    "GlassDemo SL90",
    "synthetic_standard_grade",
    ["glasses"],
    ["SL90", "soda lime glass demo"],
    ["SL90"],
    "Near-collision test for glass queries."
  );
  addDirectData(sl90, ceramicData(2498, 71e9, 73e6, 902e6, 0.94, 693));

  /*
   * Composite systems carry stable layups as states. Direction stays on the
   * observation, because one laminate can be tested in several directions.
   */
  var cfe1 = addMaterial(
    "lamdemo-cf-e1",
    "LamDemo CF-E1",
    "synthetic_composite_system",
    ["fiber-reinforced-polymers"],
    ["CF-E1", "carbon epoxy E1"],
    ["CF-E1"],
    "Synthetic carbon-fiber/epoxy system."
  );
  addState("lamdemo-cf-e1-ud", cfe1, "UD laminate", ["CF-E1 UD", "CF E1 zero degree"], { layup: "unidirectional" },
    compositeData(1582, 137e9, 1710e6, 982e6, 5.3, { orientation: "L", fiber_volume_fraction_1: 0.61 }));
  addState("lamdemo-cf-e1-qi", cfe1, "quasi-isotropic laminate", ["CF-E1 QI"], { layup: "quasi_isotropic" },
    compositeData(1574, 54e9, 681e6, 493e6, 1.8, { orientation: "in_plane", fiber_volume_fraction_1: 0.59 }));

  var gfp1 = addMaterial(
    "lamdemo-gf-p1",
    "LamDemo GF-P1",
    "synthetic_composite_system",
    ["fiber-reinforced-polymers"],
    ["GF-P1", "glass epoxy P1"],
    ["GF-P1"],
    "Synthetic glass-fiber/polymer system."
  );
  addState("lamdemo-gf-p1-ud", gfp1, "UD laminate", ["GF-P1 UD"], { layup: "unidirectional" },
    compositeData(1934, 44e9, 1091e6, 583e6, 0.66, { orientation: "L", fiber_volume_fraction_1: 0.57 }));
  addState("lamdemo-gf-p1-woven", gfp1, "woven laminate", ["GF-P1 woven"], { layup: "woven_0_90" },
    compositeData(1888, 25e9, 482e6, 371e6, 0.51, { orientation: "in_plane", fiber_volume_fraction_1: 0.52 }));

  /*
   * Wood remains one lookup identity. Moisture and grain direction intentionally
   * remain observation conditions rather than exploding into pseudo-materials.
   */
  var woodW1 = addMaterial(
    "wooddemo-w1",
    "WoodDemo W1",
    "synthetic_species",
    ["woods"],
    ["W1 timber", "wood W1"],
    ["W1"],
    "One identity with moisture- and direction-conditioned observations."
  );
  addDirectData(woodW1, {
    density: [
      { value: 528, conditions: { moisture_content_1: 0.12 } },
      { value: 771, conditions: { moisture_content_1: 0.31 } }
    ],
    youngs_modulus: [
      { value: 12.4e9, conditions: { moisture_content_1: 0.12, orientation: "longitudinal" } },
      { value: 1.08e9, conditions: { moisture_content_1: 0.12, orientation: "radial" } }
    ],
    flexural_strength: {
      value: 89e6,
      conditions: { moisture_content_1: 0.12, orientation: "longitudinal" }
    },
    compressive_strength: [
      { value: 47e6, conditions: { moisture_content_1: 0.12, orientation: "longitudinal" } },
      { value: 7.2e6, conditions: { moisture_content_1: 0.12, orientation: "radial" } }
    ],
    thermal_conductivity: {
      value: 0.14,
      conditions: { moisture_content_1: 0.12, orientation: "radial" }
    }
  });

  var s50 = addMaterial(
    "elastodemo-s50a",
    "ElastoDemo S50A",
    "synthetic_commercial_grade",
    ["elastomers"],
    ["S50A", "50A silicone demo"],
    ["S50A"],
    "Shore designation may collide with product codes."
  );
  addDirectData(s50, elastomerData(1121, 7.8e6, 4.8, 50, 473));

  var s70 = addMaterial(
    "elastodemo-s70a",
    "ElastoDemo S70A",
    "synthetic_commercial_grade",
    ["elastomers"],
    ["S70A", "70A silicone demo"],
    ["S70A"],
    "Near-duplicate hardness grade."
  );
  addDirectData(s70, elastomerData(1190, 10.4e6, 3.4, 70, 483));

  var e60 = addMaterial(
    "elastodemo-e60a",
    "ElastoDemo E60A",
    "synthetic_commercial_grade",
    ["elastomers"],
    ["E60A", "60A EPDM demo"],
    ["E60A"],
    "Different chemistry with a similar hardness designation."
  );
  addDirectData(e60, elastomerData(1084, 14.1e6, 4.1, 60, 413));

  var pu40 = addMaterial(
    "foamdemo-pu40",
    "FoamDemo PU-40",
    "synthetic_commercial_grade",
    ["foams"],
    ["PU40", "PU foam 40"],
    ["PU-40"],
    "Low-density foam-shaped fixture."
  );
  addDirectData(pu40, foamData(41, 0.19e6, 0.032, 353));

  var pu80 = addMaterial(
    "foamdemo-pu80",
    "FoamDemo PU-80",
    "synthetic_commercial_grade",
    ["foams"],
    ["PU80", "PU foam 80"],
    ["PU-80"],
    "Near-collision with PU-40."
  );
  addDirectData(pu80, foamData(82, 0.61e6, 0.039, 363));

  root.MaterialsPrototypeCorpus = {
    schema_version: "prototype-taxonomy-material-state-observation-0.2",
    corpus_version: VERSION,
    build_version: BUILD,
    synthetic: true,
    warning: "Fabricated values for interface and schema testing only. Not engineering data.",
    taxa: taxa,
    materials: materials,
    states: states,
    observations: observations,
    properties: properties,
    property_groups: propertyGroups
  };
})(window);
