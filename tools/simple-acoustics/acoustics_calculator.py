# acoustics_calculator.py
import math
import numpy as np
import traceback # Import traceback for detailed error logging

# =====================================================================
# CONSTANTS
# =====================================================================
REFERENCE_PRESSURE = 2e-5  # 20 µPa in Pa
REFERENCE_POWER = 1e-12    # 10^-12 watts

# A-weighting coefficients (simplified octave band values)
A_WEIGHTING_OCTAVE = {
    '63': -26.2, '125': -16.1, '250': -8.6, '500': -3.2,
    '1000': 0, '2000': 1.2, '4000': 1.0, '8000': -1.1,
    'broadband': 0
}

# C-weighting coefficients (simplified octave band values)
C_WEIGHTING_OCTAVE = {
    '63': -0.8, '125': -0.2, '250': 0, '500': 0,
    '1000': 0, '2000': -0.2, '4000': -0.8, '8000': -3.0,
    'broadband': 0
}

# =====================================================================
# CALCULATION HELPER FUNCTIONS
# =====================================================================

def calculate_point_source_spl(swl, distance, directivity_factor_str):
    """Calculates SPL for a point source."""
    if distance <= 1e-6: # Use a small epsilon instead of zero
        print(f"Warning: Distance near zero ({distance}) for point source, returning high SPL.")
        # Avoid log(0), return a very high value or handle as error? Let's return high value.
        # A very small distance should yield very high SPL. Arbitrarily cap or estimate based on near field.
        # For simplicity, let's estimate based on 0.1m distance.
        distance = 0.1
        # return np.inf # Alternative: Indicate infinite SPL

    try:
        Q = float(directivity_factor_str)
        if Q <= 1e-6: # Use epsilon check for Q too
            print(f"Warning: Non-positive directivity factor Q={Q}, using Q=1.")
            Q = 1.0
    except ValueError:
        print(f"Warning: Invalid directivity factor '{directivity_factor_str}', using Q=1.")
        Q = 1.0

    # Formula: SWL - 20*log10(r) - 10*log10(4pi) + 10*log10(Q)
    # 10*log10(4pi) is approx 10.99, often rounded to 11
    spl = swl - 20 * math.log10(distance) - 11 + 10 * math.log10(Q)
    return spl

def calculate_line_source_spl(swl, distance):
    """Calculates SPL for an infinite line source (simplified)."""
    if distance <= 1e-6:
        print(f"Warning: Distance near zero ({distance}) for line source, returning high SPL.")
        # Similar to point source, estimate based on a small distance like 0.1m
        distance = 0.1
        # return np.inf

    # Formula: SWL' - 10*log10(r) - C (C depends on ref length, often ~8)
    # Assumes SWL is defined appropriately (e.g., per meter)
    spl = swl - 10 * math.log10(distance) - 8
    return spl

def calculate_plane_source_spl(swl, distance):
    """Calculates SPL for a plane source (highly simplified)."""
    # Near a large plane source, SPL is relatively independent of distance.
    # This model is very basic. Assume SWL is defined for the source area implicitly.
    # Let's just apply a small fixed reduction from SWL.
    spl = swl - 3
    return spl

def apply_weighting(spl, frequency_key, weighting_type):
    """Applies A or C frequency weighting based on octave band key."""
    if weighting_type == 'Z' or frequency_key == 'broadband':
        return spl

    weighting_map = A_WEIGHTING_OCTAVE if weighting_type == 'A' else C_WEIGHTING_OCTAVE
    adjustment = weighting_map.get(str(frequency_key), 0) # Ensure key is string
    return spl + adjustment

