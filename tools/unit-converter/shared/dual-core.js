const BASE_UNITS = {
  length: "m",
  area: "m^2",
  volume: "m^3",
  mass: "kg",
  force: "N",
  torque: "N·m",
  pressure: "Pa",
  energy: "J",
  power: "W",
  density: "kg/m^3",
  temperature: "K",
  angle: "rad",
};

const QUANTITY_LABELS = {
  length: "Length",
  area: "Area",
  volume: "Volume",
  mass: "Mass",
  force: "Force",
  torque: "Torque",
  pressure: "Pressure",
  energy: "Energy",
  power: "Power",
  density: "Density",
  temperature: "Temperature",
  angle: "Angle",
};

const COMPARABLES = {
  length: [
    { label: "Credit card width", value: 0.0856 },
    { label: "A4 paper height", value: 0.297 },
    { label: "Basketball hoop height", value: 3.048 },
    { label: "City bus length", value: 12.0 },
    { label: "Marathon distance", value: 42195.0 },
    { label: "Geostationary orbit altitude", value: 35786000.0 },
  ],
  area: [
    { label: "Sheet of A4 paper", value: 0.06237 },
    { label: "Ping pong table", value: 5.0 },
    { label: "Basketball court", value: 420.0 },
    { label: "Soccer pitch", value: 7140.0 },
    { label: "City block (NYC avg)", value: 20000.0 },
  ],
  volume: [
    { label: "Shot glass", value: 0.000044 },
    { label: "Coffee mug", value: 0.00035 },
    { label: "Household bathtub", value: 0.3 },
    { label: "Shipping container (40 ft)", value: 67.0 },
    { label: "Olympic swimming pool", value: 2500.0 },
  ],
  mass: [
    { label: "AA battery", value: 0.024 },
    { label: "Laptop computer", value: 1.8 },
    { label: "Adult human", value: 70.0 },
    { label: "Grand piano", value: 480.0 },
    { label: "Mid-size car", value: 1500.0 },
  ],
  force: [
    { label: "Apple weight", value: 1.0 },
    { label: "Typical door closer", value: 30.0 },
    { label: "Bodyweight squat (person)", value: 700.0 },
    { label: "Industrial press stroke", value: 20000.0 },
    { label: "Boeing 737 thrust (per engine)", value: 120000.0 },
  ],
  torque: [
    { label: "Jar lid twist", value: 6.0 },
    { label: "Car wheel lug nut", value: 120.0 },
    { label: "Electric scooter hub", value: 350.0 },
    { label: "Truck crankshaft", value: 3000.0 },
    { label: "Modern wind turbine", value: 45000.0 },
  ],
  pressure: [
    { label: "Atmospheric pressure", value: 101325.0 },
    { label: "Car tire", value: 240000.0 },
    { label: "Fire hose", value: 700000.0 },
    { label: "Hydraulic press", value: 15000000.0 },
    { label: "Deep ocean (Mariana Trench)", value: 1086000000.0 },
  ],
  energy: [
    { label: "AAA battery", value: 5400.0 },
    { label: "Smartphone charge", value: 18000.0 },
    { label: "1 kg TNT", value: 4184000.0 },
    { label: "Home electricity (1 day)", value: 8640000.0 },
    { label: "Lightning strike", value: 5000000000.0 },
  ],
  power: [
    { label: "Human at rest", value: 100.0 },
    { label: "LED light bulb", value: 12.0 },
    { label: "Microwave oven", value: 1100.0 },
    { label: "Car engine", value: 75000.0 },
    { label: "Grid-scale wind turbine", value: 3000000.0 },
  ],
  density: [
    { label: "Air (sea level)", value: 1.225 },
    { label: "Gasoline", value: 740.0 },
    { label: "Fresh water", value: 998.0 },
    { label: "Concrete", value: 2400.0 },
    { label: "Lead", value: 11340.0 },
  ],
  temperature: [
    { label: "Absolute zero", value: 0.0 },
    { label: "Freezing water", value: 273.15 },
    { label: "Room temperature", value: 295.15 },
    { label: "Body temperature", value: 310.15 },
    { label: "Baking oven", value: 473.15 },
    { label: "Soldering iron tip", value: 773.15 },
  ],
  angle: [
    { label: "30°", value: Math.PI / 6 },
    { label: "45°", value: Math.PI / 4 },
    { label: "60°", value: Math.PI / 3 },
    { label: "90°", value: Math.PI / 2 },
    { label: "180°", value: Math.PI },
    { label: "Full turn", value: 2 * Math.PI },
  ],
};

const DEFAULT_COMPARABLE_LIMIT = 6;

