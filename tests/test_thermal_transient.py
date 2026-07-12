"""Tests for the transient thermal RC simulator."""

from __future__ import annotations

import math

import pytest

from pycalcs import heatsinks
from pycalcs.thermal_transient import (
    build_plate_fin_transient_model,
    compute_design_lever_recommendation,
    compute_plate_fin_sink_properties,
    estimate_thermal_capacitance,
    generate_power_profile,
    generate_transient_sensitivity,
    get_material_presets,
    simulate_transient_thermal_model,
    validate_transient_thermal_model,
)


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #


def one_lump_model(
    *,
    capacitance: float,
    resistance: float,
    power: float,
    duration: float,
    ambient: float = 25.0,
    initial: float = 25.0,
    profile_type: str = "step",
    profile_extras: dict | None = None,
    initial_temperature_c_node: float | None = None,
    max_temperature_c: float | None = None,
    time_step_s: float | None = None,
    cooldown_target_c: float | None = None,
) -> dict:
    profile = {"type": profile_type, "power_w": power}
    if profile_extras:
        profile = {**profile, **profile_extras}
    return {
        "time": {
            "duration_s": duration,
            "time_step_s": time_step_s,
            "initial_temperature_c": initial,
            "cooldown_target_c": cooldown_target_c,
        },
        "profile": profile,
        "network": {
            "nodes": [
                {
                    "id": "lump",
                    "label": "Lump",
                    "kind": "dynamic",
                    "capacitance_j_per_k": capacitance,
                    "max_temperature_c": max_temperature_c,
                    "initial_temperature_c": initial_temperature_c_node,
                },
                {
                    "id": "ambient",
                    "label": "Ambient",
                    "kind": "boundary",
                    "fixed_temperature_c": ambient,
                },
            ],
            "segments": [
                {
                    "id": "r_la",
                    "label": "Lump to ambient",
                    "from_node_id": "lump",
                    "to_node_id": "ambient",
                    "resistance_k_per_w": resistance,
                }
            ],
            "heat_inputs": [{"node_id": "lump", "profile_role": "primary"}],
        },
    }


# --------------------------------------------------------------------------- #
# Material / capacitance helpers                                              #
# --------------------------------------------------------------------------- #


def test_material_presets_have_required_fields() -> None:
    presets = get_material_presets()
    assert "aluminum_6063" in presets
    for preset in presets.values():
        assert preset["density_kg_per_m3"] > 0
        assert preset["heat_capacity_j_per_kgk"] > 0


def test_estimate_thermal_capacitance_with_preset() -> None:
    out = estimate_thermal_capacitance(volume_m3=1e-4, material_id="aluminum_6063")
    expected = 2700.0 * 1e-4 * 900.0  # rho * V * cp
    assert math.isclose(out["capacitance_j_per_k"], expected, rel_tol=1e-9)
    assert math.isclose(out["mass_kg"], 0.27, rel_tol=1e-6)
    assert "C = " in out["subst_capacitance"]


def test_estimate_thermal_capacitance_overrides_preset() -> None:
    out = estimate_thermal_capacitance(
        volume_m3=1e-4, material_id="aluminum_6063", density_kg_per_m3=8000.0
    )
    assert out["density_kg_per_m3"] == 8000.0
    assert out["heat_capacity_j_per_kgk"] == 900.0  # preset cp retained


def test_estimate_thermal_capacitance_requires_material_or_overrides() -> None:
    with pytest.raises(ValueError):
        estimate_thermal_capacitance(volume_m3=1e-4)


# --------------------------------------------------------------------------- #
# Power profiles                                                              #
# --------------------------------------------------------------------------- #


def test_step_profile_is_constant() -> None:
    times = [0.0, 1.0, 2.0]
    series = generate_power_profile({"type": "step", "power_w": 12.0}, times)
    assert series == [12.0, 12.0, 12.0]


def test_pulse_profile_drops_after_duration() -> None:
    times = [0.0, 1.0, 2.0, 3.0]
    series = generate_power_profile(
        {"type": "pulse", "pulse_power_w": 50.0, "pulse_duration_s": 1.5}, times
    )
    assert series == [50.0, 50.0, 0.0, 0.0]


def test_duty_cycle_profile_alternates() -> None:
    times = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]
    series = generate_power_profile(
        {
            "type": "duty_cycle",
            "on_power_w": 10.0,
            "on_time_s": 2.0,
            "off_power_w": 0.0,
            "off_time_s": 1.0,
        },
        times,
    )
    # cycle = 3 s; phase 0,1 -> on; phase 2 -> off; phase 0,1 -> on; phase 2 -> off
    assert series == [10.0, 10.0, 0.0, 10.0, 10.0, 0.0]


