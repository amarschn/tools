import thermal_calc

def test_conduction():
    # Test basic conduction equation
    q = thermal_calc.conduction_heat_transfer(
        k=50,              # Steel (W/m·K)
        A=0.01,            # 10x10 cm (m²)
        T_hot=100,         # Hot side 100°C
        T_cold=25,         # Cold side 25°C
        L=0.005            # 5mm thickness (m)
    )
    # q = k * A * ΔT / L = 50 * 0.01 * 75 / 0.005 = 7500 W
    assert abs(q - 7500) < 1

def test_natural_convection_coefficient():
    # Test for vertical plate
    h = thermal_calc.natural_convection_coefficient(
        surface_type='plate',
        char_length=0.1,   # 10 cm
        T_surface=80,      # 80°C
        T_ambient=20,      # 20°C
        orientation='vertical'
    )
    # Should return a positive value in a reasonable range
    assert h > 2 and h < 15

def test_radiation():
    # Test radiation heat transfer
    q = thermal_calc.radiation_heat_transfer(
        emissivity=0.9,    # High emissivity surface
        A=0.1,             # 0.1 m²
        T_surface=100,     # 100°C
        T_ambient=20       # 20°C
    )
    # Should be positive and in a reasonable range for these temperatures
    assert q > 0 and q < 100

def test_full_calculation_plate():
    # Test the full calculation for a steel plate
    result = thermal_calc.thermal_dissipation_calculate(
        # Geometry
        geometry_type="plate",
        orientation="vertical",
        # Dimensions
        length=0.1,         # 10 cm
        width_or_diameter=0.1,  # 10 cm
        thickness=0.01,     # 1 cm
        # Material properties (steel)
        thermal_conductivity=50,  # W/m·K
        density=7800,       # kg/m³
        specific_heat=490,  # J/kg·K
        emissivity=0.8,     # Dimensionless
        # Thermal conditions
        initial_temp=100,   # °C
        ambient_temp=20,    # °C
        air_velocity=0,     # m/s (natural convection)
        # Simulation
        time_steps=50,
        total_time=1800     # 30 minutes
    )
    
    # Make sure the result has all expected keys
    assert "times" in result
    assert "temperatures" in result
    assert "heat_rates" in result
    assert "time_constant" in result
    
    # Check the final temperature is lower than initial
    assert result["final_temp"] < 100
    
    # Check the temperature is decreasing
    assert result["temperatures"][0] > result["temperatures"][-1]
    
    # More tests could be added to validate specific scenarios
    
def test_full_calculation_cylinder():
    # Test the full calculation for a steel cylinder
    result = thermal_calc.thermal_dissipation_calculate(
        # Geometry
        geometry_type="cylinder",
        orientation="horizontal_up",
        # Dimensions
        length=0.1,         # 10 cm
        width_or_diameter=0.05,  # 5 cm diameter
        thickness=0.0,      # Not used for cylinder
        # Material properties (steel)
        thermal_conductivity=50,  # W/m·K
        density=7800,       # kg/m³
        specific_heat=490,  # J/kg·K
        emissivity=0.8,     # Dimensionless
        # Thermal conditions
        initial_temp=100,   # °C
        ambient_temp=20,    # °C
        air_velocity=0,     # m/s (natural convection)
        # Simulation
        time_steps=50,
        total_time=1800     # 30 minutes
    )
    
    # Make sure the result has all expected keys
    assert "times" in result
    assert "temperatures" in result
    assert "heat_rates" in result
    assert "time_constant" in result
    
    # Check the final temperature is lower than initial
    assert result["final_temp"] < 100
    
    # Check the temperature is decreasing
    assert result["temperatures"][0] > result["temperatures"][-1]

def test_steady_state_plate_natural():
    # Test steady state calculation for a plate with known input power
    result = thermal_calc.calculate_steady_state_temperature(
        geometry={"type": "plate", "orientation": "vertical"},
        dimensions={"length": 0.1, "width": 0.1, "thickness": 0.01},
        material_properties={"emissivity": 0.8, "density": 1, "specific_heat": 1, "thermal_conductivity": 1}, # density/cp/k not used
        thermal_conditions={"ambient_temp": 20, "air_velocity": 0},
        heat_input=10.0 # Watts
    )

    assert "steady_state_temp" in result
    assert result["steady_state_temp"] > 20 # Temp should be above ambient
    assert abs(result["final_q_output"] - result["heat_input"]) < 0.1 # Check heat balance (within tolerance)
    assert result["converged"] is True

def test_steady_state_cylinder_forced():
    # Test steady state calculation for a cylinder with forced convection
    result = thermal_calc.calculate_steady_state_temperature(
        geometry={"type": "cylinder", "orientation": "vertical"}, # Orientation less critical for forced on cylinder
        dimensions={"diameter": 0.05, "length": 0.1},
        material_properties={"emissivity": 0.3},
        thermal_conditions={"ambient_temp": 25, "air_velocity": 2.0}, # 2 m/s air flow
        heat_input=15.0 # Watts
    )

    assert "steady_state_temp" in result
    assert result["steady_state_temp"] > 25
    assert abs(result["final_q_output"] - result["heat_input"]) < 0.1
    assert result["convection_type"] == "forced"
    assert result["converged"] is True


if __name__ == "__main__":
    test_conduction()
    test_natural_convection_coefficient()
    test_radiation()
    test_full_calculation_plate()
    test_full_calculation_cylinder()
    test_full_calculation_plate() # This implicitly tests the transient path via the wrapper

    # Add calls to new tests
    test_steady_state_plate_natural()
    test_steady_state_cylinder_forced()

    print("All tests passed.")