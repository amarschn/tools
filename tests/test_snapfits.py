import pytest

from pycalcs.snapfits import calculate_cantilever_snap_fit


def test_cantilever_snap_fit_nominal():
    result = calculate_cantilever_snap_fit(
        length=0.02,
        thickness=0.002,
        width=0.01,
        install_deflection=0.003,
        service_deflection=0.001,
        removal_deflection=0.003,
        modulus=2.5e9,
        allowable_strain=0.04,
        install_angle_deg=20.0,
        removal_angle_deg=30.0,
        friction_coefficient=0.2,
    )

    assert result["spring_constant"] == pytest.approx(6.25e3, rel=1e-6)
    assert result["install_tip_force"] == pytest.approx(18.75, rel=1e-6)
    assert result["install_axial_force"] == pytest.approx(11.404631, rel=1e-6)
    assert result["install_stress"] == pytest.approx(5.625e7, rel=1e-6)
    assert result["install_strain"] == pytest.approx(0.0225, rel=1e-6)
    assert result["allowable_deflection"] == pytest.approx(5.333333e-3, rel=1e-6)
    assert result["install_safety_factor"] == pytest.approx(1.777777, rel=1e-6)
    assert result["service_tip_force"] == pytest.approx(6.25, rel=1e-6)
    assert result["retention_axial_force"] == pytest.approx(5.492679, rel=1e-6)
    assert result["removal_axial_force"] == pytest.approx(16.478037, rel=1e-6)
    assert result["removal_stress"] == pytest.approx(5.625e7, rel=1e-6)
    assert result["removal_strain"] == pytest.approx(0.0225, rel=1e-6)


def test_self_locking_angle_raises():
    with pytest.raises(ValueError):
        calculate_cantilever_snap_fit(
            length=0.02,
            thickness=0.002,
            width=0.01,
            install_deflection=0.001,
            service_deflection=0.001,
            removal_deflection=0.001,
            modulus=2.5e9,
            allowable_strain=0.04,
            install_angle_deg=85.0,
            removal_angle_deg=85.0,
            friction_coefficient=0.3,
        )