# --------------------------------------------------------------------------- #
# One-lump validation against analytical solution                             #
# --------------------------------------------------------------------------- #


def test_one_lump_step_response_matches_analytical() -> None:
    R = 2.0  # K/W
    C = 100.0  # J/K
    Q = 10.0  # W
    ambient = 25.0
    duration = 5.0 * R * C  # five time constants
    model = one_lump_model(
        capacitance=C, resistance=R, power=Q, duration=duration, ambient=ambient,
        time_step_s=R * C / 100.0,  # tight grid for analytic comparison
    )
    result = simulate_transient_thermal_model(model)
    assert result["status"] == "acceptable"
    times = result["series"]["time_s"]
    temps = result["series"]["node_temperatures_c"]["lump"]
    asymptote = ambient + Q * R
    for t, T in zip(times, temps):
        T_analytic = ambient + Q * R * (1.0 - math.exp(-t / (R * C)))
        # Implicit Euler is first-order accurate; tolerate ~2% of the
        # asymptotic rise.
        rise = max(asymptote - ambient, 1.0)
        assert abs(T - T_analytic) < 0.02 * rise


def test_one_lump_cooldown_decays_exponentially() -> None:
    R = 1.5
    C = 50.0
    ambient = 25.0
    initial_node = 80.0
    duration = 5.0 * R * C
    model = one_lump_model(
        capacitance=C,
        resistance=R,
        power=0.0,
        duration=duration,
        ambient=ambient,
        initial=ambient,
        initial_temperature_c_node=initial_node,
        time_step_s=R * C / 100.0,
    )
    result = simulate_transient_thermal_model(model)
    times = result["series"]["time_s"]
    temps = result["series"]["node_temperatures_c"]["lump"]
    for t, T in zip(times, temps):
        T_analytic = ambient + (initial_node - ambient) * math.exp(-t / (R * C))
        assert abs(T - T_analytic) < 0.02 * (initial_node - ambient)


# --------------------------------------------------------------------------- #
# Energy balance                                                              #
# --------------------------------------------------------------------------- #


def test_energy_balance_sanity() -> None:
    """Integrated heat in - integrated heat rejected = stored energy change."""
    R = 1.0
    C = 200.0
    Q = 20.0
    ambient = 25.0
    duration = 3.0 * R * C
    model = one_lump_model(
        capacitance=C, resistance=R, power=Q, duration=duration, ambient=ambient,
        time_step_s=R * C / 200.0,
    )
    result = simulate_transient_thermal_model(model)
    times = result["series"]["time_s"]
    powers = result["series"]["power_w"]
    temps = result["series"]["node_temperatures_c"]["lump"]
    assert len(times) == len(powers) == len(temps)

    # Trapezoidal integration of heat in and heat rejected.
    heat_in = 0.0
    heat_out = 0.0
    for i in range(1, len(times)):
        dt = times[i] - times[i - 1]
        heat_in += 0.5 * (powers[i] + powers[i - 1]) * dt
        rej_prev = (temps[i - 1] - ambient) / R
        rej_curr = (temps[i] - ambient) / R
        heat_out += 0.5 * (rej_prev + rej_curr) * dt
    stored = C * (temps[-1] - temps[0])
    # Net energy in should match stored energy increase within ~3% (implicit
    # Euler bias plus trapezoidal post-hoc integration error).
    residual = (heat_in - heat_out) - stored
    assert abs(residual) < 0.03 * heat_in


# --------------------------------------------------------------------------- #
# Two-node limiting behavior                                                  #
# --------------------------------------------------------------------------- #


def two_node_model(
    *,
    C1: float, C2: float, R12: float, R2a: float,
    Q: float, duration: float, ambient: float = 25.0,
) -> dict:
    return {
        "time": {"duration_s": duration, "initial_temperature_c": ambient},
        "profile": {"type": "step", "power_w": Q},
        "network": {
            "nodes": [
                {"id": "src", "label": "Source", "kind": "dynamic", "capacitance_j_per_k": C1},
                {"id": "sink", "label": "Sink", "kind": "dynamic", "capacitance_j_per_k": C2},
                {"id": "amb", "label": "Ambient", "kind": "boundary", "fixed_temperature_c": ambient},
            ],
            "segments": [
                {"id": "r12", "label": "src->sink", "from_node_id": "src", "to_node_id": "sink", "resistance_k_per_w": R12},
                {"id": "r2a", "label": "sink->amb", "from_node_id": "sink", "to_node_id": "amb", "resistance_k_per_w": R2a},
            ],
            "heat_inputs": [{"node_id": "src", "profile_role": "primary"}],
        },
    }


