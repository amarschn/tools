"""Tests for pycalcs/fluids.py – Reynolds number calculations."""

import pytest

from pycalcs.fluids import (
    compute_reynolds_number,
    classify_reynolds_regime,
    reynolds_number_analysis,
)


# ─────────────────────────────────────────────────────────────────────────────
# compute_reynolds_number – basic functionality
# ─────────────────────────────────────────────────────────────────────────────


def test_reynolds_with_kinematic_viscosity():
    """Re = V*L/nu, basic check with water at 20C (nu ≈ 1e-6 m^2/s)."""
    # V=1 m/s, L=0.1 m, nu=1e-6 → Re = 100,000
    re = compute_reynolds_number(
        velocity=1.0,
        characteristic_length=0.1,
        kinematic_viscosity=1e-6,
    )
    assert re == pytest.approx(1e5, rel=1e-9)


def test_reynolds_with_dynamic_viscosity():
    """Re = rho*V*L/mu, using water properties."""
    # rho=1000 kg/m^3, V=1 m/s, L=0.1 m, mu=1e-3 Pa·s → Re = 100,000
    re = compute_reynolds_number(
        velocity=1.0,
        characteristic_length=0.1,
        density=1000.0,
        dynamic_viscosity=1e-3,
    )
    assert re == pytest.approx(1e5, rel=1e-9)


def test_reynolds_air_properties():
    """Check with typical air at 20C (rho=1.2 kg/m^3, mu=1.8e-5 Pa·s)."""
    # V=10 m/s, L=1 m → Re = 1.2 * 10 * 1 / 1.8e-5 = 666,667
    re = compute_reynolds_number(
        velocity=10.0,
        characteristic_length=1.0,
        density=1.2,
        dynamic_viscosity=1.8e-5,
    )
    assert re == pytest.approx(666666.67, rel=1e-3)


def test_reynolds_laminar_pipe_flow():
    """Laminar pipe flow example: V=0.01 m/s, D=0.01 m, nu=1e-6 → Re=100."""
    re = compute_reynolds_number(
        velocity=0.01,
        characteristic_length=0.01,
        kinematic_viscosity=1e-6,
    )
    assert re == pytest.approx(100, rel=1e-9)


def test_reynolds_turbulent_pipe_flow():
    """Turbulent pipe flow: V=5 m/s, D=0.05 m, nu=1e-6 → Re=250,000."""
    re = compute_reynolds_number(
        velocity=5.0,
        characteristic_length=0.05,
        kinematic_viscosity=1e-6,
    )
    assert re == pytest.approx(250000, rel=1e-9)


# ─────────────────────────────────────────────────────────────────────────────
# compute_reynolds_number – validation errors
# ─────────────────────────────────────────────────────────────────────────────


def test_reynolds_zero_velocity_raises():
    """Velocity must be positive."""
    with pytest.raises(ValueError, match="[Vv]elocity.*greater than zero"):
        compute_reynolds_number(
            velocity=0.0,
            characteristic_length=0.1,
            kinematic_viscosity=1e-6,
        )


def test_reynolds_negative_velocity_raises():
    """Negative velocity is rejected."""
    with pytest.raises(ValueError, match="[Vv]elocity.*greater than zero"):
        compute_reynolds_number(
            velocity=-1.0,
            characteristic_length=0.1,
            kinematic_viscosity=1e-6,
        )


def test_reynolds_zero_length_raises():
    """Characteristic length must be positive."""
    with pytest.raises(ValueError, match="[Ll]ength.*greater than zero"):
        compute_reynolds_number(
            velocity=1.0,
            characteristic_length=0.0,
            kinematic_viscosity=1e-6,
        )


def test_reynolds_negative_length_raises():
    """Negative length is rejected."""
    with pytest.raises(ValueError, match="[Ll]ength.*greater than zero"):
        compute_reynolds_number(
            velocity=1.0,
            characteristic_length=-0.1,
            kinematic_viscosity=1e-6,
        )


def test_reynolds_zero_kinematic_viscosity_raises():
    """Kinematic viscosity must be positive."""
    with pytest.raises(ValueError, match="[Kk]inematic viscosity.*greater than zero"):
        compute_reynolds_number(
            velocity=1.0,
            characteristic_length=0.1,
            kinematic_viscosity=0.0,
        )


def test_reynolds_negative_kinematic_viscosity_raises():
    """Negative kinematic viscosity is rejected."""
    with pytest.raises(ValueError, match="[Kk]inematic viscosity.*greater than zero"):
        compute_reynolds_number(
            velocity=1.0,
            characteristic_length=0.1,
            kinematic_viscosity=-1e-6,
        )


def test_reynolds_zero_density_raises():
    """Density must be positive."""
    with pytest.raises(ValueError, match="[Dd]ensity.*greater than zero"):
        compute_reynolds_number(
            velocity=1.0,
            characteristic_length=0.1,
            density=0.0,
            dynamic_viscosity=1e-3,
        )


def test_reynolds_zero_dynamic_viscosity_raises():
    """Dynamic viscosity must be positive."""
    with pytest.raises(ValueError, match="[Dd]ynamic viscosity.*greater than zero"):
        compute_reynolds_number(
            velocity=1.0,
            characteristic_length=0.1,
            density=1000.0,
            dynamic_viscosity=0.0,
        )


