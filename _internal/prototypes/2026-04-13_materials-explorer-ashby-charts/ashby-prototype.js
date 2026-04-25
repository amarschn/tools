const FAMILY_ORDER = ["metal", "ceramic", "composite", "polymer", "natural"];

const FAMILY_STYLES = {
  metal: {
    classic: { fill: "rgba(81, 108, 140, 0.18)", line: "#516c8c", marker: "#435c79" },
    bright: { fill: "rgba(47, 84, 150, 0.15)", line: "#2f5496", marker: "#274983" },
    mono: { fill: "rgba(17, 24, 39, 0.06)", line: "#475569", marker: "#334155" },
  },
  ceramic: {
    classic: { fill: "rgba(52, 133, 122, 0.16)", line: "#34857a", marker: "#2c7269" },
    bright: { fill: "rgba(18, 135, 121, 0.15)", line: "#128779", marker: "#0f7267" },
    mono: { fill: "rgba(17, 24, 39, 0.05)", line: "#0f766e", marker: "#0f766e" },
  },
  composite: {
    classic: { fill: "rgba(186, 123, 44, 0.16)", line: "#ba7b2c", marker: "#996622" },
    bright: { fill: "rgba(215, 117, 32, 0.15)", line: "#d77520", marker: "#b76415" },
    mono: { fill: "rgba(17, 24, 39, 0.05)", line: "#b45309", marker: "#92400e" },
  },
  polymer: {
    classic: { fill: "rgba(177, 94, 104, 0.16)", line: "#b15e68", marker: "#914b54" },
    bright: { fill: "rgba(210, 78, 93, 0.15)", line: "#d24e5d", marker: "#b53f4d" },
    mono: { fill: "rgba(17, 24, 39, 0.05)", line: "#be123c", marker: "#9f1239" },
  },
  natural: {
    classic: { fill: "rgba(110, 135, 65, 0.16)", line: "#6e8741", marker: "#5b7134" },
    bright: { fill: "rgba(88, 143, 55, 0.15)", line: "#588f37", marker: "#4b7b2f" },
    mono: { fill: "rgba(17, 24, 39, 0.05)", line: "#3f6212", marker: "#365314" },
  },
};

const FAMILY_LABELS = {
  metal: "Metals",
  ceramic: "Ceramics",
  composite: "Composites",
  polymer: "Polymers",
  natural: "Natural",
};

async function loadMaterialsDatabase() {
  const response = await fetch("/data/materials/materials.json");
  if (!response.ok) {
    throw new Error(`Failed to load materials database: ${response.status}`);
  }
  return response.json();
}

function getValue(material, prop) {
  const raw = material[prop];
  if (raw == null) return null;
  if (typeof raw === "number") return raw;
  if (typeof raw === "object" && raw.value != null) return raw.value;
  return null;
}

function displayMultiplier(registry, prop) {
  return registry[prop]?.display_multiplier || 1;
}

function axisTitle(registry, prop) {
  const meta = registry[prop] || {};
  const label = meta.label || prop;
  const symbol = meta.symbol ? `${meta.symbol} ` : "";
  const unit = meta.display_unit || meta.unit;
  return `${symbol}${label}${unit ? ` (${unit})` : ""}`;
}

function buildPointSeries(db, xProp, yProp) {
  const xScale = displayMultiplier(db.property_registry, xProp);
  const yScale = displayMultiplier(db.property_registry, yProp);

  return db.materials
    .map((material) => {
      const xRaw = getValue(material, xProp);
      const yRaw = getValue(material, yProp);
      if (xRaw == null || yRaw == null || xRaw <= 0 || yRaw <= 0) {
        return null;
      }
      return {
        material,
        family: material.family,
        x: xRaw * xScale,
        y: yRaw * yScale,
      };
    })
    .filter(Boolean);
}

function groupByFamily(points) {
  const groups = new Map();
  for (const point of points) {
    if (!groups.has(point.family)) {
      groups.set(point.family, []);
    }
    groups.get(point.family).push(point);
  }
  return groups;
}

