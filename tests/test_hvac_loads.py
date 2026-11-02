"""Tests for pycalcs.hvac_loads.

The benchmarks use two published houses with fully stated inputs:

* ASHRAE Handbook Fundamentals, Chapter 17, section 9 (Atlanta, GA): the
  worked example for the Residential Load Factor method.
* Kwik Model sample report (Sacramento, CA), an EnergyGauge Manual J 8th
  edition report published by CHEERS. Its results were never used to calibrate
  the model, so it is an independent check.
"""
import math

import pytest

from pycalcs import hvac_loads as h
from pycalcs import utils


ATLANTA = {
    "floor_area_ft2": 2088, "stories": 1, "ceiling_height_ft": 8, "bedrooms": 3,
    "occupants": 4, "latitude": 33.64, "elevation_ft": 1027,
    "heating_design_f": 26, "cooling_design_f": 92, "cooling_wet_bulb_f": 74,
    "daily_range_f": 17, "indoor_heating_f": 68, "indoor_cooling_f": 75,
    "indoor_rh_pct": 50, "wall_u": 0.09, "ceiling_u": 0.031,
    "roof_color": "medium", "floor_type": "slab", "slab_edge": "r5",
    "floor_cover": "carpet", "window_u": 0.37, "window_shgc": 0.335,
    "window_height_ft": 4.5, "interior_shade": "drapes_half",
    "insect_screen": "half", "overhang_depth_ft": 2, "overhang_gap_ft": 0,
    "door_u": 0.4, "ach50": 5.03, "ventilation_type": "balanced",
    "ventilation_cfm": 93, "duct_location": "attic", "duct_r": 8,
    "duct_leakage_pct": 5,
    "rooms": [{
        "name": "House", "type": "other", "area": 2088,
        "walls": {"N": 74, "S": 74, "E": 36, "W": 36},
        "windows": {"W": 81, "S": 16, "E": 57},
        "door_area": 42, "top": True, "ground": True,
    }],
}

SACRAMENTO = {
    "floor_area_ft2": 1754, "stories": 1, "ceiling_height_ft": 8.8, "bedrooms": 3,
    "occupants": 4, "latitude": 38.5, "elevation_ft": 33,
    "heating_design_f": 26, "cooling_design_f": 98, "cooling_wet_bulb_f": 69.5,
    "daily_range_f": 30, "indoor_heating_f": 68, "indoor_cooling_f": 75,
    "indoor_rh_pct": 50, "wall_u": 0.089, "ceiling_u": 0.032, "roof_color": "dark",
    "floor_type": "slab", "slab_edge": "none", "floor_cover": "carpet",
    "window_u": 0.35, "window_shgc": 0.35, "window_height_ft": 5,
    "interior_shade": "drapes_half", "insect_screen": "half",
    "overhang_depth_ft": 2, "overhang_gap_ft": 1, "door_u": 0.46, "ach50": 5,
    "ventilation_type": "exhaust", "ventilation_cfm": 60, "duct_location": "attic",
    "duct_r": 8, "duct_leakage_pct": 5, "internal_sensible_btuh": 2120,
    "internal_latent_btuh": 1800,
    "rooms": [{
        "name": "House", "type": "other", "area": 1754,
        "walls": {"NE": 57, "SW": 57, "NW": 46.5, "SE": 46.5},
        "windows": {"NE": 111.5, "NW": 47.5, "SE": 40, "SW": 88, "S": 15, "W": 15},
        "door_area": 40, "top": True, "ground": True,
    }],
}


def run(**changes):
    return h.calculate_hvac_loads(changes, detail=False)


