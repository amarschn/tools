"""Tests for the transient thermal RC simulator."""

from __future__ import annotations

import math

import pytest

from pycalcs.thermal_transient import (
    estimate_thermal_capacitance,
    generate_power_profile,
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