function log10(value) {
  return Math.log(value) / Math.LN10;
}

function mean(values) {
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function convexHull(points) {
  if (points.length < 3) {
    return points.slice();
  }
  const sorted = points.slice().sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const cross = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);

  const lower = [];
  for (const point of sorted) {
    while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], point) <= 0) {
      lower.pop();
    }
    lower.push(point);
  }

  const upper = [];
  for (let index = sorted.length - 1; index >= 0; index -= 1) {
    const point = sorted[index];
    while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], point) <= 0) {
      upper.pop();
    }
    upper.push(point);
  }

  lower.pop();
  upper.pop();
  return lower.concat(upper);
}

function expandHull(points, factor) {
  const cx = mean(points.map((point) => point[0]));
  const cy = mean(points.map((point) => point[1]));
  return points.map(([x, y]) => [cx + (x - cx) * factor, cy + (y - cy) * factor]);
}

function smoothClosed(points, passes = 4) {
  let current = points.slice();
  for (let pass = 0; pass < passes; pass += 1) {
    const next = [];
    for (let index = 0; index < current.length; index += 1) {
      const a = current[index];
      const b = current[(index + 1) % current.length];
      next.push([0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]]);
      next.push([0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1]]);
    }
    current = next;
  }
  return current;
}

function smoothOpen(points, passes = 3) {
  if (points.length < 3) {
    return points.slice();
  }
  let current = points.slice();
  for (let pass = 0; pass < passes; pass += 1) {
    const next = [current[0]];
    for (let index = 0; index < current.length - 1; index += 1) {
      const a = current[index];
      const b = current[index + 1];
      next.push([0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]]);
      next.push([0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1]]);
    }
    next.push(current[current.length - 1]);
    current = next;
  }
  return current;
}

function toLinear(points) {
  return points.map(([x, y]) => [10 ** x, 10 ** y]);
}

function buildCapsuleEnvelope(points) {
  const logPoints = points.map((point) => [log10(point.x), log10(point.y)]);
  if (logPoints.length === 0) {
    return null;
  }
  if (logPoints.length === 1) {
    const [cx, cy] = logPoints[0];
    const ring = [];
    for (let step = 0; step <= 48; step += 1) {
      const angle = (Math.PI * 2 * step) / 48;
      ring.push([cx + 0.08 * Math.cos(angle), cy + 0.08 * Math.sin(angle)]);
    }
    return toLinear(ring);
  }

  const [a, b] = logPoints;
  const cx = (a[0] + b[0]) / 2;
  const cy = (a[1] + b[1]) / 2;
  const dx = b[0] - a[0];
  const dy = b[1] - a[1];
  const angle = Math.atan2(dy, dx);
  const semiMajor = Math.max(Math.sqrt(dx * dx + dy * dy) / 2 + 0.1, 0.16);
  const semiMinor = 0.09;

  const ring = [];
  for (let step = 0; step <= 72; step += 1) {
    const theta = (Math.PI * 2 * step) / 72;
    const localX = semiMajor * Math.cos(theta);
    const localY = semiMinor * Math.sin(theta);
    const px = cx + localX * Math.cos(angle) - localY * Math.sin(angle);
    const py = cy + localX * Math.sin(angle) + localY * Math.cos(angle);
    ring.push([px, py]);
  }
  return toLinear(ring);
}

function buildHullEnvelope(points) {
  if (points.length < 3) {
    return buildCapsuleEnvelope(points);
  }
  const logPoints = points.map((point) => [log10(point.x), log10(point.y)]);
  const hull = smoothClosed(expandHull(convexHull(logPoints), 1.34), 5);
  return toLinear(hull);
}

function eigenDecomposition2x2(a, b, c) {
  const trace = a + c;
  const diff = a - c;
  const root = Math.sqrt(diff * diff + 4 * b * b);
  const l1 = (trace + root) / 2;
  const l2 = (trace - root) / 2;

  let v1 = b !== 0 ? [l1 - c, b] : [1, 0];
  let v2 = b !== 0 ? [l2 - c, b] : [0, 1];

  const n1 = Math.hypot(v1[0], v1[1]) || 1;
  const n2 = Math.hypot(v2[0], v2[1]) || 1;
  v1 = [v1[0] / n1, v1[1] / n1];
  v2 = [v2[0] / n2, v2[1] / n2];

  return { eigenvalues: [Math.max(l1, 1e-4), Math.max(l2, 1e-4)], eigenvectors: [v1, v2] };
}