def test_two_node_low_internal_R_approaches_combined_lump() -> None:
    """When R12 << R2a, source and sink track each other; behavior approaches a single lump
    of C = C1 + C2 in series with R2a."""
    Q = 15.0
    R2a = 2.0
    C1, C2 = 30.0, 200.0
    duration = 3.0 * R2a * (C1 + C2)
    fast = two_node_model(C1=C1, C2=C2, R12=0.001, R2a=R2a, Q=Q, duration=duration)
    result = simulate_transient_thermal_model(fast)
    src = result["series"]["node_temperatures_c"]["src"]
    sink = result["series"]["node_temperatures_c"]["sink"]
    # Source and sink should be within 2 K of each other after the first step.
    assert all(abs(s - k) < 2.0 for s, k in zip(src[5:], sink[5:]))


def test_two_node_high_internal_R_delays_sink_response() -> None:
    """When R12 is large, the sink lags far behind the source."""
    Q = 15.0
    C1, C2 = 30.0, 200.0
    duration = 200.0
    slow = two_node_model(C1=C1, C2=C2, R12=10.0, R2a=2.0, Q=Q, duration=duration)
    result = simulate_transient_thermal_model(slow)
    src = result["series"]["node_temperatures_c"]["src"]
    sink = result["series"]["node_temperatures_c"]["sink"]
    # Source is much hotter than sink throughout the transient.
    midpoint = len(src) // 2
    assert src[midpoint] - sink[midpoint] > 5.0


# --------------------------------------------------------------------------- #
# Time-to-limit interpolation                                                 #
# --------------------------------------------------------------------------- #


def test_time_to_limit_interpolated_between_steps() -> None:
    R = 1.0
    C = 100.0
    Q = 50.0
    ambient = 25.0
    limit = 50.0
    # Analytical time to reach `limit`:
    # T(t) = T_amb + Q*R*(1-exp(-t/RC))  =>  t = -RC * ln(1 - (limit - T_amb)/(Q*R))
    expected = -R * C * math.log(1.0 - (limit - ambient) / (Q * R))
    model = one_lump_model(
        capacitance=C,
        resistance=R,
        power=Q,
        duration=3.0 * R * C,
        ambient=ambient,
        max_temperature_c=limit,
        time_step_s=R * C / 50.0,
    )
    result = simulate_transient_thermal_model(model)
    assert result["summary"]["time_to_limit_s"] is not None
    assert abs(result["summary"]["time_to_limit_s"] - expected) < 0.05 * expected


# --------------------------------------------------------------------------- #
# Duty cycle and cyclic steady state                                          #
# --------------------------------------------------------------------------- #


def test_duty_cycle_reaches_cyclic_steady_state() -> None:
    R = 0.5
    C = 50.0
    on_power = 60.0
    cycle = 5.0  # short relative to RC=25 -> still walks up; need many cycles
    model = one_lump_model(
        capacitance=C,
        resistance=R,
        power=0.0,  # ignored for duty
        duration=200.0,
        ambient=25.0,
        profile_type="duty_cycle",
        profile_extras={
            "on_power_w": on_power,
            "on_time_s": 2.0,
            "off_power_w": 0.0,
            "off_time_s": 3.0,
        },
        time_step_s=cycle / 50.0,
    )
    result = simulate_transient_thermal_model(model)
    assert result["summary"]["cyclic_steady_state_reached"] is True
    assert len(result["cycle_summary"]) > 5
    last = result["cycle_summary"][-1]
    prev = result["cycle_summary"][-2]
    assert abs(last["peak_c"] - prev["peak_c"]) < 0.1


def test_duty_cycle_overload_hits_limit() -> None:
    """A heavy duty cycle whose mean-power asymptote exceeds the limit must
    trigger a time-to-limit and an unacceptable status."""
    R = 1.0
    C = 50.0
    # Mean power = 60 W, asymptote = 25 + 60*1 = 85 C >> 80 C limit.
    model = one_lump_model(
        capacitance=C,
        resistance=R,
        power=0.0,
        duration=200.0,
        ambient=25.0,
        max_temperature_c=80.0,
        profile_type="duty_cycle",
        profile_extras={
            "on_power_w": 120.0,
            "on_time_s": 5.0,
            "off_power_w": 0.0,
            "off_time_s": 5.0,
        },
        time_step_s=0.1,
    )
    result = simulate_transient_thermal_model(model)
    assert result["summary"]["time_to_limit_s"] is not None
    assert result["status"] in {"unacceptable", "marginal"}


