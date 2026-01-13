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
  time: "s",
  current: "A",
  voltage: "V",
  capacitance: "F",
  magnetic_flux_density: "T",
  radiation_dose: "Sv",
  linear_stiffness: "N/m",
  rotational_stiffness: "N·m/rad",
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
  time: "Time",
  current: "Current",
  voltage: "Voltage",
  capacitance: "Capacitance",
  magnetic_flux_density: "Magnetic Flux Density",
  radiation_dose: "Radiation Dose",
  linear_stiffness: "Linear Stiffness",
  rotational_stiffness: "Rotational Stiffness",
};

const DIMENSION_MAP = {
  length: "L",
  area: "L²",
  volume: "L³",
  mass: "M",
  force: "M·L·T⁻²",
  torque: "M·L²·T⁻²",
  pressure: "M·L⁻¹·T⁻²",
  energy: "M·L²·T⁻²",
  power: "M·L²·T⁻³",
  density: "M·L⁻³",
  temperature: "Θ",
  angle: "—",
  time: "T",
  current: "I",
  voltage: "M·L²·T⁻³·I⁻¹",
  capacitance: "M⁻¹·L⁻²·T⁴·I²",
  magnetic_flux_density: "M·T⁻²·I⁻¹",
  radiation_dose: "L²·T⁻²",
  linear_stiffness: "M·T⁻²",
  rotational_stiffness: "M·L²·T⁻²",
};

const QUANTITY_SYMBOLS = {
  length: "L",
  area: "A",
  volume: "V",
  mass: "m",
  force: "F",
  torque: "τ",
  pressure: "p",
  energy: "E",
  power: "P",
  density: "ρ",
  temperature: "T",
  angle: "θ",
  time: "t",
  current: "I",
  voltage: "V",
  capacitance: "C",
  magnetic_flux_density: "B",
  radiation_dose: "H",
  linear_stiffness: "k",
  rotational_stiffness: "k_θ",
};

const PROPERTY_NATURE = {
  length: "Extensive",
  area: "Extensive",
  volume: "Extensive",
  mass: "Extensive",
  force: "Extensive",
  torque: "Extensive",
  pressure: "Intensive",
  energy: "Extensive",
  power: "Intensive",
  density: "Intensive",
  temperature: "Intensive",
  angle: "Intensive",
  time: "Extensive",
  current: "Extensive",
  voltage: "Intensive",
  capacitance: "Extensive",
  magnetic_flux_density: "Intensive",
  radiation_dose: "Intensive",
  linear_stiffness: "Extensive",
  rotational_stiffness: "Extensive",
};

const ABSOLUTE_TEMPERATURE_UNITS = new Set(["K", "°R"]);

