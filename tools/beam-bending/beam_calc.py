# calc.py - Beam Bending Calculator
import math
import numpy as np

class BeamCalculator:
    """
    Calculates beam reactions, shear force, bending moment, slope, and deflection
    for standard beam loading scenarios.
    """
    
    def __init__(self):
        # Dictionary of loading scenarios with their calculation functions
        self.scenarios = {
            "simply_supported_point_load_center": self.simply_supported_point_load_center,
            "simply_supported_point_load": self.simply_supported_point_load,
            "simply_supported_udl": self.simply_supported_udl,
            "cantilever_point_load_end": self.cantilever_point_load_end,
            "cantilever_udl": self.cantilever_udl
        }
        
    def simply_supported_point_load_center(self, L, P, E, I, num_points=100):
        """
        Simply supported beam with point load P at center
        
        Args:
            L: Length of beam (m)
            P: Point load (N)
            E: Modulus of elasticity (Pa)
            I: Moment of inertia (m^4)
            num_points: Number of points for discretization
            
        Returns:
            Dictionary with calculation results
        """
        # Reactions
        Ra = P/2
        Rb = P/2
        
        # Maximum values
        max_shear = P/2
        max_moment = P*L/4
        max_deflection = P*L**3/(48*E*I)
        
        # Create coordinate points along beam
        x = np.linspace(0, L, num_points)
        
        # Shear Force Diagram
        shear = np.ones_like(x) * Ra
        shear[x > L/2] = -Rb
        
        # Bending Moment Diagram
        moment = Ra * x
        moment[x > L/2] = Ra * x[x > L/2] - P * (x[x > L/2] - L/2)
        
        # Deflection
        deflection = np.zeros_like(x)
        for i, xi in enumerate(x):
            if xi <= L/2:
                deflection[i] = (P*xi/(48*E*I)) * (3*L**2 - 4*xi**2)
            else:
                deflection[i] = (P/(48*E*I)) * (3*L*xi**2 - 4*xi**3 - L**3)
        
        # Calculate maximum stress
        y_max = math.sqrt(I)  # Approximate for visualization (depends on shape)
        max_stress = max_moment * y_max / I
        
        return {
            "reactions": {"Ra": Ra, "Rb": Rb},
            "max_values": {
                "shear": max_shear,
                "moment": max_moment,
                "deflection": max_deflection,
                "stress": max_stress
            },
            "diagrams": {
                "x": x.tolist(),
                "shear": shear.tolist(),
                "moment": moment.tolist(),
                "deflection": deflection.tolist()
            }
        }
    
    def simply_supported_point_load(self, L, P, a, E, I, num_points=100):
        """
        Simply supported beam with point load P at distance 'a' from left support
        
        Args:
            L: Length of beam (m)
            P: Point load (N)
            a: Distance from left support (m)
            E: Modulus of elasticity (Pa)
            I: Moment of inertia (m^4)
            num_points: Number of points for discretization
            
        Returns:
            Dictionary with calculation results
        """
        # Validate input
        if a > L:
            raise ValueError("Distance 'a' cannot be greater than beam length")
        
        # Reactions
        b = L - a
        Ra = P * b / L
        Rb = P * a / L
        
        # Maximum values
        max_shear = max(Ra, Rb)
        max_moment = Ra * a
        max_deflection = (P * b * a * math.sqrt(3 * b**2 + 3 * a**2 - 2 * a * b - a**3 / b - b**3 / a)) / (27 * E * I * L)
        
        # Create coordinate points along beam
        x = np.linspace(0, L, num_points)
        
        # Shear Force Diagram
        shear = np.ones_like(x) * Ra
        shear[x > a] = -Rb
        
        # Bending Moment Diagram
        moment = Ra * x
        moment[x > a] = Ra * x[x > a] - P * (x[x > a] - a)
        
        # Deflection
        deflection = np.zeros_like(x)
        for i, xi in enumerate(x):
            if xi <= a:
                deflection[i] = (Ra * xi * (L**2 - b**2 - xi**2))/(6*E*I*L)
            else:
                deflection[i] = (Rb * (L - xi) * (L**2 - a**2 - (L - xi)**2) + P*b*(xi - a)**3/(6*L))/(6*E*I*L)
        
        # Calculate maximum stress
        y_max = math.sqrt(I)  # Approximate for visualization (depends on shape)
        max_stress = max_moment * y_max / I
        
        return {
            "reactions": {"Ra": Ra, "Rb": Rb},
            "max_values": {
                "shear": max_shear,
                "moment": max_moment,
                "deflection": max_deflection,
                "stress": max_stress
            },
            "diagrams": {
                "x": x.tolist(),
                "shear": shear.tolist(),
                "moment": moment.tolist(),
                "deflection": deflection.tolist()
            }
        }
    
    def simply_supported_udl(self, L, w, E, I, num_points=100):
        """
        Simply supported beam with uniformly distributed load w
        
        Args:
            L: Length of beam (m)
            w: Distributed load (N/m)
            E: Modulus of elasticity (Pa)
            I: Moment of inertia (m^4)
            num_points: Number of points for discretization
            
        Returns:
            Dictionary with calculation results
        """
        # Reactions
        Ra = w * L / 2
        Rb = w * L / 2
        
        # Maximum values
        max_shear = w * L / 2
        max_moment = w * L**2 / 8
        max_deflection = 5 * w * L**4 / (384 * E * I)
        
        # Create coordinate points along beam
        x = np.linspace(0, L, num_points)
        
        # Shear Force Diagram
        shear = Ra - w * x
        
        # Bending Moment Diagram
        moment = Ra * x - w * x**2 / 2
        
        # Deflection
        deflection = (w * x * (L**3 - 2*L*x**2 + x**3))/(24*E*I)
        
        # Calculate maximum stress
        y_max = math.sqrt(I)  # Approximate for visualization (depends on shape)
        max_stress = max_moment * y_max / I
        
        return {
            "reactions": {"Ra": Ra, "Rb": Rb},
            "max_values": {
                "shear": max_shear,
                "moment": max_moment,
                "deflection": max_deflection,
                "stress": max_stress
            },
            "diagrams": {
                "x": x.tolist(),
                "shear": shear.tolist(),
                "moment": moment.tolist(),
                "deflection": deflection.tolist()
            }
        }
    
    def cantilever_point_load_end(self, L, P, E, I, num_points=100):
        """
        Cantilever beam with point load P at free end
        
        Args:
            L: Length of beam (m)
            P: Point load (N)
            E: Modulus of elasticity (Pa)
            I: Moment of inertia (m^4)
            num_points: Number of points for discretization
            
        Returns:
            Dictionary with calculation results
        """
        # Reactions
        Ra = P  # Vertical reaction at fixed end
        Ma = P * L  # Moment reaction at fixed end
        
        # Maximum values
        max_shear = P
        max_moment = P * L
        max_deflection = P * L**3 / (3 * E * I)
        
        # Create coordinate points along beam
        x = np.linspace(0, L, num_points)
        
        # Shear Force Diagram (constant)
        shear = np.ones_like(x) * P
        
        # Bending Moment Diagram (linear)
        moment = P * (L - x)
        
        # Deflection
        deflection = (P * x**2 * (3*L - x))/(6*E*I)
        
        # Calculate maximum stress
        y_max = math.sqrt(I)  # Approximate for visualization (depends on shape)
        max_stress = max_moment * y_max / I
        
        return {
            "reactions": {"Ra": Ra, "Ma": Ma},
            "max_values": {
                "shear": max_shear,
                "moment": max_moment,
                "deflection": max_deflection,
                "stress": max_stress
            },
            "diagrams": {
                "x": x.tolist(),
                "shear": shear.tolist(),
                "moment": moment.tolist(),
                "deflection": deflection.tolist()
            }
        }
    
    def cantilever_udl(self, L, w, E, I, num_points=100):
        """
        Cantilever beam with uniformly distributed load w
        
        Args:
            L: Length of beam (m)
            w: Distributed load (N/m)
            E: Modulus of elasticity (Pa)
            I: Moment of inertia (m^4)
            num_points: Number of points for discretization
            
        Returns:
            Dictionary with calculation results
        """
        # Reactions
        Ra = w * L  # Vertical reaction at fixed end
        Ma = w * L**2 / 2  # Moment reaction at fixed end
        
        # Maximum values
        max_shear = w * L
        max_moment = w * L**2 / 2
        max_deflection = w * L**4 / (8 * E * I)
        
        # Create coordinate points along beam
        x = np.linspace(0, L, num_points)
        
        # Shear Force Diagram
        shear = w * (L - x)
        
        # Bending Moment Diagram
        moment = w * (L - x)**2 / 2
        
        # Deflection
        deflection = (w * x**2 * (6*L**2 - 4*L*x + x**2))/(24*E*I)
        
        # Calculate maximum stress
        y_max = math.sqrt(I)  # Approximate for visualization (depends on shape)
        max_stress = max_moment * y_max / I
        
        return {
            "reactions": {"Ra": Ra, "Ma": Ma},
            "max_values": {
                "shear": max_shear,
                "moment": max_moment,
                "deflection": max_deflection,
                "stress": max_stress
            },
            "diagrams": {
                "x": x.tolist(),
                "shear": shear.tolist(),
                "moment": moment.tolist(),
                "deflection": deflection.tolist()
            }
        }
    
    def calculate(self, scenario, params):
        """
        Main calculation function that calls the appropriate scenario calculation
        
        Args:
            scenario: String identifying the loading scenario
            params: Dictionary of parameters for the calculation
            
        Returns:
            Dictionary with calculation results
        """
        if scenario not in self.scenarios:
            raise ValueError(f"Unknown scenario: {scenario}")
        
        # Call the appropriate scenario function with the provided parameters
        return self.scenarios[scenario](**params)


def calculate_beam_response(scenario, **params):
    """
    Helper function to calculate beam response for a given scenario and parameters.
    This function is called from JavaScript in the frontend.
    
    Args:
        scenario: String identifying the loading scenario
        **params: Parameters specific to the scenario
    
    Returns:
        JSON-compatible dictionary with calculation results
    """
    calculator = BeamCalculator()
    result = calculator.calculate(scenario, params)
    
    # Add scenario name to the result
    result["scenario"] = scenario
    
    return result


# For testing directly in Python
if __name__ == "__main__":
    # Example calculation
    result = calculate_beam_response(
        "simply_supported_point_load_center",
        L=2.0,
        P=1000,
        E=210e9,
        I=1e-6
    )
    print(result)