# --------------------------------------------------------------------------- #
# Validation                                                                  #
# --------------------------------------------------------------------------- #


def test_validation_rejects_disconnected_node() -> None:
    model = one_lump_model(capacitance=10.0, resistance=1.0, power=5.0, duration=10.0)
    model["network"]["nodes"].append(
        {"id": "floating", "label": "Floating", "kind": "dynamic", "capacitance_j_per_k": 5.0}
    )
    validation = validate_transient_thermal_model(model)
    assert not validation["is_valid"]
    assert any("not connected" in err for err in validation["errors"])


def test_validation_rejects_negative_capacitance() -> None:
    model = one_lump_model(capacitance=-5.0, resistance=1.0, power=5.0, duration=10.0)
    validation = validate_transient_thermal_model(model)
    assert not validation["is_valid"]
    assert any("capacitance" in err for err in validation["errors"])


def test_validation_rejects_zero_resistance() -> None:
    model = one_lump_model(capacitance=10.0, resistance=0.0, power=5.0, duration=10.0)
    validation = validate_transient_thermal_model(model)
    assert not validation["is_valid"]
    assert any("resistance" in err for err in validation["errors"])


def test_steady_state_asymptote_flags_unacceptable_even_when_window_too_short() -> None:
    """If the simulation window stops before reaching the limit but the
    steady-state asymptote crosses it, the status must still be unacceptable.

    Step profiles auto-extend to ~5*tau_slow so they would normally reach the
    asymptote on their own; the asymptote-only check is what catches duty
    cycles whose walk-up is slower than the user's chosen window.
    """
    R = 1.0
    C = 1000.0  # tau_slow = 1000 s — far longer than the 20 s window below
    ambient = 25.0
    limit = 80.0
    # Mean power = 60 W; asymptote = ambient + 60*1 = 85 °C, above the limit.
    model = one_lump_model(
        capacitance=C,
        resistance=R,
        power=0.0,
        duration=20.0,
        ambient=ambient,
        max_temperature_c=limit,
        profile_type="duty_cycle",
        profile_extras={
            "on_power_w": 120.0, "on_time_s": 5.0,
            "off_power_w": 0.0, "off_time_s": 5.0,
        },
        time_step_s=0.5,
    )
    result = simulate_transient_thermal_model(model)
    assert result["summary"]["peak_temperature_c"] < limit
    assert result["summary"]["steady_state_temperature_c"] == pytest.approx(85.0, rel=1e-3)
    assert result["status"] == "unacceptable"


def test_auto_extends_step_duration_to_capture_asymptote() -> None:
    """Step profiles with too-short user duration should auto-extend to ~5*tau_slow
    so the temperature plot reaches the asymptote and the user can see whether
    the design ultimately exceeds its limit."""
    R = 2.0
    C = 100.0
    Q = 50.0
    # Slowest tau = R*C = 200 s.  User asks for 50 s — way too short.
    model = one_lump_model(
        capacitance=C,
        resistance=R,
        power=Q,
        duration=50.0,
        ambient=25.0,
        max_temperature_c=110.0,
    )
    result = simulate_transient_thermal_model(model)
    assert result["summary"]["requested_duration_s"] == pytest.approx(50.0)
    # Simulated window should be ~5 * tau_slow = 1000 s.
    assert result["summary"]["simulated_duration_s"] >= 5.0 * R * C * 0.95
    assert result["summary"]["auto_extended_duration"] is True
    # The warning surfaces the change so users know their input was overridden.
    assert any("extended" in w.lower() for w in result["warnings"])


def test_no_auto_extension_when_user_duration_already_long() -> None:
    """If the user picks a duration well past the slow time constant, leave it alone."""
    R = 1.0
    C = 50.0
    model = one_lump_model(
        capacitance=C, resistance=R, power=10.0, duration=10.0 * R * C, ambient=25.0,
    )
    result = simulate_transient_thermal_model(model)
    assert result["summary"]["auto_extended_duration"] is False
    assert result["summary"]["simulated_duration_s"] == pytest.approx(10.0 * R * C)


