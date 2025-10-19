import pint
import math
from handcalcs.decorator import handcalc
import functools # For wraps

# --- Pint Setup ---
ureg = pint.UnitRegistry(autoconvert_offset_to_baseunit=True)
# Define expected base units for clarity, though Pint handles conversions
_m = ureg.meter
_s = ureg.second
_kg = ureg.kilogram
_rad = ureg.radian
_deg = ureg.degree
_g_accel = ureg.standard_gravity # 9.80665 m/s²

# --- Calculation Registry ---
CALCULATION_REGISTRY = {}

# --- Decorator ---
def register_calculation(calc_id, name, description, parameters_meta, returns_meta, latex_overview=""):
    """
    Decorator to register an engineering calculation function.

    Args:
        calc_id (str): A unique identifier for the calculation.
        name (str): A user-friendly name for the calculation.
        description (str): A brief description of what the calculation does.
        parameters_meta (list): A list of dictionaries, each describing an input parameter.
            Required keys: 'name', 'description', 'unit_type' (e.g., 'velocity', 'angle', 'length'), 'default_unit'.
        returns_meta (list): A list of dictionaries, each describing a return value.
            Required keys: 'name', 'description', 'unit_type', 'base_unit'.
        latex_overview (str): Optional LaTeX string representing the general formulas.
    """
    def decorator(func):
        @functools.wraps(func) # Preserves original function metadata
        def wrapper(*args, **kwargs):
            # Potentially add pre-processing or validation here if needed
            results = func(*args, **kwargs)
            # Potentially add post-processing here if needed
            return results

        # Store metadata and the original (wrapped) function
        CALCULATION_REGISTRY[calc_id] = {
            "function": func, # Store the original function for calling
            "name": name,
            "description": description,
            "parameters_meta": parameters_meta,
            "returns_meta": returns_meta,
            "latex_overview": latex_overview,
            # We expect the handcalc decorator to add _handcalcs_latex later
        }
        # print(f"Registered calculation: {calc_id}") # Debugging
        return wrapper # Return the wrapper if you added pre/post processing logic
                       # Or return func if the wrapper doesn't do anything extra now
                       # Let's return func directly for simplicity now, but keep the wrapper structure
                       # Correction: We need the actual function for handcalcs to decorate
                       # The registry should store the *original* decorated func
        CALCULATION_REGISTRY[calc_id]["function"] = func
        return func # Return the original function so handcalc can decorate it

    return decorator

# --- API Functions for Pyodide ---

def get_calculation_manifest():
    """Returns a serializable dictionary describing available calculations."""
    manifest = {}
    for calc_id, data in CALCULATION_REGISTRY.items():
        # Exclude the raw function object, just send metadata
        manifest[calc_id] = {
            "name": data["name"],
            "description": data["description"],
            "parameters_meta": data["parameters_meta"],
            "returns_meta": data["returns_meta"],
            "latex_overview": data["latex_overview"],
        }
    return manifest

def run_calculation(calc_id, input_data):
    """
    Runs a registered calculation.

    Args:
        calc_id (str): The ID of the calculation to run.
        input_data (dict): Dictionary of input parameter names to their values (as numbers/strings from JS).

    Returns:
        dict: A dictionary containing:
            'results': Dictionary of result names to {'value': float, 'unit': str}.
            'handcalcs_latex': The step-by-step LaTeX string from handcalcs.
            'error': An error message string, if any occurred.
    """
    if calc_id not in CALCULATION_REGISTRY:
        return {"error": f"Calculation '{calc_id}' not found."}

    calc_info = CALCULATION_REGISTRY[calc_id]
    func = calc_info["function"]
    params_meta = calc_info["parameters_meta"]

    pint_inputs = {}
    try:
        # Convert JS inputs (expected as numbers) into Pint Quantities
        for meta in params_meta:
            param_name = meta['name']
            if param_name not in input_data:
                return {"error": f"Missing input parameter: {param_name}"}

            value = input_data[param_name]
            unit_str = meta['default_unit'] # Use the defined default unit

            # Basic type check
            try:
                value = float(value)
            except ValueError:
                 return {"error": f"Invalid numeric value for {param_name}: {value}"}

            pint_inputs[param_name] = ureg.Quantity(value, unit_str)
            # print(f"Converted input: {param_name} = {pint_inputs[param_name]}") # Debugging

        # Run the actual calculation function
        # Handcalcs runs *during* this function call
        results_pint = func(**pint_inputs)

        # Retrieve the handcalcs LaTeX output
        handcalcs_latex = getattr(func, '_handcalcs_latex', "Handcalcs LaTeX not generated.")

        # Format results for serialization (convert Pint Quantities back to value/unit strings)
        formatted_results = {}
        for key, value in results_pint.items():
            if isinstance(value, pint.Quantity):
                 # Check if magnitude is an array (though not expected here)
                 mag = value.magnitude
                 if hasattr(mag, 'tolist'): # Handle numpy arrays if they appear
                     mag = mag.tolist()
                 formatted_results[key] = {"value": mag, "unit": f"{value.units:~P}"} # ~P for pretty unicode
            else:
                 # Handle non-pint results if any (shouldn't happen with good practice)
                 formatted_results[key] = {"value": value, "unit": ""}

        return {
            "results": formatted_results,
            "handcalcs_latex": handcalcs_latex,
            "error": None
        }

    except pint.DimensionalityError as e:
        return {"error": f"Unit Mismatch Error: {e}"}
    except Exception as e:
        import traceback
        print(f"Error during calculation '{calc_id}':")
        traceback.print_exc() # Print full traceback to Pyodide console
        return {"error": f"Calculation Error: {type(e).__name__}: {e}"}


