import pytest

from pycalcs.controls import tune_pid_ultimate_gain


def test_tune_pid_ultimate_gain_zn_pid():
    result = tune_pid_ultimate_gain(
        ultimate_gain=5.0,
        ultimate_period=8.0,
        tuning_rule="ziegler-nichols",
        controller_type="PID",
    )

    assert result["kp"] == pytest.approx(3.0, rel=1e-6)
    assert result["ti"] == pytest.approx(4.0, rel=1e-6)
    assert result["td"] == pytest.approx(1.0, rel=1e-6)
    assert result["ki"] == pytest.approx(0.75, rel=1e-6)
    assert result["kd"] == pytest.approx(3.0, rel=1e-6)


def test_tune_pid_ultimate_gain_tl_pi():
    result = tune_pid_ultimate_gain(
        ultimate_gain=4.0,
        ultimate_period=10.0,
        tuning_rule="tyreus-luyben",
        controller_type="PI",
    )

    assert result["kp"] == pytest.approx(1.24, rel=1e-6)
    assert result["ti"] == pytest.approx(22.0, rel=1e-6)
    assert result["td"] == pytest.approx(0.0, rel=1e-6)
    assert result["ki"] == pytest.approx(0.056363636, rel=1e-6)
    assert result["kd"] == pytest.approx(0.0, rel=1e-6)


def test_tune_pid_ultimate_gain_rejects_invalid_inputs():
    with pytest.raises(ValueError):
        tune_pid_ultimate_gain(
            ultimate_gain=-1.0,
            ultimate_period=8.0,
            tuning_rule="ziegler-nichols",
            controller_type="PID",
        )

    with pytest.raises(ValueError):
        tune_pid_ultimate_gain(
            ultimate_gain=5.0,
            ultimate_period=8.0,
            tuning_rule="unknown",
            controller_type="PID",
        )

    with pytest.raises(ValueError):
        tune_pid_ultimate_gain(
            ultimate_gain=5.0,
            ultimate_period=8.0,
            tuning_rule="ziegler-nichols",
            controller_type="P",
        )