function buildEllipseEnvelope(points) {
  if (points.length < 3) {
    return buildCapsuleEnvelope(points);
  }

  const lx = points.map((point) => log10(point.x));
  const ly = points.map((point) => log10(point.y));
  const mx = mean(lx);
  const my = mean(ly);
  let sxx = 0;
  let syy = 0;
  let sxy = 0;

  for (let index = 0; index < points.length; index += 1) {
    const dx = lx[index] - mx;
    const dy = ly[index] - my;
    sxx += dx * dx;
    syy += dy * dy;
    sxy += dx * dy;
  }

  const denom = Math.max(points.length - 1, 1);
  const { eigenvalues, eigenvectors } = eigenDecomposition2x2(sxx / denom, sxy / denom, syy / denom);
  const scale = 2.2;
  const ring = [];

  for (let step = 0; step <= 96; step += 1) {
    const theta = (Math.PI * 2 * step) / 96;
    const ax = scale * Math.sqrt(eigenvalues[0]) * Math.cos(theta);
    const ay = scale * Math.sqrt(eigenvalues[1]) * Math.sin(theta);
    const px = mx + ax * eigenvectors[0][0] + ay * eigenvectors[1][0];
    const py = my + ax * eigenvectors[0][1] + ay * eigenvectors[1][1];
    ring.push([px, py]);
  }

  return toLinear(ring);
}

function buildRibbonEnvelope(points) {
  if (points.length < 5) {
    return buildHullEnvelope(points);
  }

  const logPoints = points
    .map((point) => ({ x: log10(point.x), y: log10(point.y) }))
    .sort((a, b) => a.x - b.x);
  const minX = logPoints[0].x;
  const maxX = logPoints[logPoints.length - 1].x;
  const span = Math.max(maxX - minX, 0.25);
  const binCount = Math.max(4, Math.min(7, Math.floor(logPoints.length / 3) + 2));
  const step = span / binCount;
  const bins = [];

  for (let index = 0; index <= binCount; index += 1) {
    const start = minX + (index - 0.5) * step;
    const end = minX + (index + 0.5) * step;
    const inBin = logPoints.filter((point) => point.x >= start && point.x <= end);
    if (inBin.length === 0) {
      continue;
    }
    const ys = inBin.map((point) => point.y);
    bins.push({
      x: mean(inBin.map((point) => point.x)),
      yLow: Math.min(...ys) - 0.05,
      yHigh: Math.max(...ys) + 0.05,
    });
  }

  if (bins.length < 3) {
    return buildHullEnvelope(points);
  }

  bins[0].x -= step * 0.25;
  bins[bins.length - 1].x += step * 0.25;

  const upper = smoothOpen(bins.map((bin) => [bin.x, bin.yHigh]), 3);
  const lower = smoothOpen(bins.map((bin) => [bin.x, bin.yLow]), 3).reverse();
  return toLinear(upper.concat(lower));
}

function envelopeLabelPoint(envelope) {
  const lx = envelope.map((point) => log10(point[0]));
  const ly = envelope.map((point) => log10(point[1]));
  return {
    x: 10 ** mean(lx),
    y: 10 ** mean(ly),
  };
}

function quantile(values, q) {
  if (values.length === 0) return null;
  const sorted = values.slice().sort((a, b) => a - b);
  const pos = (sorted.length - 1) * q;
  const base = Math.floor(pos);
  const rest = pos - base;
  if (sorted[base + 1] == null) return sorted[base];
  return sorted[base] + rest * (sorted[base + 1] - sorted[base]);
}