class TestPublishedHouses:
    def test_atlanta_heating_matches_ashrae(self):
        result = h.calculate_hvac_loads(ATLANTA, detail=False)
        assert result["heating_total"] == pytest.approx(27301, rel=0.02)

    def test_atlanta_heating_components_match_ashrae(self):
        parts = h.calculate_hvac_loads(ATLANTA, detail=False)["heating"]["components"]
        assert parts["walls"] == pytest.approx(4460 + 1452, rel=0.01)
        assert parts["ceiling"] == pytest.approx(2714, rel=0.01)
        assert parts["floor"] == pytest.approx(4620, rel=0.01)
        assert parts["doors"] == pytest.approx(706, rel=0.01)

    def test_atlanta_cooling_room_load_is_the_calibration_point(self):
        cooling = h.calculate_hvac_loads(ATLANTA, detail=False)["cooling"]
        assert cooling["room_load"] == pytest.approx(11380, rel=0.02)

    def test_atlanta_sensible_within_ten_percent(self):
        result = h.calculate_hvac_loads(ATLANTA, detail=False)
        assert result["cooling_sensible"] == pytest.approx(14453, rel=0.10)

    def test_atlanta_ventilation_latent_matches_ashrae(self):
        # 4840 x 129 cfm x 0.0050 lb/lb is 3122 Btu/h in the handbook. Our Q is
        # slightly lower because Equation 10 gives IDF 0.46 where it reads 0.48
        # from a table, and our humidity difference comes from Eq. 35.
        latent = h.calculate_hvac_loads(ATLANTA, detail=False)["cooling"]["latent_components"]
        flow_load = latent["infiltration"] + latent["ventilation"]
        assert flow_load == pytest.approx(3122, rel=0.08)
        assert latent["internal"] == pytest.approx(378, abs=2)

    def test_sacramento_heating_within_seven_percent_of_manual_j(self):
        result = h.calculate_hvac_loads(SACRAMENTO, detail=False)
        assert result["heating_total"] == pytest.approx(30850, rel=0.07)

    def test_sacramento_cooling_within_twelve_percent_of_manual_j(self):
        # Independent check, not used for calibration.
        result = h.calculate_hvac_loads(SACRAMENTO, detail=False)
        assert result["cooling_sensible"] == pytest.approx(21863, rel=0.12)
        assert result["cooling_total"] == pytest.approx(23778, rel=0.12)


class TestMoistAir:
    def test_saturation_pressure_at_known_points(self):
        assert h.saturation_pressure_psia(212) == pytest.approx(14.696, rel=0.002)
        assert h.saturation_pressure_psia(70) == pytest.approx(0.3633, rel=0.003)

    def test_humidity_ratio_at_design_indoor_condition(self):
        # 75 °F and 50% RH is the familiar 64.8 grains per pound.
        w = h.humidity_ratio_from_rh(75, 50, 14.696)
        assert w * 7000 == pytest.approx(64.8, abs=0.5)

    def test_wet_bulb_equal_to_dry_bulb_is_saturated(self):
        saturated = h.humidity_ratio_from_rh(80, 100, 14.696)
        assert h.humidity_ratio_from_wet_bulb(80, 80, 14.696) == pytest.approx(saturated, rel=1e-3)

    def test_air_factors_drop_with_altitude(self):
        c_s, c_l = h.air_factors(5000)
        assert c_s == pytest.approx(1.08 * 0.832, rel=0.01)
        assert c_l == pytest.approx(4840 * 0.832, rel=0.01)


class TestSolar:
    @pytest.mark.parametrize("side,azimuth,expected", [
        ("east", -90, 233), ("west", 90, 233), ("south", 0, 123), ("north", 180, 55),
    ])
    def test_peak_irradiance_near_ashrae_table(self, side, azimuth, expected):
        peak = max(
            sum(h.surface_irradiance(35, 7, t / 2, azimuth)[k] for k in ("direct", "diffuse"))
            for t in range(48)
        )
        assert peak == pytest.approx(expected, rel=0.12)

    def test_no_sun_at_night(self):
        sun = h.surface_irradiance(40, 7, 1.0, 0)
        assert sun["direct"] == 0 and sun["diffuse"] == 0

    def test_west_wall_sees_afternoon_sun_only(self):
        assert h.surface_irradiance(40, 7, 9, 90)["direct"] == 0
        assert h.surface_irradiance(40, 7, 16, 90)["direct"] > 100