const COMPARABLES = {
  length: [
    { label: "Credit card width", value: 0.0856 },
    { label: "A4 paper height", value: 0.297 },
    { label: "Basketball hoop height", value: 3.048 },
    { label: "City bus length", value: 12.0 },
    { label: "Marathon distance", value: 42195.0 },
    { label: "Geostationary orbit altitude", value: 35786000.0 },
    { label: "Sun–Earth distance (1 au)", value: 149_597_870_700.0 },
    { label: "One light-year", value: 9.460_730_472_580_8e15 },
    { label: "Milky Way diameter", value: 9.5e20 },
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
    { label: "Concrete compressive strength", value: 30000000.0 },
    { label: "Aluminum 6061-T6 yield strength", value: 276000000.0 },
    { label: "Mild steel yield strength", value: 250000000.0 },
    { label: "High-strength steel yield (A514)", value: 690000000.0 },
    { label: "Deep ocean (Mariana Trench)", value: 1086000000.0 },
    { label: "Aluminum modulus (E)", value: 69000000000.0 },
    { label: "Titanium modulus (E)", value: 116000000000.0 },
    { label: "Steel modulus (E)", value: 200000000000.0 },
  ],
  energy: [
    { label: "Visible photon (green)", value: 3.6e-19 },
    { label: "1 electronvolt", value: 1.602176634e-19 },
    { label: "AAA battery", value: 5400.0 },
    { label: "Smartphone charge", value: 18000.0 },
    { label: "1 kg TNT", value: 4.184e6 },
    { label: "Lightning strike", value: 5e9 },
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
  time: [
    { label: "Rapid blink", value: 0.25 },
    { label: "Heartbeat", value: 0.86 },
    { label: "Breath", value: 4.0 },
    { label: "Coffee brew", value: 240.0 },
    { label: "Work shift", value: 8 * 3600.0 },
    { label: "Gregorian year", value: 31_557_600.0 },
  ],
  current: [
    { label: "Smartphone fast charge", value: 3.0 },
    { label: "Household circuit (US 15 A)", value: 15.0 },
    { label: "Electric vehicle DC fast charger", value: 250.0 },
    { label: "Industrial welder", value: 500.0 },
    { label: "Lightning leader", value: 30_000.0 },
  ],
  voltage: [
    { label: "AA battery", value: 1.5 },
    { label: "USB power delivery max", value: 48.0 },
    { label: "Residential mains (US)", value: 120.0 },
    { label: "Residential mains (EU)", value: 230.0 },
    { label: "EV DC fast charge", value: 800.0 },
    { label: "High-voltage transmission", value: 345_000.0 },
  ],
  capacitance: [
    { label: "Ceramic decoupling capacitor", value: 1e-6 },
    { label: "Electrolytic capacitor", value: 1e-3 },
    { label: "Supercapacitor cell", value: 10.0 },
    { label: "Camera flash capacitor", value: 1e-2 },
    { label: "Grid storage module", value: 3000.0 },
  ],
  magnetic_flux_density: [
    { label: "Earth surface", value: 50e-6 },
    { label: "Fridge magnet", value: 5e-3 },
    { label: "MRI scanner", value: 3.0 },
    { label: "Particle accelerator dipole", value: 8.0 },
    { label: "Neodymium magnet surface", value: 1.4 },
  ],
  radiation_dose: [
    { label: "Banana equivalent", value: 0.0000001 },
    { label: "Dental X-ray", value: 0.000005 },
    { label: "Annual background (global avg)", value: 0.0024 },
    { label: "Chest CT", value: 0.007 },
    { label: "Occupational limit (year)", value: 0.05 },
    { label: "Acute illness threshold", value: 1.0 },
  ],
  linear_stiffness: [
    { label: "Microcantilever sensor", value: 0.1 },
    { label: "Guitar string", value: 600.0 },
    { label: "Office chair gas spring", value: 12_000.0 },
    { label: "Passenger car suspension (per corner)", value: 30_000.0 },
    { label: "Bridge stay cable", value: 200_000.0 },
    { label: "Press brake tooling", value: 500_000.0 },
  ],
  rotational_stiffness: [
    { label: "Precision tripod head", value: 5 * (180 / Math.PI) },
    { label: "Door closer hinge", value: 50 * (180 / Math.PI) },
    { label: "Steering column torsion bar", value: 1_000 * (180 / Math.PI) },
    { label: "Wind turbine yaw joint", value: 25_000 * (180 / Math.PI) },
    { label: "Large bearing mount", value: 100_000 * (180 / Math.PI) },
  ],
};

const DEFAULT_COMPARABLE_LIMIT = 8;

function formatNumber(value, precision = 6) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "—";
  if (num === 0) return "0";
  const stringValue = Number(num.toPrecision(precision)).toString();
  if (/e/.test(stringValue)) {
    return num.toExponential(precision - 1);
  }
  return stringValue;
}

function formatForInput(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "";
  return num.toString();
}