function buildMeritLineTraces(points, opts = {}) {
  const slope = opts.slope ?? 2;
  const xMin = Math.min(...points.map((point) => point.x)) * 0.82;
  const xMax = Math.max(...points.map((point) => point.x)) * 1.18;
  const meritValues = points.map((point) => (point.y ** (1 / slope)) / point.x).filter((value) => Number.isFinite(value));
  const levels = [0.25, 0.5, 0.78]
    .map((q) => quantile(meritValues, q))
    .filter((value) => value != null);

  return levels.map((merit, index) => {
    const constant = merit ** slope;
    const x = [xMin, xMax];
    const y = x.map((value) => constant * value ** slope);
    return {
      x,
      y,
      type: "scatter",
      mode: "lines",
      line: {
        color: opts.color || "rgba(107, 114, 128, 0.55)",
        width: opts.width || 1.1,
        dash: opts.dash || "dot",
      },
      hoverinfo: "skip",
      showlegend: false,
      name: `Merit ${index + 1}`,
    };
  });
}

function buildLayout(db, xProp, yProp, variant) {
  const base = {
    dragmode: "pan",
    hovermode: "closest",
    paper_bgcolor: "#ffffff",
    plot_bgcolor: "#ffffff",
    margin: { t: 28, r: variant.marginRight || 32, b: 74, l: 86 },
    font: { family: "'Helvetica Neue', 'Avenir Next', 'Univers', system-ui, sans-serif", color: "#111827" },
    xaxis: {
      type: "log",
      title: { text: axisTitle(db.property_registry, xProp), standoff: 12 },
      showline: true,
      mirror: true,
      linewidth: 1,
      linecolor: "#111827",
      tickfont: { color: "#475569", size: 11 },
      ticklen: 6,
      ticks: "outside",
      showgrid: true,
      gridcolor: "#eceff3",
      zeroline: false,
    },
    yaxis: {
      type: "log",
      title: { text: axisTitle(db.property_registry, yProp), standoff: 10 },
      showline: true,
      mirror: true,
      linewidth: 1,
      linecolor: "#111827",
      tickfont: { color: "#475569", size: 11 },
      ticklen: 6,
      ticks: "outside",
      showgrid: true,
      gridcolor: "#eceff3",
      zeroline: false,
    },
    legend: variant.legend
      ? {
          bgcolor: "rgba(255,255,255,0.92)",
          bordercolor: "#e5e7eb",
          borderwidth: 1,
          x: 1.02,
          xanchor: "left",
          y: 1,
          yanchor: "top",
          font: { size: 12 },
        }
      : undefined,
    annotations: [],
  };

  return base;
}

function addInlineKey(targetId, palette) {
  const target = document.getElementById(targetId);
  if (!target) return;
  target.innerHTML = FAMILY_ORDER.map((family) => {
    const swatch = FAMILY_STYLES[family][palette];
    return `<span class="swatch"><span class="dot" style="background:${swatch.line}"></span>${FAMILY_LABELS[family]}</span>`;
  }).join("");
}

function bestPointForFamily(points) {
  return points
    .slice()
    .sort((a, b) => (b.y ** 0.5) / b.x - (a.y ** 0.5) / a.x)[0];
}

function cleanMaterialLabel(name) {
  return name
    .replace("AISI ", "")
    .replace("ASTM ", "")
    .replace("Steel", "steel")
    .replace("Stainless", "SS")
    .replace("Structural ", "")
    .replace("Polyetheretherketone", "PEEK")
    .replace("Polyoxymethylene", "POM")
    .replace("Polypropylene", "PP")
    .replace("Polycarbonate", "PC");
}

