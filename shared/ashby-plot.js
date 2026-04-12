/**
 * ashby-plot.js — Reusable Plotly-based Ashby chart component.
 *
 * Renders a log-log scatter of materials colored by family, with
 * optional performance-index isolines and click-to-inspect.
 *
 * Requires Plotly 2.27+ loaded globally.
 *
 * Usage:
 *   const chart = new AshbyPlot("chart-div", { onClick: (mat) => ... });
 *   chart.update(materials, registry, {
 *     xProp: "density",
 *     yProp: "youngs_modulus",
 *     isolines: { slope: 2, values: [3, 5, 10], label: "E^½/ρ" },
 *     families: ["metal", "polymer", "ceramic", "composite", "natural"],
 *   });
 */

// ── Family color palette ────────────────────────────────────────────
const FAMILY_COLORS = {
  metal:     "#4e79a7",
  polymer:   "#e15759",
  ceramic:   "#76b7b2",
  composite: "#f28e2b",
  natural:   "#59a14f",
  foam:      "#9c755f",
  fabric:    "#bab0ac",
  gel:       "#b07aa1",
};

const FAMILY_SYMBOLS = {
  metal:     "circle",
  polymer:   "diamond",
  ceramic:   "square",
  composite: "triangle-up",
  natural:   "star",
  foam:      "hexagon",
  fabric:    "cross",
  gel:       "pentagon",
};

// ── Helpers ─────────────────────────────────────────────────────────

function getValue(material, prop) {
  const raw = material[prop];
  if (raw == null) return null;
  if (typeof raw === "number") return raw;
  if (typeof raw === "object" && raw.value != null) return raw.value;
  return null;
}

function getRange(material, prop) {
  const raw = material[prop];
  if (raw != null && typeof raw === "object" && raw.min != null && raw.max != null) {
    return [raw.min, raw.max];
  }
  return null;
}

function displayValue(val, meta) {
  if (val == null) return "—";
  const mult = meta && meta.display_multiplier ? meta.display_multiplier : 1;
  const unit = meta && meta.display_unit ? meta.display_unit : (meta && meta.unit ? meta.unit : "");
  const displayed = val * mult;
  // Format nicely
  let str;
  if (Math.abs(displayed) >= 1e6 || (Math.abs(displayed) < 0.01 && displayed !== 0)) {
    str = displayed.toExponential(2);
  } else if (Number.isInteger(displayed)) {
    str = displayed.toString();
  } else {
    str = displayed.toPrecision(4);
  }
  return unit ? `${str} ${unit}` : str;
}


// ── AshbyPlot class ─────────────────────────────────────────────────

class AshbyPlot {
  /**
   * @param {string} divId - ID of the container div
   * @param {Object} opts
   * @param {function} [opts.onClick] - callback(material) on point click
   */
  constructor(divId, opts = {}) {
    this.divId = divId;
    this.onClick = opts.onClick || null;
    this._materials = [];
    this._registry = {};
    this._currentOpts = {};
  }

