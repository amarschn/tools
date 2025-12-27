import pytest

from pycalcs import acoustics


def _base_inputs():
    return {
        "conversion_mode": "swl_to_spl",
        "source_type": "point",
        "known_level_db": 100.0,
        "distance_m": 10.0,
        "directivity_q": 1.0,
        "distance_min_m": 1.0,
        "distance_max_m": 100.0,
        "combine_levels_db": "",
        "band_weighting": "Z",
        "band_63_db": 60.0,
        "band_125_db": 60.0,
        "band_250_db": 60.0,
        "band_500_db": 60.0,
        "band_1000_db": 60.0,
        "band_2000_db": 60.0,
        "band_4000_db": 60.0,
        "band_8000_db": 60.0,
    }


def test_swl_to_spl_point_source():
    result = acoustics.calculate_sound_levels(**_base_inputs())

    assert result["divergence_loss_db"] == pytest.approx(31.0, abs=0.1)
    assert result["spl_db"] == pytest.approx(69.0, abs=0.1)


def test_spl_to_swl_inverse():
    inputs = _base_inputs()
    inputs["conversion_mode"] = "spl_to_swl"
    inputs["known_level_db"] = 69.0
    result = acoustics.calculate_sound_levels(**inputs)

    assert result["swl_db"] == pytest.approx(100.0, abs=0.2)


def test_combined_levels_addition():
    inputs = _base_inputs()
    inputs["combine_levels_db"] = "70, 70"
    result = acoustics.calculate_sound_levels(**inputs)

    assert result["combine_count"] == 2
    assert result["combined_level_db"] == pytest.approx(73.01, abs=0.05)


def test_octave_weighting_adjusts_levels():
    inputs = _base_inputs()
    inputs["band_weighting"] = "A"
    result = acoustics.calculate_sound_levels(**inputs)

    assert result["octave_weighted_db"] < result["octave_overall_db"]


def test_invalid_distance_raises():
    inputs = _base_inputs()
    inputs["distance_m"] = 0
    with pytest.raises(ValueError):
        acoustics.calculate_sound_levels(**inputs)