async function renderAshbyPrototype(options) {
  const db = await loadMaterialsDatabase();
  const xProp = options.xProp || "density";
  const yProp = options.yProp || "youngs_modulus";
  const points = buildPointSeries(db, xProp, yProp);
  const families = groupByFamily(points);
  const traces = [];
  const layout = buildLayout(db, xProp, yProp, options);

  for (const family of FAMILY_ORDER) {
    const familyPoints = families.get(family);
    if (!familyPoints || familyPoints.length === 0) {
      continue;
    }

    const style = FAMILY_STYLES[family][options.palette || "classic"];
    const envelopeBuilder = {
      hull: buildHullEnvelope,
      ellipse: buildEllipseEnvelope,
      ribbon: buildRibbonEnvelope,
    }[options.geometry || "hull"];

    const envelope = envelopeBuilder(familyPoints);
    if (envelope) {
      traces.push({
        x: envelope.map((point) => point[0]),
        y: envelope.map((point) => point[1]),
        type: "scatter",
        mode: "lines",
        fill: "toself",
        fillcolor: style.fill,
        line: {
          color: style.line,
          width: options.envelopeWidth || 1.8,
          shape: "spline",
          smoothing: options.geometry === "ribbon" ? 0.55 : 0.9,
        },
        hoverinfo: "skip",
        showlegend: false,
        name: FAMILY_LABELS[family],
      });

      if (options.directLabels) {
        const labelPoint = envelopeLabelPoint(envelope);
        layout.annotations.push({
          x: labelPoint.x,
          y: labelPoint.y,
          xref: "x",
          yref: "y",
          text: FAMILY_LABELS[family],
          showarrow: false,
          font: {
            family: "'Helvetica Neue', 'Avenir Next', 'Univers', system-ui, sans-serif",
            size: 13,
            color: style.line,
          },
          bgcolor: options.labelBackground || "rgba(255,255,255,0.76)",
          borderpad: 4,
        });
      }
    }

    traces.push({
      x: familyPoints.map((point) => point.x),
      y: familyPoints.map((point) => point.y),
      text: familyPoints.map((point) => point.material.name),
      customdata: familyPoints.map((point) => point.material.name),
      type: "scatter",
      mode: "markers",
      name: FAMILY_LABELS[family],
      showlegend: Boolean(options.legend),
      hovertemplate: "<b>%{text}</b><br>%{x:.3g}, %{y:.3g}<extra>" + FAMILY_LABELS[family] + "</extra>",
      marker: {
        color: style.marker,
        size: options.pointSize || 7,
        opacity: options.pointOpacity || 0.78,
        line: {
          color: "#ffffff",
          width: options.pointStroke || 1,
        },
        symbol: options.markerSymbol || "circle",
      },
    });

    if (options.calloutExemplars) {
      const bestPoint = bestPointForFamily(familyPoints);
      const offset = options.calloutOffsets?.[family] || { ax: 24, ay: -20 };
      layout.annotations.push({
        x: bestPoint.x,
        y: bestPoint.y,
        xref: "x",
        yref: "y",
        ax: offset.ax,
        ay: offset.ay,
        arrowhead: 0,
        arrowsize: 1,
        arrowwidth: 0.9,
        arrowcolor: style.line,
        text: cleanMaterialLabel(bestPoint.material.name),
        font: { size: 11, color: style.line },
        bgcolor: "rgba(255,255,255,0.86)",
        bordercolor: "rgba(229,231,235,0.9)",
        borderwidth: 1,
        borderpad: 4,
      });
    }
  }

  if (options.meritLines) {
    traces.push(
      ...buildMeritLineTraces(points, {
        slope: options.meritLines.slope,
        color: options.meritLines.color,
        dash: options.meritLines.dash,
      }),
    );
    layout.annotations.push({
      x: 0.02,
      y: 0.98,
      xref: "paper",
      yref: "paper",
      xanchor: "left",
      yanchor: "top",
      showarrow: false,
      text: options.meritLines.label,
      font: { size: 11, color: "#475569" },
      bgcolor: "rgba(255,255,255,0.88)",
      bordercolor: "#e5e7eb",
      borderwidth: 1,
      borderpad: 5,
    });
  }

  if (options.inlineKeyId) {
    addInlineKey(options.inlineKeyId, options.palette || "classic");
  }

  const config = {
    responsive: true,
    displayModeBar: true,
    modeBarButtonsToRemove: ["lasso2d", "select2d", "autoScale2d"],
    displaylogo: false,
  };

  await Plotly.newPlot(options.targetId, traces, layout, config);
}

window.renderAshbyPrototype = renderAshbyPrototype;