  /**
   * Render or re-render the chart.
   *
   * @param {Array} materials - array of material records
   * @param {Object} registry - property_registry from database
   * @param {Object} opts
   * @param {string} opts.xProp - x-axis property key
   * @param {string} opts.yProp - y-axis property key
   * @param {string[]} [opts.families] - families to show
   * @param {Object} [opts.isolines] - { slope, values, label }
   * @param {string[]} [opts.highlightIds] - material IDs to highlight
   * @param {boolean} [opts.showRanges] - show min/max error bars
   */
  update(materials, registry, opts) {
    this._materials = materials;
    this._registry = registry;
    this._currentOpts = opts;

    const xProp = opts.xProp;
    const yProp = opts.yProp;
    const xMeta = registry[xProp] || {};
    const yMeta = registry[yProp] || {};
    const showFamilies = new Set(opts.families || Object.keys(FAMILY_COLORS));
    const highlightSet = new Set(opts.highlightIds || []);
    const showRanges = opts.showRanges || false;

    // Group materials by family
    const familyGroups = {};
    for (const m of materials) {
      const fam = m.family;
      if (!showFamilies.has(fam)) continue;
      const xVal = getValue(m, xProp);
      const yVal = getValue(m, yProp);
      if (xVal == null || yVal == null) continue;
      if (!familyGroups[fam]) familyGroups[fam] = [];
      familyGroups[fam].push({ material: m, x: xVal, y: yVal });
    }

    const traces = [];

    // One trace per family
    for (const [fam, points] of Object.entries(familyGroups)) {
      const x = points.map(p => p.x);
      const y = points.map(p => p.y);
      const text = points.map(p => p.material.name);
      const ids = points.map(p => p.material.id);
      const customdata = points.map(p => p.material);

      // Error bars for ranges
      let error_x = undefined;
      let error_y = undefined;
      if (showRanges) {
        const xErrors = points.map(p => {
          const r = getRange(p.material, xProp);
          return r ? { lo: p.x - r[0], hi: r[1] - p.x } : { lo: 0, hi: 0 };
        });
        const yErrors = points.map(p => {
          const r = getRange(p.material, yProp);
          return r ? { lo: p.y - r[0], hi: r[1] - p.y } : { lo: 0, hi: 0 };
        });
        error_x = {
          type: "data",
          symmetric: false,
          array: xErrors.map(e => e.hi),
          arrayminus: xErrors.map(e => e.lo),
          visible: true,
          color: FAMILY_COLORS[fam] || "#888",
          thickness: 1,
        };
        error_y = {
          type: "data",
          symmetric: false,
          array: yErrors.map(e => e.hi),
          arrayminus: yErrors.map(e => e.lo),
          visible: true,
          color: FAMILY_COLORS[fam] || "#888",
          thickness: 1,
        };
      }

      // Size: larger for highlighted
      const sizes = ids.map(id => highlightSet.size > 0 && highlightSet.has(id) ? 14 : 8);
      const opacities = ids.map(id =>
        highlightSet.size > 0 ? (highlightSet.has(id) ? 1.0 : 0.35) : 0.85
      );

      const hovertemplate = points.map(p => {
        const xDisp = displayValue(p.x, xMeta);
        const yDisp = displayValue(p.y, yMeta);
        return `<b>${p.material.name}</b><br>` +
               `${xMeta.label || xProp}: ${xDisp}<br>` +
               `${yMeta.label || yProp}: ${yDisp}` +
               `<extra>${fam}</extra>`;
      });

      traces.push({
        x, y, text,
        customdata,
        ids,
        type: "scatter",
        mode: "markers",
        name: fam.charAt(0).toUpperCase() + fam.slice(1),
        marker: {
          color: FAMILY_COLORS[fam] || "#888",
          symbol: FAMILY_SYMBOLS[fam] || "circle",
          size: sizes,
          opacity: opacities,
          line: { width: 1, color: "#fff" },
        },
        error_x,
        error_y,
        hovertemplate,
        hoverlabel: { bgcolor: "#fff", font: { size: 12 } },
      });
    }

    // Isoline shapes
    const shapes = [];
    const annotations = [];
    if (opts.isolines && opts.isolines.slope != null && opts.isolines.values) {
      const slope = opts.isolines.slope;
      // On log-log: log(Y) = slope * log(X) + log(C)
      // where C = M^slope for index M = Y^(1/slope) / X
      // So Y = C * X^slope where C = M^slope
      // We need the axis range. Use data extents.
      let xMin = Infinity, xMax = -Infinity;
      for (const t of traces) {
        for (const v of t.x) {
          if (v > 0 && v < xMin) xMin = v;
          if (v > xMax) xMax = v;
        }
      }
      // Extend range slightly
      xMin *= 0.5;
      xMax *= 2;

      for (const M of opts.isolines.values) {
        const C = Math.pow(M, slope);
        const y0 = C * Math.pow(xMin, slope);
        const y1 = C * Math.pow(xMax, slope);

        shapes.push({
          type: "line",
          x0: xMin, y0: y0,
          x1: xMax, y1: y1,
          xref: "x", yref: "y",
          line: { color: "rgba(100,100,100,0.3)", width: 1.5, dash: "dot" },
        });

        // Label at right end
        annotations.push({
          x: Math.log10(xMax),
          y: Math.log10(y1),
          xref: "x", yref: "y",
          text: `M=${M}`,
          showarrow: false,
          font: { size: 10, color: "#888" },
          xanchor: "right",
        });
      }
    }

    const xScale = (xMeta.axis_scale === "linear") ? "linear" : "log";
    const yScale = (yMeta.axis_scale === "linear") ? "linear" : "log";

    const layout = {
      title: {
        text: `${yMeta.label || yProp} vs ${xMeta.label || xProp}`,
        font: { size: 16, family: "system-ui, sans-serif" },
      },
      xaxis: {
        title: { text: `${xMeta.label || xProp}${xMeta.unit ? " (" + xMeta.unit + ")" : ""}` },
        type: xScale,
        gridcolor: "#eee",
        zeroline: false,
      },
      yaxis: {
        title: { text: `${yMeta.label || yProp}${yMeta.unit ? " (" + yMeta.unit + ")" : ""}` },
        type: yScale,
        gridcolor: "#eee",
        zeroline: false,
      },
      shapes,
      annotations,
      hovermode: "closest",
      legend: {
        orientation: "h",
        yanchor: "bottom",
        y: 1.02,
        xanchor: "right",
        x: 1,
      },
      margin: { t: 60, r: 40, b: 60, l: 80 },
      plot_bgcolor: "#fafafa",
      paper_bgcolor: "#fff",
    };

    const config = {
      responsive: true,
      displayModeBar: true,
      modeBarButtonsToRemove: ["lasso2d", "select2d"],
      toImageButtonOptions: {
        format: "png",
        filename: "ashby-chart",
        height: 800,
        width: 1200,
        scale: 2,
      },
    };

    Plotly.react(this.divId, traces, layout, config);

    // Click handler
    if (this.onClick) {
      const div = document.getElementById(this.divId);
      // Remove previous listener
      div.removeAllListeners && div.removeAllListeners("plotly_click");
      div.on("plotly_click", (data) => {
        if (data.points && data.points.length > 0) {
          const pt = data.points[0];
          if (pt.customdata) {
            this.onClick(pt.customdata);
          }
        }
      });
    }
  }

  /**
   * Export chart as PNG data URL.
   * @returns {Promise<string>}
   */
  async toImage(format = "png") {
    return Plotly.toImage(this.divId, {
      format,
      height: 800,
      width: 1200,
      scale: 2,
    });
  }
}

// Export for use as ES module or global
if (typeof module !== "undefined" && module.exports) {
  module.exports = { AshbyPlot, FAMILY_COLORS, FAMILY_SYMBOLS, getValue, getRange, displayValue };
} else {
  window.AshbyPlot = AshbyPlot;
  window.FAMILY_COLORS = FAMILY_COLORS;
  window.FAMILY_SYMBOLS = FAMILY_SYMBOLS;
  window.ashbyGetValue = getValue;
  window.ashbyGetRange = getRange;
  window.ashbyDisplayValue = displayValue;
}