class TestPeriodicConduction:
    def test_zero_harmonic_is_the_u_factor(self):
        y = h.transfer_admittances(h.WALL_LAYERS["frame"], 0.09, 1 / 3.0)
        assert y[0].real == pytest.approx(0.09)

    def test_constant_driving_temperature_gives_u_dt(self):
        y = h.transfer_admittances(h.WALL_LAYERS["cmu"], 0.075, 1 / 3.0)
        flux = h.periodic_flux([20.0] * 24, y)
        assert all(value == pytest.approx(1.5, abs=1e-6) for value in flux)

    def test_masonry_damps_and_delays_more_than_frame(self):
        drive = [20 + 30 * math.sin(2 * math.pi * (t - 9) / 24) for t in h.HOURS]
        frame = h.periodic_flux(drive, h.transfer_admittances(h.WALL_LAYERS["frame"], 0.09, 1 / 3.0))
        masonry = h.periodic_flux(drive, h.transfer_admittances(h.WALL_LAYERS["cmu"], 0.09, 1 / 3.0))
        assert max(masonry) - min(masonry) < max(frame) - min(frame)
        assert masonry.index(max(masonry)) > frame.index(max(frame))

    def test_matrix_solution_matches_explicit_finite_differences(self):
        """Independent check: march a single slab to its periodic state."""
        k, rho, c = h.MATERIALS["concrete"]
        thickness = 8.0 / 12.0
        r_out, r_in = 1 / 3.0, h.R_FILM_IN
        u = 1.0 / (r_out + thickness / k + r_in)
        admittances = h.transfer_admittances([("concrete", 8.0)], u, r_out)
        drive = [30 * math.cos(2 * math.pi * (t - 15) / 24) for t in h.HOURS]
        exact = h.periodic_flux(drive, admittances)

        nodes = 16
        dx = thickness / nodes
        alpha = k / (rho * c)
        dt = 0.2 * dx * dx / alpha
        steps = round(1.0 / dt)
        dt = 1.0 / steps
        temperature = [0.0] * nodes
        result = [0.0] * 24
        for hour in range(24 * 14):
            for step in range(steps):
                now = hour + step / steps
                outside = 30 * math.cos(2 * math.pi * (now - 15) / 24)
                new = temperature[:]
                for i in range(nodes):
                    left = (
                        (outside - temperature[0]) / (r_out + dx / 2 / k)
                        if i == 0 else k * (temperature[i - 1] - temperature[i]) / dx
                    )
                    right = (
                        (temperature[-1]) / (r_in + dx / 2 / k)
                        if i == nodes - 1 else k * (temperature[i] - temperature[i + 1]) / dx
                    )
                    new[i] = temperature[i] + dt * (left - right) / (rho * c * dx)
                temperature = new
            if hour >= 24 * 13:
                result[hour - 24 * 13] = temperature[-1] / (r_in + dx / 2 / k)
        for fd, matrix in zip(result, exact):
            assert fd == pytest.approx(matrix, abs=0.05)


class TestAirLeakage:
    @pytest.mark.parametrize("height,design,expected", [
        (8, 0, 1.14), (8, 20, 1.01), (8, 40, 0.88), (16, 0, 1.58), (24, -20, 2.41),
    ])
    def test_heating_driving_force_matches_ashrae_table_5(self, height, design, expected):
        assert h.infiltration_driving_force(height, 68 - design, True) == pytest.approx(expected, abs=0.012)

    @pytest.mark.parametrize("height,design,expected", [(8, 95, 0.48), (16, 85, 0.48), (24, 105, 0.98)])
    def test_cooling_driving_force_matches_ashrae_table_5(self, height, design, expected):
        assert h.infiltration_driving_force(height, design - 75, False) == pytest.approx(expected, abs=0.012)

    def test_leakage_area_rule(self):
        assert h.leakage_area_in2(5, 16000) == pytest.approx(0.055 * 5 * 16000 / 60)

    def test_exhaust_fan_flow_combines_per_ashrae_equation_14(self):
        with_fan = run(ventilation_type="exhaust", ventilation_cfm=50)
        without = run()
        q_i = without["heating"]["air"]["combined"]
        assert with_fan["heating"]["air"]["combined"] == pytest.approx(q_i + 25)

    def test_large_exhaust_dominates(self):
        result = run(ventilation_type="exhaust", ventilation_cfm=5000)
        assert result["heating"]["air"]["combined"] == pytest.approx(5000)


