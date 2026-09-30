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

// ── Blob geometry helpers ───────────────────────────────────────
// All blob geometry is computed in log10 space so that hulls,
// expansion, and smoothing are correct on log-log Plotly axes.
// Only the final output is converted back to linear.

function _cross(o, a, b) { return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]); }

/** Convex hull via Andrew's monotone chain. Input/output: [x,y] arrays. */
function convexHull(points) {
  if (points.length < 3) return points.slice();
  const pts = points.slice().sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const lower = [];
  for (const p of pts) {
    while (lower.length >= 2 && _cross(lower[lower.length - 2], lower[lower.length - 1], p) <= 0) lower.pop();
    lower.push(p);
  }
  const upper = [];
  for (let i = pts.length - 1; i >= 0; i--) {
    const p = pts[i];
    while (upper.length >= 2 && _cross(upper[upper.length - 2], upper[upper.length - 1], p) <= 0) upper.pop();
    upper.push(p);
  }
  upper.pop(); lower.pop();
  return lower.concat(upper);
}

/** Expand hull outward from centroid by factor. Operates in log space. */
function expandHull(hull, factor) {
  if (hull.length < 3) return hull;
  let cx = 0, cy = 0;
  for (const [x, y] of hull) { cx += x; cy += y; }
  cx /= hull.length; cy /= hull.length;
  return hull.map(([x, y]) => [cx + (x - cx) * factor, cy + (y - cy) * factor]);
}

/** Chaikin corner-cutting smoothing. Operates in log space.
 *  Each pass replaces every edge with two points at 25%/75%,
 *  converging to a smooth quadratic B-spline curve. */
function smoothPolygon(pts, passes) {
  if (pts.length < 3) return pts;
  let result = pts.slice();
  for (let s = 0; s < passes; s++) {
    const next = [];
    const n = result.length;
    for (let i = 0; i < n; i++) {
      const p1 = result[i];
      const p2 = result[(i + 1) % n];
      next.push([0.75 * p1[0] + 0.25 * p2[0], 0.75 * p1[1] + 0.25 * p2[1]]);
      next.push([0.25 * p1[0] + 0.75 * p2[0], 0.25 * p1[1] + 0.75 * p2[1]]);
    }
    result = next;
  }
  return result;
}

/**
 * Build a smooth blob envelope from raw material points.
 * Input: array of [x, y] in linear space (positive values).
 * Output: array of [x, y] in linear space forming a closed smooth blob.
 */
function buildBlobEnvelope(linearPoints) {
  if (linearPoints.length < 3) return null;
  // Convert to log space
  const logPts = linearPoints.map(([x, y]) => [Math.log10(x), Math.log10(y)]);
  // Compute hull in log space
  let hull = convexHull(logPts);
  if (hull.length < 3) return null;
  // Expand outward in log space
  hull = expandHull(hull, 1.5);
  // Smooth in log space (6 Chaikin corner-cutting passes)
  hull = smoothPolygon(hull, 6);
  // Convert back to linear
  return hull.map(([lx, ly]) => [Math.pow(10, lx), Math.pow(10, ly)]);
}

const FAMILY_BLOB_COLORS = {
  metal:     { fill: "rgba(78,121,167,0.13)",  line: "rgba(78,121,167,0.5)" },
  polymer:   { fill: "rgba(225,87,89,0.13)",   line: "rgba(225,87,89,0.5)" },
  ceramic:   { fill: "rgba(118,183,178,0.13)", line: "rgba(118,183,178,0.5)" },
  composite: { fill: "rgba(242,142,43,0.13)",  line: "rgba(242,142,43,0.5)" },
  natural:   { fill: "rgba(89,161,79,0.13)",   line: "rgba(89,161,79,0.5)" },
  foam:      { fill: "rgba(156,117,95,0.13)",   line: "rgba(156,117,95,0.5)" },
  fabric:    { fill: "rgba(186,176,172,0.13)", line: "rgba(186,176,172,0.5)" },
  gel:       { fill: "rgba(176,122,161,0.13)", line: "rgba(176,122,161,0.5)" },
};

