const formatter = new Intl.NumberFormat(undefined, {
  minimumFractionDigits: 2,
  maximumFractionDigits: 3,
});

function formatMu(value) {
  if (typeof value !== "number" || Number.isNaN(value)) return "—";
  if (!Number.isFinite(value)) return value.toString();
  return formatter.format(value);
}

function buildCandidatePaths(target) {
  const candidates = new Set();
  const prefixes = ["", ".", "..", "../..", "../../..", "../../../.."];
  prefixes.forEach((prefix) => {
    const trimmed = prefix.replace(/\/+$/, "");
    const path = trimmed ? `${trimmed}/${target}` : target;
    candidates.add(path);
  });
  const segments = window.location.pathname.split("/").filter(Boolean);
  for (let i = 1; i <= segments.length; i += 1) {
    const prefix = segments.slice(0, i).join("/");
    candidates.add(`/${prefix}/${target}`);
  }
  candidates.add(`/${target}`);
  return Array.from(candidates);
}

function createListItem(label, subtitle, isActive, onSelect) {
  const li = document.createElement("li");
  const button = document.createElement("button");
  button.type = "button";
  button.className = "unit-chip" + (isActive ? " is-active" : "");
  button.innerHTML = `
    <span class="unit-symbol">${label}</span>
    ${
      subtitle
        ? `<span class="unit-description">— ${subtitle}</span>`
        : "<span class=\"unit-description\"></span>"
    }
  `;
  button.addEventListener("click", onSelect);
  li.appendChild(button);
  return li;
}

function renderList(listEl, items) {
  listEl.innerHTML = "";
  items.forEach((item) => listEl.appendChild(item));
}

