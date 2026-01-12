import math

import pytest

from pycalcs import circle_basics


def test_calculate_circle_basics_nominal():
    result = circle_basics.calculate_circle_basics(10.0)

    assert result["area_mm2"] == pytest.approx(math.pi * 25.0)
    assert result["circumference_mm"] == pytest.approx(math.pi * 10.0)


def test_calculate_circle_basics_raises_on_non_positive():
    with pytest.raises(ValueError):
        circle_basics.calculate_circle_basics(0.0)
