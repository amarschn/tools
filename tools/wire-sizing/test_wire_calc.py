import unittest
import wire_calc # Import the module containing your functions

class TestWireCalculations(unittest.TestCase):

    def test_load_calculation_vi(self):
        result = wire_calc.calculate_wire_parameters(
            mode="calculate_size", circuit_type="DC", voltage=24, current=15, power=None,
            conductor_material="copper", insulation_rating_c=75, wire_length_m=10,
            ambient_temp_c=30, num_bundled_conductors=3
        )
        self.assertAlmostEqual(result['load_current'], 15)
        self.assertAlmostEqual(result['calculated_power'], 24 * 15)
        self.assertNotIn("errors", result)

    def test_load_calculation_vp_dc(self):
         result = wire_calc.calculate_wire_parameters(
            mode="calculate_size", circuit_type="DC", voltage=24, power=360, current=None,
             # ... other params ...
             conductor_material="copper", insulation_rating_c=75, wire_length_m=10,
            ambient_temp_c=30, num_bundled_conductors=3
         )
         self.assertAlmostEqual(result['load_current'], 360 / 24)
         self.assertNotIn("errors", result)

    def test_load_calculation_vp_ac(self):
         result = wire_calc.calculate_wire_parameters(
            mode="calculate_size", circuit_type="AC", voltage=120, power=1800, current=None, power_factor=0.9,
            # ... other params ...
            conductor_material="copper", insulation_rating_c=75, wire_length_m=10,
            ambient_temp_c=30, num_bundled_conductors=3
         )
         self.assertAlmostEqual(result['load_current'], 1800 / (120 * 0.9))
         self.assertNotIn("errors", result)


    def test_derating_factors(self):
        # Example: 40C ambient, 75C wire -> should use 0.82 factor
        # 5 conductors -> should use 0.80 factor
        result = wire_calc.calculate_wire_parameters(
            mode="calculate_size", circuit_type="DC", voltage=1, current=10, power=None, # Simple load
            conductor_material="copper", insulation_rating_c=75, wire_length_m=1,
            ambient_temp_c=40, num_bundled_conductors=5
        )
        self.assertAlmostEqual(result['temp_correction_factor'], 0.82)
        self.assertAlmostEqual(result['bundling_adjustment_factor'], 0.80)
        self.assertAlmostEqual(result['total_derating_factor'], 0.82 * 0.80)
        self.assertNotIn("errors", result)

    def test_calculate_size_basic(self):
        # Load 18A, Copper, 75C, 30C ambient, <=3 conductors -> Needs base ampacity >= 18.
        # Should select 14 AWG (base 20A).
        result = wire_calc.calculate_wire_parameters(
            mode="calculate_size", circuit_type="DC", current=18, voltage=1, power=None,
            conductor_material="copper", insulation_rating_c=75, wire_length_m=10,
            ambient_temp_c=30, num_bundled_conductors=3
        )
        self.assertEqual(result.get('recommended_wire_size'), "14 AWG")
        self.assertAlmostEqual(result.get('corrected_ampacity'), 20 * 1.0 * 1.0) # Base amp * factors
        self.assertNotIn("errors", result)

    def test_calculate_size_derated(self):
         # Load 25A, Copper, 75C, 40C ambient (0.82), 5 conductors (0.80)
         # Total derating = 0.656
         # Required base ampacity = 25 / 0.656 = 38.1A
         # Should select 8 AWG (base 50A)
        result = wire_calc.calculate_wire_parameters(
            mode="calculate_size", circuit_type="DC", current=25, voltage=1, power=None,
            conductor_material="copper", insulation_rating_c=75, wire_length_m=10,
            ambient_temp_c=40, num_bundled_conductors=5
        )
        self.assertEqual(result.get('recommended_wire_size'), "8 AWG")
        self.assertAlmostEqual(result.get('corrected_ampacity'), 50 * 0.82 * 0.80)
        self.assertNotIn("errors", result)


    def test_check_size_pass(self):
        # Check 12 AWG (25A base) for 18A load, basic conditions
         result = wire_calc.calculate_wire_parameters(
            mode="check_size", check_wire_size="12 AWG",
            circuit_type="DC", current=18, voltage=1, power=None,
            conductor_material="copper", insulation_rating_c=75, wire_length_m=10,
            ambient_temp_c=30, num_bundled_conductors=3
        )
         self.assertEqual(result.get('check_result'), "PASS")
         self.assertAlmostEqual(result.get('corrected_ampacity'), 25 * 1.0 * 1.0)
         self.assertNotIn("errors", result)

    def test_check_size_fail(self):
        # Check 14 AWG (20A base) for 22A load
         result = wire_calc.calculate_wire_parameters(
            mode="check_size", check_wire_size="14 AWG",
            circuit_type="DC", current=22, voltage=1, power=None,
            conductor_material="copper", insulation_rating_c=75, wire_length_m=10,
            ambient_temp_c=30, num_bundled_conductors=3
        )
         self.assertEqual(result.get('check_result'), "FAIL")
         self.assertAlmostEqual(result.get('corrected_ampacity'), 20 * 1.0 * 1.0)
         self.assertNotIn("errors", result)

    def test_voltage_drop(self):
         # 10 AWG Copper, 20m length, 30A load, assume op temp = 75C
         # R_10AWG_20C = 0.00328 ohm/m
         # alpha = 0.00393
         # R_75C = 0.00328 * (1 + 0.00393 * (75 - 20)) = 0.00399 ohm/m
         # R_total = 0.00399 * 20 = 0.0798 ohms
         # Vdrop = 30A * 0.0798 = 2.39V
         result = wire_calc.calculate_wire_parameters(
            mode="check_size", check_wire_size="10 AWG",
            circuit_type="DC", current=30, voltage=120, power=None,
            conductor_material="copper", insulation_rating_c=75, wire_length_m=20,
            ambient_temp_c=30, num_bundled_conductors=3
        )
         self.assertAlmostEqual(result.get('voltage_drop_v'), 2.39, delta=0.05)
         self.assertAlmostEqual(result.get('voltage_drop_percent'), (2.39 / 120)*100, delta=0.1)
         self.assertAlmostEqual(result.get('power_loss_w'), (30**2) * 0.0798, delta=0.5)
         self.assertNotIn("errors", result)

# Add more tests for edge cases, different materials, ratings, AC etc.

if __name__ == '__main__':
    unittest.main()