def test_pulse_duration_not_auto_extended() -> None:
    """Pulse profiles have a meaningful user-specified window; never override it."""
    R = 5.0
    C = 100.0
    # Slowest tau = 500 s.  Run the pulse for 30 s, cool for 60 s — total 90 s.
    model = one_lump_model(
        capacitance=C,
        resistance=R,
        power=0.0,
        duration=90.0,
        ambient=25.0,
        profile_type="pulse",
        profile_extras={"pulse_power_w": 100.0, "pulse_duration_s": 30.0, "cooldown_power_w": 0.0},
    )
    result = simulate_transient_thermal_model(model)
    assert result["summary"]["auto_extended_duration"] is False


def test_slowest_mode_tau_matches_two_node_eigenvalue() -> None:
    """For a 2-node ladder, the reported slow mode τ must match the analytical
    smallest eigenvalue of A = C^{-1} G."""
    C1, C2 = 12.0, 310.0
    R12, R2a = 0.5, 1.5
    model = two_node_model(C1=C1, C2=C2, R12=R12, R2a=R2a, Q=10.0, duration=1000.0)
    result = simulate_transient_thermal_model(model)
    # Analytical: A = C^{-1} G with G = [[1/R12, -1/R12], [-1/R12, 1/R12 + 1/R2a]]
    g11, g22 = 1 / R12, 1 / R12 + 1 / R2a
    g12 = -1 / R12
    a11, a22 = g11 / C1, g22 / C2
    a12, a21 = g12 / C1, g12 / C2
    trace = a11 + a22
    det = a11 * a22 - a12 * a21
    lam_min = 0.5 * (trace - math.sqrt(trace * trace - 4 * det))
    expected_tau = 1.0 / lam_min
    reported = result["summary"]["slowest_mode_tau_s"]
    assert abs(reported - expected_tau) / expected_tau < 0.01


def test_invalid_model_returns_invalid_status_not_exception() -> None:
    bad = {"time": {}, "profile": {}, "network": {"nodes": [], "segments": [], "heat_inputs": []}}
    result = simulate_transient_thermal_model(bad)
    assert result["status"] == "invalid"
    assert result["errors"]


# --------------------------------------------------------------------------- #
# Plate-fin bridge                                                            #
# --------------------------------------------------------------------------- #


# Reference plate-fin geometry used across the bridge tests — a typical
# extruded aluminum sink, vertical, natural convection.
_PLATE_FIN_GEOMETRY = dict(
    base_length=0.10,
    base_width=0.10,
    base_thickness=0.006,
    fin_height=0.025,
    fin_thickness=0.0015,
    fin_count=12,
    material_conductivity=201.0,
    surface_emissivity=0.85,
    airflow_mode="natural",
)


def test_plate_fin_bridge_R_sa_matches_direct_solver_call() -> None:
    """The bridge must report exactly the R_sa that analyze_plate_fin_heatsink
    returns for the same geometry — otherwise transient simulations would
    silently disagree with the steady-state tool for the same hardware."""
    direct = heatsinks.analyze_plate_fin_heatsink(
        heat_load=30.0,
        ambient_temperature=25.0,
        target_junction_temperature=125.0,
        **_PLATE_FIN_GEOMETRY,
    )
    bridged = compute_plate_fin_sink_properties(
        reference_heat_load_w=30.0,
        ambient_temperature_c=25.0,
        **_PLATE_FIN_GEOMETRY,
    )
    assert math.isclose(
        bridged["sink_thermal_resistance_k_per_w"],
        direct["sink_thermal_resistance"],
        rel_tol=1e-9,
    )


def test_plate_fin_bridge_C_sink_equals_rho_V_cp() -> None:
    """C_sink = rho * V * cp using the geometry's solid volume and the
    selected sink material preset."""
    geom = heatsinks.calculate_plate_fin_geometry(
        base_length=_PLATE_FIN_GEOMETRY["base_length"],
        base_width=_PLATE_FIN_GEOMETRY["base_width"],
        base_thickness=_PLATE_FIN_GEOMETRY["base_thickness"],
        fin_height=_PLATE_FIN_GEOMETRY["fin_height"],
        fin_thickness=_PLATE_FIN_GEOMETRY["fin_thickness"],
        fin_count=_PLATE_FIN_GEOMETRY["fin_count"],
    )
    bridged = compute_plate_fin_sink_properties(
        reference_heat_load_w=30.0,
        ambient_temperature_c=25.0,
        sink_material_id="aluminum_6063",
        **_PLATE_FIN_GEOMETRY,
    )
    expected_C = 2700.0 * geom.volume * 900.0
    assert bridged["sink_volume_m3"] == pytest.approx(geom.volume, rel=1e-9)
    assert bridged["sink_capacitance_j_per_k"] == pytest.approx(expected_C, rel=1e-9)