class TestDuctFactors:
    @pytest.mark.parametrize("loc,stories,leak,r,mode,room,around,expected", [
        ("attic", 1, 5, 8, "C", 75, 120, 0.27),
        ("attic", 1, 11, 8, "C", 75, 120, 0.63),
        ("attic", 2, 5, 4, "F", 68, 32, 0.14),
        ("attic", 1, 11, 0, "HP", 68, 32, 0.56),
        ("basement", 1, 5, 8, "F", 68, 64, 0.08),
        ("vented_crawl", 2, 11, 8, "C", 75, 72, 0.11),
    ])
    def test_table_points_are_reproduced(self, loc, stories, leak, r, mode, room, around, expected):
        assert h.duct_loss_factor(loc, stories, leak, r, mode, room, around) == pytest.approx(expected, abs=1e-9)

    def test_conditioned_ducts_have_no_loss(self):
        assert h.duct_loss_factor("conditioned", 1, 20, 0, "C", 75, 75) == 0

    def test_hotter_attic_raises_the_factor_less_than_proportionally(self):
        # Supply leaks waste the same share whatever surrounds the duct.
        base = h.duct_loss_factor("attic", 1, 5, 8, "C", 75, 120)
        hot = h.duct_loss_factor("attic", 1, 5, 8, "C", 75, 165)
        assert base < hot < 2 * base

    def test_cold_climate_furnace_factor_stays_believable(self):
        # Well below the room-to-attic ratio of 66/36 = 1.83.
        table = h.duct_loss_factor("attic", 1, 11, 8, "F", 68, 32)
        cold = h.duct_loss_factor("attic", 1, 11, 8, "F", 70, 4)
        assert 1.1 * table < cold < 1.5 * table

    def test_tight_ducts_follow_conduction_only(self):
        base = h.duct_loss_factor("attic", 1, 0, 8, "F", 68, 32)
        cold = h.duct_loss_factor("attic", 1, 0, 8, "F", 68, 2)
        assert cold / base == pytest.approx((123 - 2) / (123 - 32))

    def test_less_leakage_never_raises_the_factor(self):
        values = [h.duct_loss_factor("attic", 1, x, 8, "C", 75, 120) for x in (0, 2, 4, 5, 8, 11, 20)]
        assert values == sorted(values)

    def test_more_insulation_never_raises_the_factor(self):
        values = [h.duct_loss_factor("attic", 1, 8, r, "F", 68, 32) for r in (0, 2, 4, 6, 8, 12, 30)]
        assert values == sorted(values, reverse=True)


class TestBehaviour:
    def test_heating_scales_with_temperature_difference(self):
        mild = run(heating_design_f=40, duct_location="conditioned")
        cold = run(heating_design_f=10, duct_location="conditioned")
        slab_free = cold["heating"]["components"]["walls"] / mild["heating"]["components"]["walls"]
        assert slab_free == pytest.approx(60 / 30)

    def test_tighter_house_has_lower_loads(self):
        assert run(ach50=3)["heating_total"] < run(ach50=10)["heating_total"]
        assert run(ach50=3)["cooling_total"] < run(ach50=10)["cooling_total"]

    def test_more_swing_lowers_the_cooling_load(self):
        loads = [run(temperature_swing_f=s)["cooling_sensible"] for s in (0, 1, 2, 3, 5)]
        assert loads == sorted(loads, reverse=True)

    def test_zero_swing_equals_fixed_setpoint_peak(self):
        result = run(temperature_swing_f=0)["cooling"]
        assert result["room_load"] == pytest.approx(result["fixed_setpoint_peak"])

    def test_more_mass_lowers_the_cooling_load(self):
        loads = [run(construction_mass=m)["cooling"]["room_load"] for m in ("light", "medium", "heavy")]
        assert loads == sorted(loads, reverse=True)

    def test_heating_ignores_sun_and_thermal_mass(self):
        assert run(construction_mass="heavy")["heating_total"] == run()["heating_total"]
        assert run(window_shgc=0.2)["heating_total"] == run()["heating_total"]

    def test_lower_shgc_reduces_cooling(self):
        assert run(window_shgc=0.25)["cooling_total"] < run(window_shgc=0.6)["cooling_total"]

    def test_overhang_reduces_cooling(self):
        assert run(overhang_depth_ft=3)["cooling_total"] < run(overhang_depth_ft=0)["cooling_total"]

    def test_altitude_reduces_air_loads(self):
        low = run(elevation_ft=0)["heating"]["components"]["infiltration"]
        high = run(elevation_ft=7000)["heating"]["components"]["infiltration"]
        assert high < low

    def test_dark_roof_heats_the_attic(self):
        assert run(roof_color="dark")["cooling"]["attic_at_peak"] > run(roof_color="white")["cooling"]["attic_at_peak"]

    def test_radiant_barrier_cools_the_attic(self):
        assert run(radiant_barrier=True)["cooling"]["attic_at_peak"] < run()["cooling"]["attic_at_peak"]

    def test_attic_temperature_is_physically_plausible(self):
        attic = run(roof_color="dark", cooling_design_f=95)["cooling"]["t_attic"]
        assert 115 < max(attic) < 160

    def test_dry_climate_has_no_negative_latent(self):
        result = run(cooling_design_f=100, cooling_wet_bulb_f=60)
        assert result["cooling"]["delta_w"] == 0
        assert result["cooling_latent"] > 0

    def test_erv_reduces_ventilation_latent_more_than_hrv(self):
        base = dict(ventilation_cfm=100, cooling_wet_bulb_f=78)
        erv = run(ventilation_type="erv", **base)["cooling_latent"]
        hrv = run(ventilation_type="hrv", **base)["cooling_latent"]
        balanced = run(ventilation_type="balanced", **base)["cooling_latent"]
        assert erv < hrv <= balanced

    def test_two_story_has_less_ceiling_more_wall(self):
        one = run(stories=1)["heating"]["components"]
        two = run(stories=2)["heating"]["components"]
        assert two["ceiling"] < one["ceiling"] and two["walls"] > one["walls"]

    @pytest.mark.parametrize("floor", [
        "slab", "crawl_vented", "crawl_sealed", "basement_conditioned",
        "basement_unconditioned", "over_garage", "over_ambient",
    ])
    def test_every_floor_type_runs_and_is_finite(self, floor):
        result = run(floor_type=floor)
        assert result["heating"]["components"]["floor"] >= 0
        assert math.isfinite(result["cooling_total"])

    def test_vented_crawl_loses_more_than_sealed_crawl_for_same_floor(self):
        vented = run(floor_type="crawl_vented", floor_u=0.2)["heating"]["components"]["floor"]
        sealed = run(floor_type="crawl_sealed", floor_u=0.2)["heating"]["components"]["floor"]
        assert sealed < vented

    def test_cathedral_ceiling_runs(self):
        assert run(ceiling_type="cathedral")["cooling_total"] > 0


