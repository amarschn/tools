/* Plotly charts for the HVAC load calculator. Colors come from CSS variables so
   both themes stay in one place. */
(function () {
  'use strict';

  function cssVar(name) {
    return getComputedStyle(document.body).getPropertyValue(name).trim();
  }

  function baseLayout(xTitle, yTitle) {
    const text = cssVar('--text-color');
    const muted = cssVar('--text-light');
    const grid = cssVar('--border-color');
    return {
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      font: { family: cssVar('--font-sans') || 'system-ui, sans-serif', color: text, size: 12 },
      margin: { l: 66, r: 16, t: 12, b: 50 },
      hovermode: 'x unified',
      hoverlabel: { bgcolor: cssVar('--bg-card'), bordercolor: grid, font: { color: text } },
      legend: { orientation: 'h', x: 0, y: 1.14, font: { color: text } },
      xaxis: {
        title: { text: xTitle, font: { color: muted } }, gridcolor: grid, zerolinecolor: grid,
        tickfont: { color: muted }, linecolor: grid, type: 'linear',
      },
      yaxis: {
        title: { text: yTitle, font: { color: muted } }, gridcolor: grid, zerolinecolor: muted,
        tickfont: { color: muted }, linecolor: grid, type: 'linear', separatethousands: true,
      },
    };
  }

  const CONFIG = { displayModeBar: false, responsive: true };

  const HOURLY_SERIES = [
    ['windows', 'Windows', '--series-1'],
    ['walls', 'Walls', '--series-2'],
    ['ceiling', 'Ceiling', '--series-3'],
    ['air', 'Air leakage and ventilation', '--series-4'],
    ['internal', 'People and appliances', '--series-5'],
    ['floor', 'Floor and doors', '--series-6'],
  ];

  function hourly(el, cooling) {
    const surface = cssVar('--bg-card');
    const traces = HOURLY_SERIES.map(([key, name, color]) => ({
      type: 'bar',
      name,
      x: cooling.hours,
      y: cooling.hourly[key],
      marker: { color: cssVar(color), line: { color: surface, width: 1 } },
      hovertemplate: '%{y:,.0f} Btu/h<extra>' + name + '</extra>',
    }));
    traces.push({
      type: 'scatter',
      mode: 'lines',
      name: 'Capacity with allowed swing',
      x: [0.5, 24.5],
      y: [cooling.room_load, cooling.room_load],
      line: { color: cssVar('--text-color'), width: 2, dash: 'dash' },
      hoverinfo: 'skip',
    });
    const layout = baseLayout('Solar hour (add 1 for daylight time)', 'Sensible load before ducts (Btu/h)');
    layout.barmode = 'relative';
    layout.bargap = 0.12;
    layout.showlegend = false;
    layout.margin.t = 12;
    layout.xaxis.tick0 = 0;
    layout.xaxis.dtick = 3;
    layout.xaxis.range = [0.5, 24.5];
    layout.annotations = [{
      x: 1, y: cooling.room_load, xref: 'x', yref: 'y', xanchor: 'left', yanchor: 'bottom', showarrow: false,
      text: Math.round(cooling.room_load).toLocaleString() + ' Btu/h',
      font: { size: 11, color: cssVar('--text-color') },
    }];
    Plotly.react(el, traces, layout, CONFIG);
    const key = document.getElementById('hourly-key');
    if (key) {
      key.innerHTML = HOURLY_SERIES.map(([, name, color]) => (
        `<span class="key-item"><span class="key-swatch" style="background:${cssVar(color)}"></span>${name}</span>`
      )).join('') + '<span class="key-item"><span class="key-line"></span>Capacity with allowed swing</span>';
    }
  }

  function temps(el, cooling) {
    const series = [
      ['Attic air', cooling.t_attic, '--series-2'],
      ['Outdoor air', cooling.t_out, '--series-1'],
    ];
    const traces = series.map(([name, y, color]) => ({
      type: 'scatter', mode: 'lines', name, x: cooling.hours, y,
      line: { color: cssVar(color), width: 2 },
      hovertemplate: '%{y:.0f} °F<extra>' + name + '</extra>',
    }));
    const layout = baseLayout('Solar hour of the design day', 'Temperature (°F)');
    layout.xaxis.dtick = 3;
    layout.xaxis.range = [1, 24];
    layout.margin.t = 34;
    Plotly.react(el, traces, layout, CONFIG);
  }

  function balance(el, chart, equipment, design) {
    const traces = [
      {
        type: 'scatter', mode: 'lines', name: 'House heat loss', x: chart.t, y: chart.load,
        line: { color: cssVar('--series-2'), width: 2 },
        hovertemplate: '%{y:,.0f} Btu/h<extra>House heat loss</extra>',
      },
      {
        type: 'scatter', mode: 'lines', name: 'Heat pump maximum capacity', x: chart.t, y: chart.capacity,
        line: { color: cssVar('--series-1'), width: 2 },
        hovertemplate: '%{y:,.0f} Btu/h<extra>Heat pump capacity</extra>',
      },
    ];
    const layout = baseLayout('Outdoor temperature (°F)', 'Heat (Btu/h)');
    layout.margin.t = 34;
    layout.yaxis.rangemode = 'tozero';
    layout.shapes = [{
      type: 'line', x0: design, x1: design, yref: 'paper', y0: 0, y1: 1,
      line: { color: cssVar('--text-light'), width: 1, dash: 'dot' },
    }];
    layout.annotations = [{
      x: design, yref: 'paper', y: 1, yanchor: 'top', xanchor: 'left', showarrow: false,
      text: ' Design ' + design.toFixed(0) + ' °F', font: { size: 11, color: cssVar('--text-light') },
    }];
    if (equipment.balance_point_f !== null && equipment.balance_point_f !== undefined) {
      const t = equipment.balance_point_f;
      const y = chart.load.reduce((best, value, i) => (
        Math.abs(chart.t[i] - t) < Math.abs(chart.t[best] - t) ? i : best), 0);
      traces.push({
        type: 'scatter', mode: 'markers', name: 'Balance point',
        x: [t], y: [chart.load[y]],
        marker: { color: cssVar('--text-color'), size: 10, line: { color: cssVar('--bg-card'), width: 2 } },
        hovertemplate: 'Balance point ' + t.toFixed(0) + ' °F<extra></extra>',
      });
      layout.annotations.push({
        x: t, y: chart.load[y], xanchor: 'left', yanchor: 'bottom', ax: 14, ay: -22, showarrow: true,
        arrowcolor: cssVar('--text-light'), text: 'Balance point ' + t.toFixed(0) + ' °F',
        font: { size: 11, color: cssVar('--text-color') },
      });
    }
    Plotly.react(el, traces, layout, CONFIG);
  }

  function bins(el, station, binWidth) {
    const x = station.b.map((_, i) => station.b0 + (i + 0.5) * binWidth);
    const traces = [{
      type: 'bar', name: 'Hours per year', x, y: station.b, width: binWidth * 0.86,
      marker: { color: cssVar('--series-1') },
      hovertemplate: '%{y:,.0f} hours at %{x} °F<extra></extra>',
    }];
    const layout = baseLayout('Outdoor temperature, 5 °F bins (°F)', 'Hours per year');
    layout.showlegend = true;
    layout.margin.t = 34;
    Plotly.react(el, traces, layout, CONFIG);
  }

  window.HvacCharts = { hourly, temps, balance, bins };
})();
