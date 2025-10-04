import json
from whistle_acoustics import (
    speed_of_sound,
    open_closed_mode_frequencies,
    helmholtz_frequency,
    get_locking_table,
    format_locking_table,
    DEFAULT_STAGES
)

# --- PRESETS ---
# These presets will be fetched by the JavaScript frontend.
PRESETS = {
    "default": {
        "model": "pipe", "T": 293.15, "d": 0.001,
        "L": 0.3, "end_corr": 0.005, "n_max": 6,
        "A": 5e-5, "V": 30e-6, "L_eff": 0.01,
        "stages": ",".join(map(str, DEFAULT_STAGES))
    },
    "tin_whistle": {
        "model": "pipe", "T": 293.15, "d": 0.0008,
        "L": 0.28, "end_corr": 0.004, "n_max": 7,
        "stages": "0.2,0.4,0.7,1.0,1.3,1.6"
    },
    "bottle_blow": {
        "model": "helmholtz", "T": 293.15, "d": 0.002,
        "A": 3.14e-4, "V": 750e-6, "L_eff": 0.04
    }
}

def get_presets():
    """Returns the presets dictionary to be used in JavaScript."""
    return PRESETS

def get_sanitized_params(js_params):
    """
    Extracts and sanitizes parameters passed from JavaScript.
    js_params is a PyProxy object that behaves like a dictionary.
    """
    params = PRESETS["default"].copy() # Start with defaults
    
    # Helper to safely convert form values to float/int
    def get_typed_val(name, target_type, default):
        try:
            val = js_params.get(name)
            return target_type(val) if val is not None else default
        except (ValueError, TypeError):
            return default

    params["model"] = js_params.get('model', params["model"])
    params["T"] = get_typed_val('T', float, params["T"])
    params["d"] = get_typed_val('d', float, params["d"])
    
    # Sanitize stages string
    stages_str = js_params.get('stages', params["stages"])
    try:
        parsed_stages = [float(x) for x in stages_str.split(',') if x.strip()]
        params["stages"] = ",".join(map(str, parsed_stages))
    except (ValueError, TypeError):
        pass # Keep default if parsing fails

    # Pipe-specific parameters
    params["L"] = get_typed_val('L', float, params["L"])
    params["n_max"] = get_typed_val('n_max', int, params["n_max"])
    params["end_corr"] = get_typed_val('end_corr', float, params["end_corr"])
    
    # Helmholtz-specific parameters
    params["A"] = get_typed_val('A', float, params["A"])
    params["V"] = get_typed_val('V', float, params["V"])
    params["L_eff"] = get_typed_val('L_eff', float, params["L_eff"])
    
    return params

def generate_plot_data(resonator_modes, d, stages, locking_results):
    """Generates the data traces needed for the Plotly.js visualization."""
    max_freq = max(resonator_modes) * 1.2 if resonator_modes else 1000
    max_U = max((r.required_U for r in locking_results), default=50) * 1.2

    # 1. Traces for resonator mode frequencies (horizontal lines)
    resonator_traces = [
        {
            "x": [0, max_U], "y": [f, f],
            "mode": 'lines', "line": {"dash": 'dash', "color": '#0ea5e9'},
            "name": f'Mode {i} ({f:.0f} Hz)',
            "hoverinfo": "name"
        } for i, f in enumerate(resonator_modes, start=1)
    ]

    # 2. Traces for edge-tone stages (diagonal lines)
    edgetone_traces = [
        {
            "x": [0, max_U], "y": [0, St * max_U / d],
            "mode": 'lines', "line": {"dash": 'dot', "color": '#84cc16'},
            "name": f'Stage {i} (St={St})',
            "hoverinfo": "name"
        } for i, St in enumerate(stages, start=1)
    ]
        
    # 3. Trace for locking points (markers)
    locking_points_trace = {
        "x": [r.required_U for r in locking_results],
        "y": [r.mode_frequency for r in locking_results],
        "text": [f'Locking!<br>U: {r.required_U:.2f} m/s<br>Freq: {r.mode_frequency:.0f} Hz<br>Stage {r.stage_index} (St={r.St})' for r in locking_results],
        "mode": 'markers',
        "marker": {"size": 10, "color": '#f97316'},
        "name": 'Locking Points',
        "hoverinfo": "text"
    }

    plot_payload = {
        "data": resonator_traces + edgetone_traces + [locking_points_trace],
        "layout": {
            "title": 'Frequency vs. Jet Speed',
            "xaxis": {"title": 'Jet Speed U (m/s)', "range": [0, max_U]},
            "yaxis": {"title": 'Frequency (Hz)', "range": [0, max_freq]},
            "showlegend": True,
            "legend": {"orientation": "h", "y": -0.2, "x": 0.5, "xanchor": "center"},
            "margin": {"l": 60, "r": 20, "t": 40, "b": 50},
            "hovermode": "closest",
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "font": {"color": "#6b7280"}
        }
    }
    # Return as a JSON string because it's easier to parse in JS
    return json.dumps(plot_payload)

def calculate_acoustics(js_params):
    """
    Main calculation function called from JavaScript.
    It takes a PyProxy object from JS, processes it, and returns a Python dict.
    """
    params = get_sanitized_params(js_params)
    c = speed_of_sound(params['T'])
    stages = [float(s) for s in params['stages'].split(',')]
    
    resonator_modes = []
    if params['model'] == 'pipe':
        resonator_modes = open_closed_mode_frequencies(params['L'], c, n_max=params['n_max'], end_correction=params['end_corr'])
    else: # helmholtz
        freq = helmholtz_frequency(params['A'], params['V'], params['L_eff'], c)
        resonator_modes.append(freq)

    locking_results = get_locking_table(resonator_modes, params['d'], stages)
    table_data = format_locking_table(locking_results)
    
    plot_payload_str = generate_plot_data(resonator_modes, params['d'], stages, locking_results)
    
    return {
        "c": c,
        "resonator_modes": resonator_modes,
        "table": table_data,
        "plot_payload": plot_payload_str
    }