class TestRooms:
    rooms = [
        {"name": "Living", "type": "living", "area": 400,
         "walls": {"W": 20, "S": 20}, "windows": {"W": 60}, "top": True, "ground": True},
        {"name": "Bedroom", "type": "bedroom", "area": 200,
         "walls": {"E": 14, "N": 14}, "windows": {"E": 20}, "top": True, "ground": True},
        {"name": "Kitchen", "type": "kitchen", "area": 200,
         "walls": {"N": 14}, "windows": {"N": 10}, "door_area": 20, "top": True, "ground": True},
    ]

    def test_room_loads_sum_to_block_heating(self):
        result = run(rooms=self.rooms)
        assert sum(r["heating"] for r in result["rooms"]) == pytest.approx(result["heating_total"])

    def test_room_airflows_sum_to_system_flow(self):
        result = run(rooms=self.rooms)
        assert sum(r["cooling_cfm"] for r in result["rooms"]) == pytest.approx(result["cooling"]["fan_cfm"])

    def test_west_room_peaks_later_than_east_room(self):
        result = run(rooms=self.rooms)
        living, bedroom = result["rooms"][0], result["rooms"][1]
        assert living["peak_hour"] > bedroom["peak_hour"]

    def test_rooms_diversity_makes_sum_of_peaks_exceed_block(self):
        result = run(rooms=self.rooms)
        assert sum(r["cooling"] for r in result["rooms"]) >= result["cooling_sensible"] - 1

    def test_floor_area_comes_from_rooms(self):
        assert run(rooms=self.rooms)["floor_area"] == 800

    def test_interior_room_carries_only_its_infiltration_share(self):
        # ASHRAE Chapter 17 allocates infiltration to rooms by volume, so a room
        # with no exterior surfaces still gets a share, and nothing else.
        rooms = self.rooms + [{"name": "Core", "type": "other", "area": 100, "walls": {},
                               "windows": {}, "top": False, "ground": False}]
        result = run(rooms=rooms)
        share = 100 / 900
        expected = result["heating"]["components"]["infiltration"] * share
        factor = 1 + result["heating"]["components"]["ducts"] / (
            result["heating_total"] - result["heating"]["components"]["ducts"])
        assert result["rooms"][-1]["heating"] == pytest.approx(expected * factor)

    def test_zero_area_room_is_rejected(self):
        with pytest.raises(ValueError, match="floor area"):
            run(rooms=[{"name": "Bad", "area": 0}])

    def test_bad_compass_side_is_rejected(self):
        with pytest.raises(ValueError, match="compass"):
            run(rooms=[{"name": "Bad", "area": 100, "walls": {"X": 10}}])