// ── Theme helper ────────────────────────────────────────────────
function getPlotlyThemeColors(isDark) {
  if (isDark) {
    return {
      plotBg: "#1a1f2e",
      paperBg: "#111827",
      gridColor: "rgba(255,255,255,0.08)",
      fontColor: "#e5e7eb",
      axisColor: "#9ca3af",
      hoverBg: "#1f2937",
    };
  }
  return {
    plotBg: "#fafafa",
    paperBg: "#ffffff",
    gridColor: "#eee",
    fontColor: "#111827",
    axisColor: "#6b7280",
    hoverBg: "#fff",
  };
}

/** Fit an axis to the plotted data, independent of reference lines. */
function dataAxisRange(values, scale) {
  const valid = values.filter(v => Number.isFinite(v) && (scale !== "log" || v > 0));
  if (!valid.length) return [0, 1];
  const coords = valid.map(v => scale === "log" ? Math.log10(v) : v);
  const low = Math.min(...coords), high = Math.max(...coords);
  const padding = Math.max((high - low) * 0.08, scale === "log" ? 0.08 : Math.abs(low) * 0.08 || 1);
  return [low - padding, high + padding];
}

/** Clip a reference segment in axis coordinates so it cannot stretch the view. */
function clipIsoline(points, ranges, scales) {
  const coords = points.map(point => point.map((v, axis) => scales[axis] === "log" ? Math.log10(v) : v));
  let start = 0, end = 1;
  for (let axis = 0; axis < 2; axis++) {
    const origin = coords[0][axis], delta = coords[1][axis] - origin;
    const [low, high] = ranges[axis];
    if (Math.abs(delta) < 1e-12) {
      if (origin < low || origin > high) return null;
      continue;
    }
    const bounds = [(low - origin) / delta, (high - origin) / delta].sort((a, b) => a - b);
    start = Math.max(start, bounds[0]);
    end = Math.min(end, bounds[1]);
    if (start > end) return null;
  }
  return [start, end].map(t => coords[0].map((v, axis) => v + t * (coords[1][axis] - v)));
}


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
    this._size = [];
    if (typeof ResizeObserver !== "undefined") {
      this._resizeObserver = new ResizeObserver(() => {
        const container = document.getElementById(this.divId);
        if (this._currentOpts.xProp && (container.clientWidth !== this._size[0] || container.clientHeight !== this._size[1])) {
          this.update(this._materials, this._registry, this._currentOpts);
        }
      });
      this._resizeObserver.observe(document.getElementById(divId));
    }
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
   * @param {boolean} [opts.showBlobs] - show family envelope blobs
   * @param {boolean} [opts.showPoints] - show individual material points (default true)
   * @param {boolean} [opts.dark] - use dark theme colors
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
    const showBlobs = opts.showBlobs || false;
    const showPoints = opts.showPoints !== false;
    const isDark = opts.dark || false;
    const theme = getPlotlyThemeColors(isDark);

    // Group materials by family
    const familyGroups = {};
    for (const m of materials) {
      const fam = m.family;
      if (!showFamilies.has(fam)) continue;
      const xVal = getValue(m, xProp);
      const yVal = getValue(m, yProp);
      if (!Number.isFinite(xVal) || !Number.isFinite(yVal) || xVal <= 0 || yVal <= 0) continue;
      if (!familyGroups[fam]) familyGroups[fam] = [];
      familyGroups[fam].push({ material: m, x: xVal, y: yVal });
    }

    const traces = [];

    // Blob traces (family envelopes) — rendered behind points
    if (showBlobs) {
      for (const [fam, pts] of Object.entries(familyGroups)) {
        const blobColors = FAMILY_BLOB_COLORS[fam];
        if (!blobColors) continue;

        // A specified lower/upper bound cannot define a finite family extent.
        const measured = pts.filter(p => !p.material.hasBounds);
        const blob = buildBlobEnvelope(measured.map(p => [p.x, p.y]));
        if (!blob) continue;

        // Close the polygon
        const hx = blob.map(p => p[0]);
        const hy = blob.map(p => p[1]);
        hx.push(hx[0]);
        hy.push(hy[0]);

        traces.push({
          x: hx, y: hy,
          type: "scatter", mode: "lines",
          fill: "toself",
          fillcolor: blobColors.fill,
          line: { color: blobColors.line, width: 1.5, shape: "spline", smoothing: 1.0 },
          name: fam + " envelope",
          showlegend: false,
          hoverinfo: "skip",
        });
      }
    }

    // Point traces — one per family
    for (const [fam, points] of Object.entries(familyGroups)) {
      if (!showPoints) continue;
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
        const xDisp = p.material[xProp]?.label || displayValue(p.x, xMeta);
        const yDisp = p.material[yProp]?.label || displayValue(p.y, yMeta);
        return `<b>${p.material.name}</b><br>` +
               `${xMeta.label || xProp}: ${xDisp}<br>` +
               `${yMeta.label || yProp}: ${yDisp}` +
               (p.material.condition ? `<br>${p.material.condition}` : '') +
               `<extra>${fam}</extra>`;
      });

      traces.push({
        x, y, text,
        customdata,
        ids,
        type: "scatter",
        mode: opts.showLabels ? "markers+text" : "markers",
        textposition: "top center",
        textfont: { size: 10, color: theme.fontColor },
        name: fam.charAt(0).toUpperCase() + fam.slice(1),
        marker: {
          color: FAMILY_COLORS[fam] || "#888",
          symbol: points.map(p => (FAMILY_SYMBOLS[fam] || "circle") + (p.material.hasBounds ? "-open" : "")),
          size: sizes,
          opacity: opacities,
          line: { width: 1, color: "#fff" },
        },
        error_x,
        error_y,
        hovertemplate,
        hoverlabel: { bgcolor: theme.hoverBg, font: { size: 12, color: theme.fontColor } },
      });
    }

    const xScale = (xMeta.axis_scale === "linear") ? "linear" : "log";
    const yScale = (yMeta.axis_scale === "linear") ? "linear" : "log";
    const axisValues = [[], []];
    for (const points of Object.values(familyGroups)) {
      for (const p of points) {
        axisValues[0].push(p.x, ...(showRanges ? getRange(p.material, xProp) || [] : []));
        axisValues[1].push(p.y, ...(showRanges ? getRange(p.material, yProp) || [] : []));
      }
    }
    for (const trace of traces) {
      if (trace.fill === "toself") {
        axisValues[0].push(...trace.x);
        axisValues[1].push(...trace.y);
      }
    }
    const ranges = [dataAxisRange(axisValues[0], xScale), dataAxisRange(axisValues[1], yScale)];
    const scales = [xScale, yScale];
    const fitToData = Array.isArray(opts.isolines?.lines);
    const container = document.getElementById(this.divId);
    this._size = [container.clientWidth, container.clientHeight];
    const narrow = this._size[0] < 580;

    // Isoline shapes
    const shapes = [];
    const annotations = [];
    // Endpoints supplied by the Python index library also work with reversed
    // axes. The old slope/value API remains available to retained prototypes.
    for (const line of opts.isolines?.lines || []) {
      if (line.points?.length !== 2 || !line.points.flat().every(v => Number.isFinite(v) && v > 0)) continue;
      const clipped = clipIsoline(line.points, ranges, scales);
      if (!clipped) continue;
      const [[x0, y0], [x1, y1]] = clipped.map(point => point.map((v, axis) => scales[axis] === "log" ? Math.pow(10, v) : v));
      shapes.push({ type: "line", x0, y0, x1, y1, xref: "x", yref: "y",
        line: { color: isDark ? "rgba(180,180,180,0.4)" : "rgba(100,100,100,0.4)", width: 1.5, dash: "dot" } });
      const [labelX, labelY] = clipped[1];
      const crowded = annotations.some(a =>
        Math.abs(a.x - labelX) / (ranges[0][1] - ranges[0][0]) * Math.max(150, this._size[0] - 200) < 70 &&
        Math.abs(a.y - labelY) / (ranges[1][1] - ranges[1][0]) * (this._size[1] - 150) < 18);
      if (!crowded) annotations.push({ x: labelX, y: labelY, xref: "x", yref: "y",
        text: line.label, showarrow: false, font: { size: 10, color: theme.axisColor },
        xanchor: "right", yanchor: "top", xshift: -4, yshift: -4 });
    }
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
        if (!Number.isFinite(xMin) || !Number.isFinite(xMax) || !Number.isFinite(M) || M <= 0) continue;
        const C = Math.pow(M, slope);
        const y0 = C * Math.pow(xMin, slope);
        const y1 = C * Math.pow(xMax, slope);

        shapes.push({
          type: "line",
          x0: xMin, y0: y0,
          x1: xMax, y1: y1,
          xref: "x", yref: "y",
          line: { color: isDark ? "rgba(180,180,180,0.25)" : "rgba(100,100,100,0.3)", width: 1.5, dash: "dot" },
        });

        // Label at right end
        annotations.push({
          x: Math.log10(xMax),
          y: Math.log10(y1),
          xref: "x", yref: "y",
          text: `M=${M}`,
          showarrow: false,
          font: { size: 10, color: theme.axisColor },
          xanchor: "right",
        });
      }
    }

    const layout = {
      width: this._size[0],
      height: this._size[1],
      title: {
        text: `${yMeta.label || yProp}${narrow ? "<br>vs " : " vs "}${xMeta.label || xProp}`,
        font: { size: narrow ? 14 : 16, family: "system-ui, sans-serif", color: theme.fontColor },
        y: narrow ? 0.92 : 0.98,
        yanchor: "top",
      },
      xaxis: {
        title: { text: `${xMeta.label || xProp}${xMeta.unit ? " (" + xMeta.unit + ")" : ""}`, font: { color: theme.axisColor } },
        type: xScale,
        ...(fitToData ? { range: ranges[0], autorange: false } : {}),
        gridcolor: theme.gridColor,
        zeroline: false,
        exponentformat: "SI",
        tickfont: { color: theme.axisColor },
      },
      yaxis: {
        title: { text: `${yMeta.label || yProp}${yMeta.unit ? " (" + yMeta.unit + ")" : ""}`, font: { color: theme.axisColor } },
        type: yScale,
        ...(fitToData ? { range: ranges[1], autorange: false } : {}),
        gridcolor: theme.gridColor,
        zeroline: false,
        exponentformat: "SI",
        tickfont: { color: theme.axisColor },
      },
      shapes,
      annotations,
      hovermode: "closest",
      legend: {
        orientation: narrow ? "h" : "v",
        yanchor: "top",
        y: narrow ? -0.3 : 1,
        xanchor: "left",
        x: narrow ? 0 : 1.02,
        font: { color: theme.fontColor, size: 12 },
      },
      margin: { t: narrow ? 84 : 50, r: narrow ? 18 : 120, b: narrow ? 100 : 60, l: narrow ? 62 : 80 },
      plot_bgcolor: theme.plotBg,
      paper_bgcolor: theme.paperBg,
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

    const rendered = Plotly.react(this.divId, traces, layout, config);

    // Click handler
    return Promise.resolve(rendered).then(() => {
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
    });
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
  module.exports = { AshbyPlot, FAMILY_COLORS, FAMILY_SYMBOLS, FAMILY_BLOB_COLORS, getValue, getRange, displayValue, getPlotlyThemeColors };
} else {
  window.AshbyPlot = AshbyPlot;
  window.FAMILY_COLORS = FAMILY_COLORS;
  window.FAMILY_SYMBOLS = FAMILY_SYMBOLS;
  window.FAMILY_BLOB_COLORS = FAMILY_BLOB_COLORS;
  window.ashbyGetValue = getValue;
  window.ashbyGetRange = getRange;
  window.ashbyDisplayValue = displayValue;
  window.getPlotlyThemeColors = getPlotlyThemeColors;
}