# --- Example Calculation: Ballistic Trajectory (No Air Resistance) ---

@register_calculation(
    calc_id="ballistic_trajectory_simple",
    name="Simple Ballistic Trajectory",
    description="Calculates range, max height, and time of flight for a projectile launched from y=0 with no air resistance.",
    parameters_meta=[
        {'name': 'v0', 'description': 'Initial Velocity', 'unit_type': 'velocity', 'default_unit': 'm/s'},
        {'name': 'theta', 'description': 'Launch Angle (from horizontal)', 'unit_type': 'angle', 'default_unit': 'deg'},
        # Optional: Allow overriding gravity
        # {'name': 'g', 'description': 'Gravitational Acceleration', 'unit_type': 'acceleration', 'default_unit': 'm/s**2'}
    ],
    returns_meta=[
        {'name': 't_flight', 'description': 'Total Time of Flight', 'unit_type': 'time', 'base_unit': 's'},
        {'name': 't_peak', 'description': 'Time to Reach Peak Height', 'unit_type': 'time', 'base_unit': 's'},
        {'name': 'max_height', 'description': 'Maximum Height Reached (relative to launch)', 'unit_type': 'length', 'base_unit': 'm'},
        {'name': 'range_x', 'description': 'Horizontal Range Covered', 'unit_type': 'length', 'base_unit': 'm'},
        {'name': 'vx', 'description': 'Horizontal Velocity (Constant)', 'unit_type': 'velocity', 'base_unit': 'm/s'},
        {'name': 'vy0', 'description': 'Initial Vertical Velocity', 'unit_type': 'velocity', 'base_unit': 'm/s'},
    ],
    latex_overview=r"""
        \text{Assumptions: No air resistance, launch height } y_0 = 0. \\
        v_{x} = v_0 \cos(\theta) \\
        v_{y0} = v_0 \sin(\theta) \\
        t_{peak} = \frac{v_{y0}}{g} \\
        t_{flight} = 2 \times t_{peak} \\
        y_{max} = v_{y0} t_{peak} - \frac{1}{2} g t_{peak}^2 = \frac{v_{y0}^2}{2g} \\
        x_{range} = v_x \times t_{flight}
    """
)
@handcalc(override="long", precision=3) # Apply handcalc decorator *inside* register_calculation
def calculate_ballistic_trajectory(v0: ureg.Quantity, theta: ureg.Quantity):
    """
    Performs the ballistic trajectory calculation using Pint and Handcalcs.

    Args:
        v0: Initial velocity (Quantity with velocity units).
        theta: Launch angle (Quantity with angle units).

    Returns:
        dict: Dictionary of result Quantities.
    """
    # Use standard gravity by default
    g = _g_accel

    # --- Handcalcs section ---
    # Note: Handcalcs works best with direct calculations.
    # Ensure inputs are in correct units for formulas (e.g., radians for trig)
    theta_rad = theta.to(_rad) # Convert angle to radians for math functions

    # Calculate initial velocity components
    vx = v0 * math.cos(theta_rad)
    vy0 = v0 * math.sin(theta_rad)

    # Calculate time to peak height
    t_peak = vy0 / g

    # Calculate total time of flight (assuming y0 = 0)
    t_flight = 2 * t_peak

    # Calculate maximum height (relative to launch)
    # Using the formula y_max = vy0**2 / (2*g) for simplicity with handcalcs display
    max_height = (vy0**2) / (2 * g)
    # Alternative: max_height = vy0 * t_peak - 0.5 * g * t_peak**2

    # Calculate horizontal range
    range_x = vx * t_flight
    # --- End Handcalcs section ---

    # Return results as a dictionary of Pint quantities
    # Handcalcs stores its LaTeX in func._handcalcs_latex automatically
    return {
        "t_flight": t_flight,
        "t_peak": t_peak,
        "max_height": max_height,
        "range_x": range_x,
        "vx": vx, # Include components for reference
        "vy0": vy0
    }

# --- Optional: Add more calculations here following the same pattern ---

# Example: Simple Stress Calculation
@register_calculation(
    calc_id="axial_stress",
    name="Axial Stress",
    description="Calculates the axial stress in a member under load.",
    parameters_meta=[
        {'name': 'F', 'description': 'Axial Force', 'unit_type': 'force', 'default_unit': 'N'},
        {'name': 'A', 'description': 'Cross-sectional Area', 'unit_type': 'area', 'default_unit': 'mm**2'},
    ],
    returns_meta=[
        {'name': 'sigma', 'description': 'Axial Stress', 'unit_type': 'pressure', 'base_unit': 'Pa'},
    ],
    latex_overview=r"\sigma = \frac{F}{A}"
)
@handcalc(override="long", precision=4)
def calculate_axial_stress(F: ureg.Quantity, A: ureg.Quantity):
    """Calculates axial stress."""
    # --- Handcalcs section ---
    sigma = F / A
    # --- End Handcalcs section ---
    return {"sigma": sigma}


print("hand_calcs.py loaded and calculations registered.")
# You can uncomment this to see the registry in the console when loaded by Pyodide
# print("Registry:", CALCULATION_REGISTRY)