class TestUncertaintyAndUpgrades:
    def test_band_contains_the_result(self):
        result = h.calculate_hvac_loads({}, detail=True)
        band = result["uncertainty"]
        assert band["heating_low"] < result["heating_total"] < band["heating_high"]
        assert band["cooling_low"] < result["cooling_total"] < band["cooling_high"]

    def test_knowing_an_input_narrows_the_band(self):
        unknown = h.calculate_hvac_loads({}, detail=True)["uncertainty"]
        known = h.calculate_hvac_loads({}, ["ach50", "wall_u", "ceiling_u"], True)["uncertainty"]
        assert known["heating_high"] - known["heating_low"] < unknown["heating_high"] - unknown["heating_low"]

    def test_upgrades_all_reduce_or_hold_load(self):
        upgrades = h.calculate_hvac_loads({}, detail=True)["upgrades"]
        assert upgrades
        for item in upgrades:
            assert item["heating_saved"] >= -1 and item["cooling_saved"] >= -1

    def test_sealing_a_leaky_house_ranks_high(self):
        upgrades = h.calculate_hvac_loads({"ach50": 20}, detail=True)["upgrades"]
        assert "Air seal" in upgrades[0]["label"] or "Air seal" in upgrades[1]["label"]

    def test_orientation_sweep_has_eight_rotations(self):
        rotations = h.calculate_hvac_loads(
            {"window_area_n": 0, "window_area_e": 0, "window_area_s": 0, "window_area_w": 300},
            detail=True)["orientations"]
        assert len(rotations) == 8
        totals = [r["total"] for r in rotations]
        assert max(totals) > min(totals) * 1.05

    def test_detail_runs_quickly_enough_for_a_browser(self):
        import time
        start = time.perf_counter()
        h.calculate_hvac_loads(ATLANTA, detail=True)
        assert time.perf_counter() - start < 1.0


class TestEquipment:
    base = dict(heating_load=40000, cooling_sensible=20000, cooling_latent=5000,
                heating_design_f=10, cooling_design_f=90)

    def test_balance_point_of_a_known_line(self):
        # Load falls linearly to zero at 60 °F; a flat 20,000 Btu/h meets it at 35 °F.
        result = h.evaluate_equipment(
            heating_load=40000, cooling_sensible=1, cooling_latent=0, heating_design_f=10,
            cooling_design_f=90, indoor_heating_f=70, internal_gain_btuh=40000 / 60 * 10,
            hp_cap_47=20000, hp_cap_17=20000,
        )
        assert result["balance_point_f"] == pytest.approx(35, abs=0.2)

    def test_backup_heat_at_design(self):
        result = h.evaluate_equipment(**self.base, hp_cap_47=36000, hp_cap_17=24000)
        at_10 = 24000 - 7 * 400
        assert result["hp_capacity_at_design"] == pytest.approx(at_10)
        assert result["backup_kw_at_design"] == pytest.approx((40000 - at_10) / 3412.14)

    def test_cold_climate_point_extends_the_curve(self):
        plain = h.evaluate_equipment(**self.base, hp_cap_47=36000, hp_cap_17=30000)
        cold = h.evaluate_equipment(**self.base, hp_cap_47=36000, hp_cap_17=30000, hp_cap_5=28000)
        assert cold["hp_capacity_at_design"] > plain["hp_capacity_at_design"]

    def test_lockout_zeroes_capacity(self):
        result = h.evaluate_equipment(**self.base, hp_cap_47=36000, hp_cap_17=30000, hp_lockout_f=20)
        assert result["hp_capacity_at_design"] == 0

    def test_bins_split_compressor_and_backup(self):
        result = h.evaluate_equipment(
            **self.base, hp_cap_47=30000, hp_cap_17=20000, hp_min_47=10000,
            bins_start_f=-5, bins_hours=[20, 60, 150, 300, 500, 700, 800, 800, 700, 600, 400, 300, 200, 100],
        )
        assert 0 < result["heat_pump_energy_share"] < 1
        assert result["seasonal_cop"] > 1
        assert result["cycling_hours"] > 0

    def test_oversized_cooling_flags_advisory_not_required(self):
        result = h.evaluate_equipment(**self.base, cooling_total_at_design=60000)
        check = next(c for c in result["checks"] if "oversized" in c["name"])
        assert check["ok"] is False and check["kind"] == "advisory"

    def test_variable_speed_has_a_higher_limit(self):
        single = h.evaluate_equipment(**self.base, cooling_rated_btuh=30000)
        variable = h.evaluate_equipment(**self.base, cooling_rated_btuh=30000, cooling_stages="variable")
        assert variable["cooling_limit_pct"] > single["cooling_limit_pct"]

    def test_manufacturer_data_overrides_the_estimate(self):
        result = h.evaluate_equipment(**self.base, cooling_rated_btuh=30000,
                                      cooling_total_at_design=26000, cooling_sensible_at_design=21000)
        assert result["cooling_capacity_total"] == 26000
        assert result["cooling_capacity_latent"] == 5000
        assert result["cooling_source"] == "manufacturer table"

    def test_furnace_percent(self):
        result = h.evaluate_equipment(**self.base, furnace_output_btuh=60000)
        assert result["furnace_pct"] == pytest.approx(150)
        assert any("oversized" in c["name"] and not c["ok"] for c in result["checks"])

    def test_rejects_zero_load(self):
        with pytest.raises(ValueError):
            h.evaluate_equipment(0, 1, 1, 10, 90)