function formatNumber(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "—";
  const abs = Math.abs(num);
  if ((abs >= 1000 || abs < 1e-3) && abs !== 0) {
    return num.toExponential(5).replace(/(\.0+)?e/, "e");
  }
  return Number.parseFloat(num.toFixed(6)).toString();
}

function formatForInput(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "";
  const abs = Math.abs(num);
  if ((abs >= 1e7 || abs !== 0 && abs < 1e-4)) {
    return num.toExponential(8);
  }
  let asString = num.toPrecision(12);
  if (asString.indexOf("e") === -1) {
    asString = asString.replace(/(\.\d*?[1-9])0+$/g, "$1").replace(/\.0+$/, "");
  }
  return asString;
}

function ratioDescription(ratio) {
  if (!Number.isFinite(ratio) || ratio === 0) return "—";
  const abs = Math.abs(ratio);
  if (abs === 1) return "Roughly the same magnitude";
  if (abs > 1) {
    return `${abs.toFixed(2)}× your value`;
  }
  return `${(1 / abs).toFixed(2)}× smaller than your value`;
}

function titleCase(text) {
  if (!text) return "";
  const custom = QUANTITY_LABELS[text.toLowerCase()];
  if (custom) return custom;
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function initDualConverter({
  container,
  comparablesLimit = DEFAULT_COMPARABLE_LIMIT,
} = {}) {
  if (!container) {
    throw new Error("Dual converter container not provided.");
  }

  const refs = {
    quantityRow: container.querySelector("[data-role='quantity-row']"),
    leftInput: container.querySelector("[data-role='value-input'][data-side='left']"),
    rightInput: container.querySelector("[data-role='value-input'][data-side='right']"),
    leftSearch: container.querySelector("[data-role='search-input'][data-side='left']"),
    rightSearch: container.querySelector("[data-role='search-input'][data-side='right']"),
    leftUnitList: container.querySelector("[data-role='unit-list'][data-side='left']"),
    rightUnitList: container.querySelector("[data-role='unit-list'][data-side='right']"),
    infoQuantity: container.querySelector("[data-role='info-quantity']"),
    infoBase: container.querySelector("[data-role='info-base']"),
    infoUnits: container.querySelector("[data-role='info-units']"),
    infoFactorCard: container.querySelector("[data-role='info-factor-card']"),
    infoFactorValue: container.querySelector("[data-role='info-factor-value']"),
    infoMessage: container.querySelector("[data-role='info-message']"),
    comparisons: container.querySelector("[data-role='info-comparisons']"),
    infoUpdated: container.querySelector("[data-role='info-updated']"),
  };

  const missingRef = Object.entries(refs)
    .filter(([, node]) => !node)
    .map(([key]) => key);

  if (missingRef.length > 0) {
    throw new Error(
      `Dual converter markup missing required elements: ${missingRef.join(", ")}`
    );
  }

  const state = {
    quantity: null,
    leftUnit: null,
    rightUnit: null,
    leftValue: 1,
    rightValue: 1,
    activeSide: "left",
    filters: {
      left: "",
      right: "",
    },
    catalog: {},
    lastResult: null,
  };

  let pyodideInstance;
  let unitsModule;
  let syncing = false;

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

  function convertScalar(quantity, fromUnit, toUnit, value) {
    if (!unitsModule) return Number.NaN;
    let proxy;
    try {
      proxy = unitsModule.convert_value(quantity, fromUnit, toUnit, value);
      let raw = proxy;
      if (proxy && typeof proxy.toJs === "function") {
        raw = proxy.toJs({ create_proxies: false });
      }
      return Number(raw);
    } catch (error) {
      return Number.NaN;
    } finally {
      if (proxy && typeof proxy.destroy === "function") {
        proxy.destroy();
      }
    }
  }

  function setMessage(kind, message) {
    if (!refs.infoMessage) return;
    refs.infoMessage.dataset.state = kind;
    refs.infoMessage.textContent = message || "";
    refs.infoMessage.style.display = message ? "block" : "none";
  }

  function ensureQuantityInitialized() {
    const quantities = Object.keys(state.catalog);
    if (quantities.length === 0) return;
    if (!state.quantity || !state.catalog[state.quantity]) {
      state.quantity = quantities.sort()[0];
    }
    const unitList = Object.keys(state.catalog[state.quantity]);
    state.leftUnit = unitList[0] || null;
    state.rightUnit = unitList[1] || unitList[0] || null;
    if (refs.leftSearch) refs.leftSearch.value = "";
    if (refs.rightSearch) refs.rightSearch.value = "";
    state.filters.left = "";
    state.filters.right = "";
    state.leftValue = Number(state.leftValue) || 1;
    state.rightValue = Number(state.rightValue) || state.leftValue;
    state.activeSide = "left";
    refs.leftInput.value = formatForInput(state.leftValue);
    refs.rightInput.value = formatForInput(state.rightValue);
  }

  function renderQuantityChips() {
    refs.quantityRow.innerHTML = "";
    const quantities = Object.keys(state.catalog).sort();
    quantities.forEach((quantity) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "quantity-chip" + (state.quantity === quantity ? " is-active" : "");
      button.textContent = titleCase(quantity);
      button.addEventListener("click", () => {
        if (state.quantity === quantity) return;
        state.quantity = quantity;
        ensureQuantityInitialized();
        renderQuantityChips();
        renderUnitList("left");
        renderUnitList("right");
        convert(state.activeSide);
      });
      refs.quantityRow.appendChild(button);
    });
  }

  function createUnitButton(symbol, description, isActive, onSelect) {
    const li = document.createElement("li");
    li.className = "unit-option";
    const button = document.createElement("button");
    button.type = "button";
    button.className = "unit-chip" + (isActive ? " is-active" : "");
    button.innerHTML = `
      <span class="unit-symbol">${symbol}</span>
      <span class="unit-description">${description}</span>
    `;
    button.addEventListener("click", () => onSelect(symbol));
    li.appendChild(button);
    return li;
  }

  function renderUnitList(side) {
    const unitListEl = side === "left" ? refs.leftUnitList : refs.rightUnitList;
    const filterValue = (state.filters[side] || "").toLowerCase();
    unitListEl.innerHTML = "";
    const units = state.catalog[state.quantity] || {};
    const entries = Object.entries(units);

    const filtered = entries.filter(([symbol, info]) => {
      if (!filterValue) return true;
      return (
        symbol.toLowerCase().includes(filterValue) ||
        info.name.toLowerCase().includes(filterValue)
      );
    });

    const currentUnit = side === "left" ? state.leftUnit : state.rightUnit;
    filtered.forEach(([symbol, info]) => {
      const item = createUnitButton(symbol, info.name, currentUnit === symbol, (selected) => {
        if (side === "left") {
          state.leftUnit = selected;
        } else {
          state.rightUnit = selected;
        }
        renderUnitList(side);
        convert(state.activeSide);
      });
      unitListEl.appendChild(item);
    });
  }

  function handleSearchInput(side, value) {
    state.filters[side] = value || "";
    renderUnitList(side);
  }

  function updateComparisons(result) {
    const list = refs.comparisons;
    list.innerHTML = "";
    const quantityKey = state.quantity;
    const comparables = COMPARABLES[quantityKey];
    if (!comparables || comparables.length === 0) {
      const empty = document.createElement("p");
      empty.className = "comparison-empty";
      empty.textContent = `No comparison data yet for ${titleCase(quantityKey)}.`;
      list.appendChild(empty);
      return;
    }

    const baseUnit = BASE_UNITS[quantityKey];
    const leftUnit = state.leftUnit;
    const rightUnit = state.rightUnit;
    const activeSide = state.activeSide;
    const leftValue = Number(state.leftValue);
    const rightValue = Number(state.rightValue);

    comparables.slice(0, comparablesLimit).forEach((item) => {
      const rightConverted = rightUnit
        ? convertScalar(quantityKey, baseUnit, rightUnit, item.value)
        : Number.NaN;
      const leftConverted = leftUnit
        ? convertScalar(quantityKey, baseUnit, leftUnit, item.value)
        : Number.NaN;

      if (!Number.isFinite(rightConverted) && !Number.isFinite(leftConverted)) {
        return;
      }

      const comparison = document.createElement("div");
      comparison.className = "comparison-card";
      const ratioSource =
        activeSide === "left"
          ? leftConverted / leftValue
          : rightConverted / rightValue;

      comparison.innerHTML = `
        <div class="comparison-label">${item.label}</div>
        <div class="comparison-values">
          <span>${Number.isFinite(rightConverted) ? formatNumber(rightConverted) : "—"} ${rightUnit || ""}</span>
          <span class="comparison-secondary">${Number.isFinite(leftConverted) ? formatNumber(leftConverted) : "—"} ${leftUnit || ""}</span>
        </div>
        <div class="comparison-ratio">${ratioDescription(ratioSource)}</div>
      `;
      list.appendChild(comparison);
    });
  }

  function updateInfo(result) {
    if (refs.infoQuantity) {
      refs.infoQuantity.textContent = titleCase(state.quantity);
    }
    if (refs.infoBase) {
      const baseUnit = BASE_UNITS[state.quantity] || "SI";
      refs.infoBase.textContent = `${formatNumber(result.base_value)} ${baseUnit}`;
    }
    if (refs.infoUnits) {
      refs.infoUnits.textContent = `${state.leftUnit || "—"} ↔ ${state.rightUnit || "—"}`;
    }
    if (refs.infoFactorCard && refs.infoFactorValue) {
      if (result.has_multiplier_only) {
        refs.infoFactorCard.style.display = "";
        refs.infoFactorValue.textContent = formatNumber(result.multiplier);
      } else {
        refs.infoFactorCard.style.display = "none";
      }
    }
    if (refs.infoUpdated) {
      const timestamp = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
      refs.infoUpdated.textContent = `Updated ${timestamp}`;
    }
    updateComparisons(result);
  }

  function convert(sourceSide) {
    if (!unitsModule || !state.quantity || syncing) return;
    const fromUnit = sourceSide === "left" ? state.leftUnit : state.rightUnit;
    const toUnit = sourceSide === "left" ? state.rightUnit : state.leftUnit;
    const fromValue = sourceSide === "left" ? Number(state.leftValue) : Number(state.rightValue);
    if (!fromUnit || !toUnit || !Number.isFinite(fromValue)) return;

    try {
      const pyResult = unitsModule.convert_units(
        state.quantity,
        fromUnit,
        toUnit,
        fromValue
      );
      const result = pyResult.toJs({ create_proxies: false, dict_converter: Object.fromEntries });
      pyResult.destroy();
      if (result.error) {
        setMessage("error", result.error);
        return;
      }

      syncing = true;
      if (sourceSide === "left") {
        state.rightValue = Number(result.converted_value);
        refs.rightInput.value = formatForInput(state.rightValue);
        refs.leftInput.value = formatForInput(fromValue);
      } else {
        state.leftValue = Number(result.converted_value);
        refs.leftInput.value = formatForInput(state.leftValue);
        refs.rightInput.value = formatForInput(fromValue);
      }
      syncing = false;

      state.activeSide = sourceSide;
      state.lastResult = result;
      setMessage("info", "");
      updateInfo(result);
    } catch (error) {
      syncing = false;
      setMessage("error", error.message || "Conversion failed.");
    }
  }

  function handleValueInput(side, rawValue) {
    if (syncing) return;
    const numeric = Number(rawValue);
    if (!Number.isFinite(numeric)) return;
    if (side === "left") {
      state.leftValue = numeric;
    } else {
      state.rightValue = numeric;
    }
    state.activeSide = side;
    convert(side);
  }

  async function boot() {
    try {
      setMessage("info", "Loading Python runtime…");
      pyodideInstance = await loadPyodide();
      await pyodideInstance.loadPackage("micropip");
      setMessage("info", "Loading conversion library…");
      const unitsCandidates = buildCandidatePaths("pycalcs/units.py");
      const utilsCandidates = buildCandidatePaths("pycalcs/utils.py");

      await pyodideInstance.runPythonAsync(`
import json
from pyodide.http import pyfetch

async def fetch_to_file(paths, destination):
    for path in paths:
        response = await pyfetch(path)
        if response.ok:
            with open(destination, 'w', encoding='utf-8') as f:
                f.write(await response.string())
            return path
    raise OSError(f"Could not fetch {destination} from any candidate path.")

utils_candidates = ${JSON.stringify(utilsCandidates)}
units_candidates = ${JSON.stringify(unitsCandidates)}

try:
    await fetch_to_file(utils_candidates, 'utils.py')
except OSError:
    pass

await fetch_to_file(units_candidates, 'units.py')

import units
      `);

      unitsModule = pyodideInstance.globals.get("units");
      const catalogProxy = unitsModule.get_unit_catalog();
      state.catalog = catalogProxy.toJs({ create_proxies: false, dict_converter: Object.fromEntries });
      catalogProxy.destroy();

      ensureQuantityInitialized();
      renderQuantityChips();
      renderUnitList("left");
      renderUnitList("right");
      convert("left");
      setMessage("", "");
    } catch (error) {
      setMessage("error", error.message || "Failed to initialise converter.");
    }
  }

  refs.leftInput.addEventListener("input", (event) =>
    handleValueInput("left", event.target.value)
  );
  refs.rightInput.addEventListener("input", (event) =>
    handleValueInput("right", event.target.value)
  );
  refs.leftSearch.addEventListener("input", (event) =>
    handleSearchInput("left", event.target.value)
  );
  refs.rightSearch.addEventListener("input", (event) =>
    handleSearchInput("right", event.target.value)
  );

  boot();
}