def calculate_air_absorption(frequency_key, distance, temp_c, rel_humidity):
    """Calculates air absorption attenuation (simplified model)."""
    if distance <= 0: return 0

    # Approx dB/km at 20C, 60% RH for octave bands
    absorption_coeffs_db_km = {
        '63': 0.1, '125': 0.4, '250': 1.0, '500': 1.9,
        '1000': 3.7, '2000': 9.7, '4000': 28.0, '8000': 75.0,
        'broadband': 5.0 # Rough broadband average
    }

    coeff_db_km = absorption_coeffs_db_km.get(str(frequency_key), absorption_coeffs_db_km['broadband'])

    # Crude adjustments for Temp/Humidity (ISO 9613-1 is much more complex)
    temp_factor = 1.0 # Reference 20C
    if temp_c < 10: temp_factor = 1.2
    elif temp_c > 30: temp_factor = 0.8

    humidity_factor = 1.0 # Reference 60%
    if rel_humidity < 40: humidity_factor = 1.3 # Higher absorption at low humidity
    elif rel_humidity > 80: humidity_factor = 0.8 # Lower absorption at high humidity

    # Crude frequency dependency for adjustments (stronger effect at high freq)
    freq_hz_int = 0
    try:
        freq_hz_int = int(frequency_key)
        if freq_hz_int >= 2000:
             humidity_factor = 1 + (humidity_factor - 1) * 1.8 # Amplify effect more
             temp_factor = 1 + (temp_factor - 1) * 1.4
        elif freq_hz_int <= 500: # Less effect at low freq
             humidity_factor = 1 + (humidity_factor - 1) * 0.5
             temp_factor = 1 + (temp_factor - 1) * 0.5
    except ValueError: # broadband case
         pass # Use base factors

    effective_coeff_db_km = coeff_db_km * temp_factor * humidity_factor
    absorption_db = (effective_coeff_db_km / 1000.0) * distance # Convert km to m

    return max(0, absorption_db) # Attenuation cannot be negative

def calculate_ground_effect(distance, ground_absorption_coeff, frequency_key):
    """Calculates ground effect attenuation (simplified model based on G factor)."""
    if distance <= 1 or ground_absorption_coeff <= 0:
        return 0 # No effect very close or for hard ground (G=0)

    # Model: Attenuation increases with G, distance (log), and is frequency dependent
    freq_factor = 1.0
    freq_hz_int = 0
    try:
        freq_hz_int = int(frequency_key)
        if 250 <= freq_hz_int <= 1000: freq_factor = 1.5 # Strongest effect in mid-low freq
        elif freq_hz_int < 250: freq_factor = 1.2
        elif freq_hz_int > 1000: freq_factor = 0.8
    except ValueError: # broadband
        freq_factor = 1.0

    # Max attenuation scales with G (e.g., up to ~6dB for G=1)
    max_attenuation_soft_ground = 6.0
    # Attenuation increases logarithmically with distance, scaled by G and freq factor
    # Add small value to distance inside log10 to avoid log10(1)=0 if distance is exactly 1
    attenuation = ground_absorption_coeff * freq_factor * 1.5 * math.log10(distance + 0.1)

    # Cap the attenuation based on ground type
    max_possible_attenuation = max_attenuation_soft_ground * ground_absorption_coeff
    return min(max(0, attenuation), max_possible_attenuation) # Ensure 0 <= Attenuation <= Max


def calculate_barrier_attenuation(num_barriers, attenuation_per_barrier):
    """Calculates total barrier attenuation (simple additive model)."""
    if num_barriers <= 0 or attenuation_per_barrier <= 0:
        return 0
    return float(num_barriers) * float(attenuation_per_barrier)

# =====================================================================
# CORE CALCULATION FUNCTION
# =====================================================================
def calculate_total_spl(
    source_type, swl, distance, directivity_factor_str,
    frequency_key, ground_absorption_coeff, air_attenuation_enabled,
    temp_c, humidity, num_barriers, barrier_attenuation_db
):
    """Calculates the final SPL after accounting for all effects."""

    # Ensure distance is positive for calculations
    current_dist = max(distance, 1e-6)

    # 1. Calculate base SPL based on source type and distance
    spl = -np.inf # Default to invalid
    if source_type == 'point':
        spl = calculate_point_source_spl(swl, current_dist, directivity_factor_str)
    elif source_type == 'line':
        spl = calculate_line_source_spl(swl, current_dist)
    elif source_type == 'plane':
        spl = calculate_plane_source_spl(swl, current_dist) # Distance has minimal effect in this model

    if spl == -np.inf or math.isnan(spl):
        print(f"Warning: Base SPL calculation failed for dist {current_dist}. Returning 0.")
        return 0

    # 2. Apply ground effect (attenuation)
    ground_attenuation = calculate_ground_effect(current_dist, ground_absorption_coeff, frequency_key)
    spl -= ground_attenuation

    # 3. Apply air absorption if enabled (attenuation)
    air_attenuation = 0
    if air_attenuation_enabled:
        air_attenuation = calculate_air_absorption(frequency_key, current_dist, temp_c, humidity)
        spl -= air_attenuation

    # 4. Apply barrier attenuation
    barrier_effect = calculate_barrier_attenuation(num_barriers, barrier_attenuation_db)
    spl -= barrier_effect

    # Ensure SPL is not below 0 (realistic floor for environmental SPL)
    return max(0, spl)