class TestBillCheck:
    def test_hand_calculation(self):
        # 100 therms at 90% over 1000 degree days: 9,000,000 / 24,000 = 375 Btu/h·°F.
        result = h.bill_check(100, "gas_therm", 90, 1000, 5)
        assert result["measured_ua"] == pytest.approx(375)
        assert result["measured_design_load"] == pytest.approx(375 * 60)

    def test_baseline_is_removed(self):
        with_base = h.bill_check(120, "gas_therm", 90, 1000, 5, baseline_usage=20)
        assert with_base["measured_ua"] == pytest.approx(375)

    @pytest.mark.parametrize("kwargs", [
        dict(usage=0, fuel="gas_therm", efficiency_pct=90, degree_days=100, heating_design_f=5),
        dict(usage=10, fuel="wood", efficiency_pct=90, degree_days=100, heating_design_f=5),
        dict(usage=10, fuel="gas_therm", efficiency_pct=0, degree_days=100, heating_design_f=5),
        dict(usage=10, fuel="gas_therm", efficiency_pct=90, degree_days=0, heating_design_f=5),
        dict(usage=10, fuel="gas_therm", efficiency_pct=90, degree_days=100, heating_design_f=5, baseline_usage=20),
    ])
    def test_rejects_bad_input(self, kwargs):
        with pytest.raises(ValueError):
            h.bill_check(**kwargs)


class TestValidation:
    @pytest.mark.parametrize("changes,match", [
        ({"floor_area_ft2": 0}, "floor_area_ft2"),
        ({"floor_area_ft2": -10}, "floor_area_ft2"),
        ({"wall_u": 0}, "wall_u"),
        ({"ach50": -1}, "ach50"),
        ({"window_shgc": 1.5}, "window_shgc"),
        ({"heating_design_f": 80}, "heating design"),
        ({"cooling_wet_bulb_f": 120}, "wet bulb"),
        ({"stories": 9}, "stories"),
        ({"latitude": 80}, "Latitude"),
        ({"floor_type": "lava"}, "floor type"),
        ({"duct_location": "moon"}, "duct location"),
        ({"duct_leakage_pct": 60}, "Duct leakage"),
        ({"not_a_real_input": 1}, "Unknown inputs"),
    ])
    def test_bad_inputs_raise_clear_errors(self, changes, match):
        with pytest.raises(ValueError, match=match):
            h.calculate_hvac_loads(changes, detail=False)

    def test_extreme_but_valid_inputs_stay_finite(self):
        result = run(floor_area_ft2=20000, ach50=40, heating_design_f=-40, cooling_design_f=120,
                     cooling_wet_bulb_f=85, window_pct_of_floor=60, duct_leakage_pct=40, duct_r=0)
        for key in ("heating_total", "cooling_total"):
            assert math.isfinite(result[key]) and result[key] > 0

    def test_windowless_tiny_house_runs(self):
        assert run(floor_area_ft2=100, window_pct_of_floor=0, door_area_ft2=0)["cooling_total"] > 0