def test_plate_fin_bridge_material_override() -> None:
    """Explicit density/cp must override the preset, and a non-preset material
    must work when both overrides are supplied."""
    bridged = compute_plate_fin_sink_properties(
        reference_heat_load_w=30.0,
        ambient_temperature_c=25.0,
        sink_material_id=None,
        sink_density_kg_per_m3=8000.0,
        sink_heat_capacity_j_per_kgk=500.0,
        **_PLATE_FIN_GEOMETRY,
    )
    assert bridged["sink_density_kg_per_m3"] == 8000.0
    assert bridged["sink_heat_capacity_j_per_kgk"] == 500.0


def test_plate_fin_bridge_warns_when_fin_efficiency_low() -> None:
    """Tall, thin steel fins push fin efficiency well below the warning
    threshold; the bridge must surface that to the caller."""
    inputs = dict(_PLATE_FIN_GEOMETRY)
    inputs.update(
        material_conductivity=15.0,  # steel
        fin_height=0.080,             # very tall
        fin_thickness=0.0008,         # very thin
    )
    bridged = compute_plate_fin_sink_properties(
        reference_heat_load_w=30.0, ambient_temperature_c=25.0, **inputs,
    )
    assert any("fin efficiency" in w.lower() for w in bridged["warnings"])


def test_build_plate_fin_transient_model_simulates_cleanly() -> None:
    """End-to-end: bridge → simulate. The assembled model must validate and
    produce a finite peak temperature."""
    bundle = build_plate_fin_transient_model(
        **_PLATE_FIN_GEOMETRY,
        junction_to_case_resistance_k_per_w=0.5,
        interface_resistance_k_per_w=0.05,
        source_capacitance_j_per_k=12.0,
        max_source_temperature_c=110.0,
        profile={"type": "step", "power_w": 30.0},
        duration_s=600.0,
        initial_temperature_c=25.0,
        ambient_temperature_c=25.0,
    )
    result = simulate_transient_thermal_model(bundle["model"])
    assert result["status"] in {"acceptable", "marginal", "unacceptable"}
    assert math.isfinite(result["summary"]["peak_temperature_c"])
    # Sanity: the source-to-sink segment combines junction-to-case + interface.
    r_jc_seg = next(s for s in bundle["model"]["network"]["segments"] if s["id"] == "r_jc")
    assert r_jc_seg["resistance_k_per_w"] == pytest.approx(0.55)
    # Sanity: the sink resistance in the model matches the bridge's reported R_sa.
    r_sa_seg = next(s for s in bundle["model"]["network"]["segments"] if s["id"] == "r_sa")
    assert r_sa_seg["resistance_k_per_w"] == pytest.approx(
        bundle["sink"]["sink_thermal_resistance_k_per_w"], rel=1e-9
    )


def test_build_plate_fin_transient_model_uses_mean_power_for_duty() -> None:
    """For a 50% duty cycle, the plate-fin reference operating point should be
    the mean power, not the on-power. R_sa drifts only weakly with temperature,
    but the bridge contract is to use the steady-state-equivalent load."""
    bundle = build_plate_fin_transient_model(
        **_PLATE_FIN_GEOMETRY,
        junction_to_case_resistance_k_per_w=0.5,
        source_capacitance_j_per_k=12.0,
        max_source_temperature_c=110.0,
        profile={
            "type": "duty_cycle",
            "on_power_w": 60.0, "on_time_s": 30.0,
            "off_power_w": 0.0, "off_time_s": 30.0,
        },
        duration_s=600.0,
        initial_temperature_c=25.0,
        ambient_temperature_c=25.0,
    )
    assert bundle["reference_heat_load_w"] == pytest.approx(30.0)


def test_build_plate_fin_transient_model_zero_jc_uses_resistance_floor() -> None:
    """If both junction-to-case and interface resistance are zero, the
    validator would reject a zero-resistance segment. The bridge inserts a
    tiny floor so the simulation still runs (physically: source lumped with
    sink)."""
    bundle = build_plate_fin_transient_model(
        **_PLATE_FIN_GEOMETRY,
        junction_to_case_resistance_k_per_w=0.0,
        interface_resistance_k_per_w=0.0,
        source_capacitance_j_per_k=12.0,
        profile={"type": "step", "power_w": 30.0},
        duration_s=200.0,
        initial_temperature_c=25.0,
        ambient_temperature_c=25.0,
    )
    r_jc_seg = next(s for s in bundle["model"]["network"]["segments"] if s["id"] == "r_jc")
    assert 0.0 < r_jc_seg["resistance_k_per_w"] < 1e-3
    result = simulate_transient_thermal_model(bundle["model"])
    assert result["status"] != "invalid"


