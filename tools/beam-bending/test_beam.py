import unittest
import beam_calc as calc

class TestBeamCalculator(unittest.TestCase):
    """
    Test cases for beam bending calculations.
    """
    
    def setUp(self):
        """Set up common test parameters."""
        self.calculator = calc.BeamCalculator()
        
        # Common parameters
        self.L = 2.0  # Length (m)
        self.P = 1000.0  # Point load (N)
        self.w = 500.0  # Distributed load (N/m)
        self.E = 200e9  # Young's modulus for steel (Pa)
        self.I = 1e-6  # Moment of inertia (m^4)
        
    def test_simply_supported_point_load_center(self):
        """Test simply supported beam with center point load."""
        result = self.calculator.simply_supported_point_load_center(
            L=self.L, P=self.P, E=self.E, I=self.I
        )
        
        # Check reactions
        self.assertAlmostEqual(result["reactions"]["Ra"], self.P/2)
        self.assertAlmostEqual(result["reactions"]["Rb"], self.P/2)
        
        # Check maximum values
        self.assertAlmostEqual(result["max_values"]["shear"], self.P/2)
        self.assertAlmostEqual(result["max_values"]["moment"], self.P*self.L/4)
        self.assertAlmostEqual(result["max_values"]["deflection"], self.P*self.L**3/(48*self.E*self.I))
        
    def test_simply_supported_udl(self):
        """Test simply supported beam with uniformly distributed load."""
        result = self.calculator.simply_supported_udl(
            L=self.L, w=self.w, E=self.E, I=self.I
        )
        
        # Check reactions
        self.assertAlmostEqual(result["reactions"]["Ra"], self.w*self.L/2)
        self.assertAlmostEqual(result["reactions"]["Rb"], self.w*self.L/2)
        
        # Check maximum values
        self.assertAlmostEqual(result["max_values"]["shear"], self.w*self.L/2)
        self.assertAlmostEqual(result["max_values"]["moment"], self.w*self.L**2/8)
        self.assertAlmostEqual(result["max_values"]["deflection"], 5*self.w*self.L**4/(384*self.E*self.I))
    
    def test_cantilever_point_load_end(self):
        """Test cantilever beam with end point load."""
        result = self.calculator.cantilever_point_load_end(
            L=self.L, P=self.P, E=self.E, I=self.I
        )
        
        # Check reactions
        self.assertAlmostEqual(result["reactions"]["Ra"], self.P)
        self.assertAlmostEqual(result["reactions"]["Ma"], self.P*self.L)
        
        # Check maximum values
        self.assertAlmostEqual(result["max_values"]["shear"], self.P)
        self.assertAlmostEqual(result["max_values"]["moment"], self.P*self.L)
        self.assertAlmostEqual(result["max_values"]["deflection"], self.P*self.L**3/(3*self.E*self.I))
    
    def test_cantilever_udl(self):
        """Test cantilever beam with uniformly distributed load."""
        result = self.calculator.cantilever_udl(
            L=self.L, w=self.w, E=self.E, I=self.I
        )
        
        # Check reactions
        self.assertAlmostEqual(result["reactions"]["Ra"], self.w*self.L)
        self.assertAlmostEqual(result["reactions"]["Ma"], self.w*self.L**2/2)
        
        # Check maximum values
        self.assertAlmostEqual(result["max_values"]["shear"], self.w*self.L)
        self.assertAlmostEqual(result["max_values"]["moment"], self.w*self.L**2/2)
        self.assertAlmostEqual(result["max_values"]["deflection"], self.w*self.L**4/(8*self.E*self.I))


if __name__ == "__main__":
    unittest.main()