class TestDocumentation:
    @pytest.mark.parametrize("function", ["calculate_hvac_loads", "evaluate_equipment", "bill_check"])
    def test_docstring_parses(self, function):
        doc = utils.get_documentation("pycalcs.hvac_loads", function)
        assert doc["parameters"], "parameters section missing"
        assert doc["returns"], "returns section missing"

    def test_every_input_is_documented(self):
        doc = utils.get_documentation("pycalcs.hvac_loads", "calculate_hvac_loads")
        assert set(h.DEFAULTS) <= set(doc["parameters"])

    def test_presets_reference_real_keys(self):
        for era in h.ERA_PRESETS.values():
            assert era["wall_preset"] in h.WALL_PRESETS
            assert era["ceiling_preset"] in h.CEILING_PRESETS
            assert era["window_preset"] in h.WINDOW_PRESETS
            assert era["slab_edge"] in h.SLAB_EDGE_F


class TestSizesAndDerivations:
    def test_suggested_size_is_the_smallest_above_the_lower_limit(self):
        sizes = h.suggest_sizes(40000, 30000, 95)
        factor = h.rated_to_design_factor(95)
        assert sizes["cooling_tons"] * 12000 * factor >= 0.9 * 30000
        assert (sizes["cooling_tons"] - 0.5) * 12000 * factor < 0.9 * 30000
        assert sizes["furnace_output"] == 40000

    def test_dry_climate_sensible_load_can_set_the_size(self):
        total_only = h.suggest_sizes(40000, 24000, 90)
        with_sensible = h.suggest_sizes(40000, 24000, 90, cooling_sensible=23000)
        assert with_sensible["cooling_tons"] > total_only["cooling_tons"]
        assert with_sensible["cooling_sensible_pct"] >= 90

    def test_huge_load_has_no_single_unit(self):
        assert h.suggest_sizes(500000, 500000, 95)["cooling_tons"] is None

    def test_every_component_has_a_derivation(self):
        result = h.calculate_hvac_loads({}, detail=True)
        derivations = result["derivations"]
        for key in result["heating"]["components"]:
            assert derivations["heating"][key]["equation"]
        for key in result["cooling"]["components"]:
            assert derivations["cooling"][key]["equation"]

    def test_heating_wall_derivation_shows_the_real_numbers(self):
        result = h.calculate_hvac_loads({"wall_u": 0.1}, detail=True)
        assert "0.100" in result["derivations"]["heating"]["walls"]["values"]

    def test_results_are_json_ready(self):
        import json
        json.dumps(h.calculate_hvac_loads(ATLANTA, detail=True))


class TestClimateData:
    """Checks the derived NOAA table against values printed in published sources."""

    @pytest.fixture(scope="class")
    def stations(self):
        import json
        from pathlib import Path
        path = Path(__file__).parent.parent / "tools/hvac-load-calculator/data/stations.json"
        return {s["id"]: s for s in json.loads(path.read_text())["stations"]}

    def test_atlanta_matches_ashrae_example(self, stations):
        # ASHRAE Ch. 17 Table 18: 1% 91.5 °F, MCWB 74 °F, DR 16.7 °F, 99% 26.5 °F.
        atlanta = stations["722190-13874"]
        assert atlanta["c1"] == pytest.approx(91.5, abs=1.5)
        assert atlanta["wb"] == pytest.approx(74, abs=1.5)
        assert atlanta["dr"] == pytest.approx(16.7, abs=1.5)
        assert atlanta["h99"] == pytest.approx(26.5, abs=3.5)

    def test_every_station_is_physically_sensible(self, stations):
        assert len(stations) > 500
        for s in stations.values():
            assert s["h996"] <= s["h99"] < s["c1"] <= s["c04"], s["n"]
            assert s["wb"] <= s["c1"], s["n"]
            assert s["lo_typ"] <= s["h99"], s["n"]
            assert 3 <= s["dr"] <= 55, s["n"]
            assert 8500 <= sum(s["b"]) <= 9000, s["n"]
            assert len(s["hdd"]) == len(s["cdd"]) == len(s["tm"]) == 12, s["n"]

    def test_zip_table_has_known_zips(self):
        from pathlib import Path
        rows = (Path(__file__).parent.parent / "tools/hvac-load-calculator/data/zips.txt").read_text().splitlines()
        table = {row.split()[0]: row.split()[1:] for row in rows}
        assert len(table) > 30000
        assert float(table["60601"][0]) == pytest.approx(41.9, abs=0.2)
        assert float(table["33101"][1]) == pytest.approx(-80.2, abs=0.2) if "33101" in table else True