export function initFrictionLookup({ container }) {
  if (!container) return;

  const refs = {
    docDescription: container.querySelector("[data-role='doc-description']"),
    docEquations: container.querySelector("[data-role='doc-equations']"),
    infoMessage: container.querySelector("[data-role='info-message']"),
    infoNotes: container.querySelector("[data-role='info-notes']"),
    infoApplications: container.querySelector("[data-role='info-applications']"),
    infoComparables: container.querySelector("[data-role='info-comparables']"),
    infoReference: container.querySelector("[data-role='info-reference']"),
    infoPairLabel: container.querySelector("[data-role='info-pair-label']"),
    infoCondition: container.querySelector("[data-role='info-condition']"),
    materialList: container.querySelector("[data-role='material-list']"),
    materialSearch: container.querySelector("[data-role='material-search']"),
    pairList: container.querySelector("[data-role='pair-list']"),
    conditionRow: container.querySelector("[data-role='condition-row']"),
    staticTypical: container.querySelector("[data-role='result-static-typical']"),
    staticRange: container.querySelector("[data-role='result-static-range']"),
    kineticTypical: container.querySelector("[data-role='result-kinetic-typical']"),
    kineticRange: container.querySelector("[data-role='result-kinetic-range']"),
  };

  const state = {
    catalog: {
      materials: {},
      combinations: [],
    },
    pairIndex: {},
    selectedMaterial: null,
    selectedPairKey: null,
    selectedCondition: null,
    docInfo: null,
    lastResult: null,
    filters: {
      material: "",
      pair: "",
    },
  };

  let pyodideInstance;
  let frictionModule;
  let utilsModule;

  function setMessage(kind, message) {
    if (!refs.infoMessage) return;
    refs.infoMessage.dataset.state = kind;
    refs.infoMessage.textContent = message || "";
    refs.infoMessage.style.display = message ? "block" : "none";
  }

  function updateDocDisplay() {
    if (!state.docInfo) return;
    if (refs.docDescription) {
      refs.docDescription.textContent = state.docInfo.description || "";
    }
    if (refs.docEquations) {
      const latex = state.docInfo.latex || "";
      if (latex.trim().length > 0) {
        const lines = latex
          .split("\n")
          .map((line) => line.trim())
          .filter(Boolean);
        refs.docEquations.innerHTML = lines
          .map((line) => `<div class="equation-line">$$${line}$$</div>`)
          .join("");
        if (window.MathJax && typeof window.MathJax.typesetPromise === "function") {
          window.MathJax.typesetPromise();
        }
      } else {
        refs.docEquations.textContent = "";
      }
    }
  }

  function ensureSelections() {
    const materials = Object.keys(state.catalog.materials);
    if (!materials.length) return;

    if (!state.selectedMaterial || !state.catalog.materials[state.selectedMaterial]) {
      const sorted = materials.sort((a, b) =>
        state.catalog.materials[a].name.localeCompare(state.catalog.materials[b].name),
      );
      state.selectedMaterial = sorted[0];
    }

    const combos = state.catalog.combinations.filter((combo) =>
      combo.materials.includes(state.selectedMaterial),
    );
    if (!combos.length) {
      state.selectedPairKey = null;
      state.selectedCondition = null;
      return;
    }

    const currentPair = state.selectedPairKey ? state.pairIndex[state.selectedPairKey] : null;
    const pairHasMaterial =
      currentPair && currentPair.materials && currentPair.materials.includes(state.selectedMaterial);
    if (!state.selectedPairKey || !currentPair || !pairHasMaterial) {
      state.selectedPairKey = combos[0].pair_key;
    }

    const pair = state.selectedPairKey ? state.pairIndex[state.selectedPairKey] : null;
    if (pair && Array.isArray(pair.conditions) && pair.conditions.length) {
      if (!pair.conditions.includes(state.selectedCondition)) {
        state.selectedCondition = pair.conditions[0];
      }
    } else {
      state.selectedCondition = null;
    }
  }

  function renderMaterials() {
    if (!refs.materialList) return;
    const entries = Object.entries(state.catalog.materials).map(([key, meta]) => ({
      key,
      name: meta.name,
      category: meta.category,
    }));
    entries.sort((a, b) => a.name.localeCompare(b.name));
    const filter = (state.filters.material || "").trim().toLowerCase();
    const items = entries
      .filter((entry) => {
        if (!filter) return true;
        return (
          entry.name.toLowerCase().includes(filter) ||
          (entry.category || "").toLowerCase().includes(filter)
        );
      })
      .map((entry) =>
        createListItem(
          entry.name,
          entry.category || "",
          state.selectedMaterial === entry.key,
          () => {
            state.selectedMaterial = entry.key;
            ensureSelections();
            renderMaterials();
            renderPairs();
            renderConditions();
            fetchResult();
          },
        ),
      );
    renderList(refs.materialList, items);
  }

  function renderPairs() {
    if (!refs.pairList) return;
    const combos = state.catalog.combinations.filter((combo) =>
      combo.materials.includes(state.selectedMaterial),
    );
    combos.sort((a, b) => a.label.localeCompare(b.label));
    if (combos.length) {
      const selectedStillValid = combos.some((combo) => combo.pair_key === state.selectedPairKey);
      if (!selectedStillValid) {
        state.selectedPairKey = combos[0].pair_key;
      }
    } else {
      state.selectedPairKey = null;
    }
    const items = combos.map((combo) => {
      const other =
        combo.materials[0] === state.selectedMaterial
          ? combo.materials[1]
          : combo.materials[0];
      const otherName = state.catalog.materials[other]
        ? state.catalog.materials[other].name
        : other;
      const subtitle = combo.conditions.map((cond) => cond.toUpperCase()).join(" • ");
      return createListItem(otherName, subtitle, state.selectedPairKey === combo.pair_key, () => {
        state.selectedPairKey = combo.pair_key;
        ensureSelections();
        renderPairs();
        renderConditions();
        fetchResult();
      });
    });
    renderList(refs.pairList, items);
  }

  function renderConditions() {
    if (!refs.conditionRow) return;
    refs.conditionRow.innerHTML = "";
    const pair = state.pairIndex[state.selectedPairKey];
    if (!pair) return;

    pair.conditions.forEach((condition) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "quantity-chip" + (state.selectedCondition === condition ? " is-active" : "");
      button.textContent = condition.toUpperCase();
      button.addEventListener("click", () => {
        if (state.selectedCondition === condition) return;
        state.selectedCondition = condition;
        renderConditions();
        fetchResult();
      });
      refs.conditionRow.appendChild(button);
    });
  }

  function updateResultDisplay() {
    const result = state.lastResult;
    if (!result) {
      if (refs.staticTypical) refs.staticTypical.textContent = "—";
      if (refs.staticRange) refs.staticRange.textContent = "Static range —";
      if (refs.kineticTypical) refs.kineticTypical.textContent = "—";
      if (refs.kineticRange) refs.kineticRange.textContent = "Kinetic range —";
      if (refs.infoPairLabel) refs.infoPairLabel.textContent = "No pairing selected";
      if (refs.infoCondition) refs.infoCondition.textContent = "";
      if (refs.infoNotes) refs.infoNotes.textContent = "Select a valid material pair to view guidance.";
      if (refs.infoApplications) refs.infoApplications.innerHTML = "";
      if (refs.infoComparables) refs.infoComparables.innerHTML = "";
      if (refs.infoReference) refs.infoReference.textContent = "";
      return;
    }

    if (refs.staticTypical) {
      refs.staticTypical.textContent = formatMu(result.mu_static_typical);
    }
    if (refs.staticRange) {
      refs.staticRange.textContent = `Range: ${formatMu(result.mu_static_min)} – ${formatMu(
        result.mu_static_max,
      )}`;
    }
    if (refs.kineticTypical) {
      refs.kineticTypical.textContent = formatMu(result.mu_kinetic_typical);
    }
    if (refs.kineticRange) {
      refs.kineticRange.textContent = `Range: ${formatMu(result.mu_kinetic_min)} – ${formatMu(
        result.mu_kinetic_max,
      )}`;
    }
    if (refs.infoPairLabel) {
      refs.infoPairLabel.textContent = `${result.material_a_name} ↔ ${result.material_b_name}`;
    }
    if (refs.infoCondition) {
      refs.infoCondition.textContent = result.surface_condition.toUpperCase();
    }
    if (refs.infoNotes) {
      refs.infoNotes.textContent = result.notes || "";
    }
    if (refs.infoApplications) {
      refs.infoApplications.innerHTML = "";
      (result.typical_applications || []).forEach((item) => {
        const li = document.createElement("li");
        li.textContent = item;
        refs.infoApplications.appendChild(li);
      });
    }
    if (refs.infoComparables) {
      refs.infoComparables.innerHTML = "";
      (result.comparable_pairs || []).forEach((item) => {
        const li = document.createElement("li");
        li.textContent = item;
        refs.infoComparables.appendChild(li);
      });
    }
    if (refs.infoReference) {
      refs.infoReference.textContent = result.reference || "";
    }
  }

  function getOtherMaterialKey(pair, selected) {
    if (!pair) return selected;
    const [a, b] = pair.materials;
    if (selected === a) return b;
    if (selected === b) return a;
    return a;
  }

  async function fetchResult() {
    if (!frictionModule) return;
    const pair = state.pairIndex[state.selectedPairKey];
    if (!pair) return;
    const condition = state.selectedCondition;
    if (!condition) return;

    const other = getOtherMaterialKey(pair, state.selectedMaterial);
    try {
      setMessage("info", "Evaluating lookup…");
      const pyResult = frictionModule.lookup_coefficient_of_friction(
        state.selectedMaterial,
        other,
        condition,
      );
      const result = pyResult.toJs({ create_proxies: false, dict_converter: Object.fromEntries });
      pyResult.destroy();
      state.lastResult = result;
      setMessage("", "");
      updateResultDisplay();
    } catch (error) {
      setMessage("error", error.message || "Lookup failed.");
    }
  }

  async function boot() {
    try {
      setMessage("info", "Loading Python runtime…");
      pyodideInstance = await loadPyodide();
      setMessage("info", "Loading friction library…");

      const utilsCandidates = buildCandidatePaths("pycalcs/utils.py");
      const frictionCandidates = buildCandidatePaths("pycalcs/friction.py");

      await pyodideInstance.runPythonAsync(`
from pyodide.http import pyfetch

async def fetch_to_file(paths, destination):
    for path in paths:
        response = await pyfetch(path)
        if response.ok:
            with open(destination, 'w', encoding='utf-8') as f:
                f.write(await response.string())
            return path
    raise OSError(f"Failed to fetch {destination}.")

utils_candidates = ${JSON.stringify(utilsCandidates)}
friction_candidates = ${JSON.stringify(frictionCandidates)}

await fetch_to_file(utils_candidates, 'utils.py')
await fetch_to_file(friction_candidates, 'friction.py')

import utils
import friction
      `);

      frictionModule = pyodideInstance.globals.get("friction");
      utilsModule = pyodideInstance.globals.get("utils");

      const catalogProxy = frictionModule.get_friction_catalog();
      state.catalog = catalogProxy.toJs({
        create_proxies: false,
        dict_converter: Object.fromEntries,
      });
      catalogProxy.destroy();

      state.pairIndex = {};
      (state.catalog.combinations || []).forEach((combo) => {
        state.pairIndex[combo.pair_key] = combo;
      });

      const docProxy = utilsModule.get_documentation("friction", "lookup_coefficient_of_friction");
      state.docInfo = docProxy.toJs({ create_proxies: false, dict_converter: Object.fromEntries });
      docProxy.destroy();
      updateDocDisplay();

      if (refs.materialSearch && state.docInfo && state.docInfo.parameters) {
        const materialTooltip = state.docInfo.parameters.material_a || "";
        const pairTooltip = state.docInfo.parameters.material_b || "";
        const conditionTooltip = state.docInfo.parameters.surface_condition || "";
        refs.materialSearch.title = materialTooltip;
        if (refs.pairList) refs.pairList.title = pairTooltip;
        if (refs.conditionRow) refs.conditionRow.title = conditionTooltip;
      }

      ensureSelections();
      renderMaterials();
      renderPairs();
      renderConditions();
      fetchResult();
      setMessage("", "");
    } catch (error) {
      setMessage("error", error.message || "Failed to initialise tool.");
    }
  }

  if (refs.materialSearch) {
    refs.materialSearch.addEventListener("input", (event) => {
      state.filters.material = event.target.value || "";
      renderMaterials();
    });
  }

  boot();
}