# =====================================================================
# MAIN FUNCTION (Called from JavaScript via Pyodide)
# =====================================================================
def run_calculation(inputs_proxy):
    """
    Performs the full SPL calculation over a range of distances.

    Args:
        inputs_proxy (JsProxy): A Pyodide proxy for the JS input object.

    Returns:
        dict: A dictionary containing the results or an error message.
    """
    try:
        # Convert the JsProxy to a Python dictionary immediately for robustness
        inputs = dict(inputs_proxy.to_py())

        # Extract and validate inputs
        source_type = inputs.get('sourceType', 'point')
        swl = float(inputs.get('swl', 100))
        distance_min = float(inputs.get('distanceMin', 1))
        distance_max = float(inputs.get('distanceMax', 100))
        directivity_factor_str = str(inputs.get('directivityFactor', '2')) # Keep as string initially
        frequency_key = str(inputs.get('frequency', 'broadband')) # Ensure string key
        weighting_type = inputs.get('weighting', 'A')
        ground_absorption = float(inputs.get('groundAbsorption', 0.5))
        # Explicitly handle boolean conversion for checkbox
        air_attenuation_enabled = inputs.get('airAttenuationEnabled', True)
        if isinstance(air_attenuation_enabled, str): # Handle if passed as string 'true'/'false'
            air_attenuation_enabled = air_attenuation_enabled.lower() == 'true'
        else:
             air_attenuation_enabled = bool(air_attenuation_enabled)

        temp_c = float(inputs.get('tempC', 20))
        humidity = float(inputs.get('humidity', 60))
        num_barriers = int(inputs.get('barriers', 0))
        barrier_attenuation = float(inputs.get('barrierAttenuation', 5))

        # Sanitize distance inputs
        distance_min = max(distance_min, 0.1) # Ensure min distance is at least 0.1m
        distance_max = max(distance_max, distance_min + 1) # Ensure max > min

        # Generate distance array
        num_points = 50
        if source_type == 'point':
            # Use logspace only if min distance > 0
            distances = np.logspace(np.log10(distance_min), np.log10(distance_max), num_points)
        else:
            # Use linspace for line/plane
            distances = np.linspace(distance_min, distance_max, num_points)

        # Calculate SPL at each distance
        spls = []
        spls_weighted = []
        for dist in distances:
            spl = calculate_total_spl(
                source_type, swl, dist, directivity_factor_str,
                frequency_key, ground_absorption, air_attenuation_enabled,
                temp_c, humidity, num_barriers, barrier_attenuation
            )
            spls.append(spl)
            weighted_spl = apply_weighting(spl, frequency_key, weighting_type)
            spls_weighted.append(weighted_spl)

        # Calculate single point result at 1m (or distance_min if 1m is not valid)
        calc_dist_1m = max(1.0, distance_min) # Calculate at 1m or the minimum distance if > 1m
        spl_1m = calculate_total_spl(
            source_type, swl, calc_dist_1m, directivity_factor_str,
            frequency_key, ground_absorption, air_attenuation_enabled,
            temp_c, humidity, num_barriers, barrier_attenuation
        )
        spl_weighted_1m = apply_weighting(spl_1m, frequency_key, weighting_type)

        # Return results as a dictionary
        return {
            'distances': distances.tolist(), # Convert numpy array to list for JS
            'spls': spls,
            'spls_weighted': spls_weighted,
            'spl_1m': spl_1m,
            'spl_weighted_1m': spl_weighted_1m,
            'calc_dist_1m': calc_dist_1m
        }

    except Exception as e:
        # Log the full traceback to the console where Pyodide runs (browser dev console)
        print("--- Python Error Traceback ---")
        print(traceback.format_exc())
        print("-----------------------------")
        # Return an error structure to JavaScript
        return {
            'error': f"{type(e).__name__}: {e}", # Include exception type and message
            'distances': [], 'spls': [], 'spls_weighted': [],
            'spl_1m': 0, 'spl_weighted_1m': 0, 'calc_dist_1m': 1
        }