# --------------------------------------------------------------------------- #
# Sensitivity sweeps and design-lever recommendation                          #
# --------------------------------------------------------------------------- #


def package_on_heatsink_model(
    *,
    R_jc: float = 0.5, R_sa: float = 1.5,
    C_source: float = 12.0, C_sink: float = 310.0,
    profile: dict | None = None,
    duration: float = 600.0,
    ambient: float = 25.0, initial: float = 25.0,
    max_temperature_c: float | None = 110.0,
) -> dict:
    """Canonical 3-node Package-On-Heatsink model with the same ids the bridge
    function and UI build, so it's compatible with SENSITIVITY_PARAMETERS."""
    return {
        "time": {"duration_s": duration, "initial_temperature_c": initial},
        "profile": profile or {"type": "step", "power_w": 30.0},
        "network": {
            "nodes": [
                {"id": "source", "label": "Source", "kind": "dynamic",
                 "capacitance_j_per_k": C_source, "max_temperature_c": max_temperature_c},
                {"id": "sink", "label": "Sink", "kind": "dynamic",
                 "capacitance_j_per_k": C_sink},
                {"id": "ambient", "label": "Ambient", "kind": "boundary",
                 "fixed_temperature_c": ambient},
            ],
            "segments": [
                {"id": "r_jc", "label": "Source->Sink", "from_node_id": "source",
                 "to_node_id": "sink", "resistance_k_per_w": R_jc},
                {"id": "r_sa", "label": "Sink->Ambient", "from_node_id": "sink",
                 "to_node_id": "ambient", "resistance_k_per_w": R_sa},
            ],
            "heat_inputs": [{"node_id": "source", "profile_role": "primary"}],
        },
    }


def test_sensitivity_sweep_r_sa_is_monotonic() -> None:
    """Higher R_sa → higher peak temperature for a step load. The relationship
    must be strictly monotonic; if it isn't, something is wrong with the
    deep-copy-and-mutate logic."""
    sweep = generate_transient_sensitivity(
        package_on_heatsink_model(),
        "r_sa",
        fractions=[0.5, 1.0, 1.5, 2.0],
    )
    peaks = sweep["peak_temperature_c"]
    assert all(p is not None for p in peaks)
    assert all(peaks[i] < peaks[i + 1] for i in range(len(peaks) - 1))
    # Baseline must be present in the result regardless of the fractions list.
    assert 1.0 in sweep["fractions"]
    assert sweep["baseline_value"] == pytest.approx(1.5)


def test_sensitivity_sweep_does_not_mutate_input() -> None:
    """The input model must be left untouched after a sweep — otherwise
    successive calls would compound."""
    model = package_on_heatsink_model(R_sa=1.5)
    generate_transient_sensitivity(model, "r_sa", fractions=[0.5, 2.0])
    r_sa_seg = next(s for s in model["network"]["segments"] if s["id"] == "r_sa")
    assert r_sa_seg["resistance_k_per_w"] == 1.5


def test_sensitivity_c_sink_changes_time_to_limit_not_steady_state() -> None:
    """Adding heatsink mass slows the rise but cannot change the steady-state
    temperature (asymptote depends only on R_sa, R_jc, ambient, power)."""
    model = package_on_heatsink_model(
        R_jc=0.3, R_sa=2.0,
        profile={"type": "step", "power_w": 50.0},
        duration=2000.0,
    )
    sweep = generate_transient_sensitivity(model, "c_sink", fractions=[0.5, 1.0, 2.0, 4.0])
    steady = sweep["steady_state_temperature_c"]
    assert all(s is not None for s in steady)
    # All four steady-state temperatures should match within numerical noise.
    assert max(steady) - min(steady) < 0.05


def test_sensitivity_unknown_parameter_raises() -> None:
    with pytest.raises(ValueError, match="Unknown sensitivity parameter"):
        generate_transient_sensitivity(package_on_heatsink_model(), "not_a_param")


def test_sensitivity_inapplicable_parameter_returns_error_not_exception() -> None:
    """Sweeping on_time on a step-profile model must return an error in the
    result — not raise — so the UI can surface it next to the dropdown."""
    sweep = generate_transient_sensitivity(package_on_heatsink_model(), "on_time")
    assert sweep["baseline_value"] is None
    assert any("duty_cycle" in e["message"] for e in sweep["errors"])