function ratioDescription(ratio, precision = 2) {
  if (!Number.isFinite(ratio) || ratio === 0) return "—";
  const abs = Math.abs(ratio);
  if (abs === 1) return "Roughly the same magnitude";
  if (abs > 1) {
    return `${formatNumber(abs, precision)}× your value`;
  }
  return `${formatNumber(1 / abs, precision)}× smaller than your value`;
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
    infoDimensions: container.querySelector("[data-role='info-dimensions']"),
    infoSymbol: container.querySelector("[data-role='info-symbol']"),
    infoNature: container.querySelector("[data-role='info-nature']"),
    comparisons: container.querySelector("[data-role='info-comparisons']"),
    infoUpdated: container.querySelector("[data-role='info-updated']"),
  };

  const optionalRefs = new Set(["infoDimensions", "infoSymbol", "infoNature"]);
  const missingRef = Object.entries(refs)
    .filter(([key, node]) => !node && !optionalRefs.has(key))
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
    precision: 6,
    raw: {
      left: "1",
      right: "1",
    },
  };

  let pyodideInstance;
  let unitsModule;
  let syncing = false;

  function isIncompleteRaw(value) {
    if (value === null || value === undefined) return false;
    const raw = String(value);
    if (raw === "" || raw === "-" || raw === "." || raw === "-.") return true;
    if (/^-?\d*\.$/.test(raw)) return true;
    return false;
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
    state.raw.left = refs.leftInput.value;
    state.raw.right = refs.rightInput.value;
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
    const trimmedSymbol = symbol.trim();
    const trimmedDescription = (description || "").trim();
    const descIsDuplicate =
      !trimmedDescription ||
      trimmedDescription.toLowerCase() === trimmedSymbol.toLowerCase();

    button.innerHTML = descIsDuplicate
      ? `<span class="unit-symbol">${trimmedSymbol}</span>`
      : `<span class="unit-symbol">${trimmedSymbol}</span><span class="unit-description">— ${trimmedDescription}</span>`;
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
      const ratioSource = activeSide === "left"
        ? (leftValue === 0 ? Number.NaN : leftConverted / leftValue)
        : (rightValue === 0 ? Number.NaN : rightConverted / rightValue);

      comparison.innerHTML = `
        <div class="comparison-label">${item.label}</div>
        <div class="comparison-values">
          <span>${Number.isFinite(rightConverted) ? formatNumber(rightConverted, state.precision) : "—"} ${rightUnit || ""}</span>
          <span class="comparison-secondary">${Number.isFinite(leftConverted) ? formatNumber(leftConverted, state.precision) : "—"} ${leftUnit || ""}</span>
        </div>
        <div class="comparison-ratio">${ratioDescription(ratioSource, 3)}</div>
      `;
      list.appendChild(comparison);
    });
  }

  function updateInfo(result) {
    if (refs.infoQuantity) {
      refs.infoQuantity.textContent = titleCase(state.quantity);
    }
    if (refs.infoDimensions) {
      refs.infoDimensions.textContent = DIMENSION_MAP[state.quantity] || "—";
    }
    if (refs.infoSymbol) {
      refs.infoSymbol.textContent = QUANTITY_SYMBOLS[state.quantity] || "—";
    }
    if (refs.infoNature) {
      refs.infoNature.textContent = PROPERTY_NATURE[state.quantity] || "—";
    }
    if (refs.infoBase) {
      const baseUnit = BASE_UNITS[state.quantity] || "SI";
      refs.infoBase.textContent = `${formatNumber(result.base_value, state.precision)} ${baseUnit}`;
    }
    if (refs.infoUnits) {
      refs.infoUnits.textContent = `${state.leftUnit || "—"} ↔ ${state.rightUnit || "—"}`;
    }
    if (refs.infoFactorCard && refs.infoFactorValue) {
      if (result.has_multiplier_only) {
        refs.infoFactorCard.style.display = "";
        refs.infoFactorValue.textContent = formatNumber(result.multiplier, state.precision);
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
        const formatted = formatForInput(state.rightValue);
        refs.rightInput.value = formatted;
        state.raw.right = formatted;
      } else {
        state.leftValue = Number(result.converted_value);
        const formatted = formatForInput(state.leftValue);
        refs.leftInput.value = formatted;
        state.raw.left = formatted;
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
    const raw = String(rawValue ?? "");
    state.raw[side] = raw;
    if (isIncompleteRaw(raw)) {
      setMessage("info", "");
      return;
    }
    const numeric = Number(raw);
    if (!Number.isFinite(numeric)) return;
    const unit = side === "left" ? state.leftUnit : state.rightUnit;
    if (
      state.quantity === "temperature" &&
      ABSOLUTE_TEMPERATURE_UNITS.has(unit || "") &&
      numeric < 0
    ) {
      setMessage("error", "Absolute temperature units cannot be negative.");
      return;
    }
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