def test_reynolds_both_viscosity_types_raises():
    """Cannot supply both kinematic and dynamic viscosity."""
    with pytest.raises(ValueError, match="[Ss]upply either"):
        compute_reynolds_number(
            velocity=1.0,
            characteristic_length=0.1,
            kinematic_viscosity=1e-6,
            density=1000.0,
            dynamic_viscosity=1e-3,
        )


def test_reynolds_neither_viscosity_raises():
    """Must supply at least one viscosity approach."""
    with pytest.raises(ValueError, match="[Ss]upply either"):
        compute_reynolds_number(
            velocity=1.0,
            characteristic_length=0.1,
        )


def test_reynolds_only_density_raises():
    """Density without dynamic viscosity should fail."""
    with pytest.raises(ValueError, match="[Ss]upply either"):
        compute_reynolds_number(
            velocity=1.0,
            characteristic_length=0.1,
            density=1000.0,
        )


def test_reynolds_only_dynamic_viscosity_raises():
    """Dynamic viscosity without density should fail."""
    with pytest.raises(ValueError, match="[Ss]upply either"):
        compute_reynolds_number(
            velocity=1.0,
            characteristic_length=0.1,
            dynamic_viscosity=1e-3,
        )


# ─────────────────────────────────────────────────────────────────────────────
# classify_reynolds_regime
# ─────────────────────────────────────────────────────────────────────────────


def test_regime_laminar_low():
    """Re=100 is clearly laminar."""
    assert classify_reynolds_regime(100) == "laminar"


def test_regime_laminar_boundary():
    """Re=2299 is still laminar (just below threshold)."""
    assert classify_reynolds_regime(2299) == "laminar"


def test_regime_transitional_lower_bound():
    """Re=2300 is the start of transitional."""
    assert classify_reynolds_regime(2300) == "transitional"


def test_regime_transitional_mid():
    """Re=3000 is transitional."""
    assert classify_reynolds_regime(3000) == "transitional"


def test_regime_transitional_upper_bound():
    """Re=4000 is still transitional."""
    assert classify_reynolds_regime(4000) == "transitional"


def test_regime_turbulent_start():
    """Re=4001 is turbulent."""
    assert classify_reynolds_regime(4001) == "turbulent"


def test_regime_turbulent_high():
    """Re=1,000,000 is turbulent."""
    assert classify_reynolds_regime(1e6) == "turbulent"


def test_regime_zero_is_laminar():
    """Re=0 is laminar (no flow)."""
    assert classify_reynolds_regime(0) == "laminar"


def test_regime_negative_raises():
    """Negative Reynolds number should raise."""
    with pytest.raises(ValueError, match="cannot be negative"):
        classify_reynolds_regime(-1)


# ─────────────────────────────────────────────────────────────────────────────
# reynolds_number_analysis – integration tests
# ─────────────────────────────────────────────────────────────────────────────


def test_analysis_kinematic_path():
    """Full analysis using kinematic viscosity."""
    result = reynolds_number_analysis(
        velocity=1.0,
        characteristic_length=0.1,
        kinematic_viscosity=1e-6,
    )
    assert result["reynolds_number"] == pytest.approx(1e5, rel=1e-9)
    assert result["flow_regime"] == "turbulent"
    assert result["viscosity_path"] == "kinematic"
    assert "subst_reynolds_number" in result
    assert "subst_flow_regime" in result


def test_analysis_dynamic_path():
    """Full analysis using density and dynamic viscosity."""
    result = reynolds_number_analysis(
        velocity=0.01,
        characteristic_length=0.01,
        density=1000.0,
        dynamic_viscosity=1e-3,
    )
    # Re = 1000 * 0.01 * 0.01 / 1e-3 = 100
    assert result["reynolds_number"] == pytest.approx(100, rel=1e-9)
    assert result["flow_regime"] == "laminar"
    assert result["viscosity_path"] == "dynamic"


def test_analysis_transitional_regime():
    """Analysis producing transitional regime."""
    # Target Re ≈ 3000: V=0.3 m/s, L=0.01 m, nu=1e-6 → Re=3000
    result = reynolds_number_analysis(
        velocity=0.3,
        characteristic_length=0.01,
        kinematic_viscosity=1e-6,
    )
    assert result["reynolds_number"] == pytest.approx(3000, rel=1e-9)
    assert result["flow_regime"] == "transitional"


def test_analysis_returns_all_expected_keys():
    """Verify the result dict structure."""
    result = reynolds_number_analysis(
        velocity=1.0,
        characteristic_length=0.1,
        kinematic_viscosity=1e-6,
    )
    expected_keys = {
        "reynolds_number",
        "flow_regime",
        "viscosity_path",
        "subst_reynolds_number",
        "subst_flow_regime",
    }
    assert set(result.keys()) == expected_keys


def test_analysis_substitution_latex_format():
    """Check that LaTeX substitution strings are properly formatted."""
    result = reynolds_number_analysis(
        velocity=2.0,
        characteristic_length=0.05,
        kinematic_viscosity=1e-6,
    )
    # Should contain the actual values in the LaTeX string
    assert "2.0" in result["subst_reynolds_number"] or "2" in result["subst_reynolds_number"]
    assert "0.05" in result["subst_reynolds_number"]
    assert "\\mathrm{Re}" in result["subst_reynolds_number"]