def test_sensitivity_local_slope_sign_matches_physics() -> None:
    """For a duty cycle, raising R_sa raises peak T → slope > 0.
    Raising C_sink smooths cyclic peaks → slope < 0.
    Duty cycles are used here because step profiles auto-extend the
    simulation window to ~5*tau_slow, which masks the C_sink effect."""
    model = package_on_heatsink_model(
        profile={
            "type": "duty_cycle",
            "on_power_w": 80.0, "on_time_s": 30.0,
            "off_power_w": 0.0, "off_time_s": 30.0,
        },
        duration=300.0,
    )
    r_sweep = generate_transient_sensitivity(model, "r_sa", fractions=[1.0, 1.1])
    c_sweep = generate_transient_sensitivity(model, "c_sink", fractions=[1.0, 1.1])
    assert r_sweep["local_peak_slope"] is not None and r_sweep["local_peak_slope"] > 0
    assert c_sweep["local_peak_slope"] is not None and c_sweep["local_peak_slope"] < 0


def test_design_lever_recommendation_resistance_dominated() -> None:
    """When R_sa is the bottleneck (large R, small mass already saturating),
    halving R_sa should win over doubling C_sink."""
    # Step load on a heavy sink: doubling sink mass barely changes the steady-state
    # peak because the system is near its asymptote, but halving R_sa cuts the
    # asymptote almost in half.
    model = package_on_heatsink_model(
        R_jc=0.1, R_sa=3.0, C_source=5.0, C_sink=200.0,
        profile={"type": "step", "power_w": 30.0},
        duration=4000.0,  # long enough to approach steady state
    )
    rec = compute_design_lever_recommendation(model)
    assert rec["recommendation"] == "improve_resistance"
    assert rec["delta_peak_half_r_sa_c"] > rec["delta_peak_double_c_sink_c"]
    assert "R_sa" in rec["message"]


def test_design_lever_recommendation_capacitance_dominated_pulse() -> None:
    """A pulse long enough for energy to reach the sink, but short enough
    that the system is still far from the R_sa-determined asymptote.  In
    that regime the lumped capacitance dominates the peak, so doubling
    C_sink wins over halving R_sa."""
    # 60-second pulse, R_sa*C_sink = 450 s (long compared to pulse).  The
    # sink barely cools during the pulse, so peak rise ≈ Q*t / (C_source +
    # C_sink) — doubling C_sink ≈ halves the rise; halving R_sa hardly
    # matters in 60 s.
    model = package_on_heatsink_model(
        R_jc=0.05, R_sa=1.5, C_source=10.0, C_sink=300.0,
        profile={
            "type": "pulse", "pulse_power_w": 100.0,
            "pulse_duration_s": 60.0, "cooldown_power_w": 0.0,
        },
        duration=600.0,
    )
    rec = compute_design_lever_recommendation(model)
    assert rec["recommendation"] in {"add_mass", "comparable"}
    assert rec["delta_peak_double_c_sink_c"] is not None
    assert rec["delta_peak_double_c_sink_c"] >= rec["delta_peak_half_r_sa_c"]


def test_design_lever_recommendation_handles_missing_segments() -> None:
    """A single-lump model has no R_sa or C_sink segment with the canonical
    ids; the helper must return insufficient_data, not raise."""
    model = one_lump_model(capacitance=200.0, resistance=2.0, power=30.0, duration=300.0)
    rec = compute_design_lever_recommendation(model)
    assert rec["recommendation"] == "insufficient_data"


def test_cycle_summary_includes_walk_up() -> None:
    """Each cycle (after the first) reports its peak rise relative to the
    prior cycle, so the UI can show whether duty-cycle peaks are drifting."""
    model = package_on_heatsink_model(
        profile={
            "type": "duty_cycle",
            "on_power_w": 80.0, "on_time_s": 30.0,
            "off_power_w": 0.0, "off_time_s": 30.0,
        },
        duration=300.0,
    )
    result = simulate_transient_thermal_model(model)
    cycles = result["cycle_summary"]
    assert len(cycles) >= 3
    assert cycles[0]["walk_up_c"] is None
    # The system is climbing toward steady state, so early cycles must walk up
    # and the magnitude must shrink as we approach convergence.
    assert cycles[1]["walk_up_c"] > 0
    assert cycles[1]["walk_up_c"] >= cycles[-1]["walk_up_c"]
