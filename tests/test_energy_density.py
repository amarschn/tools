import pytest
from pycalcs.energy_density import analyze_energy_storage, ENERGY_SOURCES

def test_energy_density_basic():
    # Commuter car is 150 Wh/km, 400 km range -> 60,000 Wh = 60 kWh useful energy
    # li_ion_nmc:
    # 60 kWh useful / 0.9 = 66.666 kWh stored = 66,666.66 Wh
    # gravimetric density 250 Wh/kg -> 66,666.66 / 250 = 266.66 kg media mass
    # total mass = 266.66 / (1 - 0.3) = 380.95 kg
    res = analyze_energy_storage(
        vehicle_type="commuter_car",
        custom_consumption_wh_km=150, # Ignored since vehicle_type != 'custom'
        target_range_km=400,
        energy_source_1="li_ion_nmc",
        energy_source_2="gasoline"
    )
    
    assert res["useful_energy_kwh"] == pytest.approx(60.0)
    assert res["source1_total_energy_kwh"] == pytest.approx(66.666, rel=1e-3)
    assert res["source1_total_mass_kg"] == pytest.approx(380.95, rel=1e-3)

def test_energy_density_custom_vehicle():
    res = analyze_energy_storage(
        vehicle_type="custom",
        custom_consumption_wh_km=200,
        target_range_km=100,
        energy_source_1="li_ion_nmc",
        energy_source_2="solid_state"
    )
    
    # 20 kWh useful
    assert res["useful_energy_kwh"] == pytest.approx(20.0)

def test_invalid_inputs():
    with pytest.raises(ValueError, match="Unknown vehicle type"):
        analyze_energy_storage("spaceship", 150, 400, "gasoline", "diesel")

    with pytest.raises(ValueError, match="Target range must be positive"):
        analyze_energy_storage("custom", 150, -10, "gasoline", "diesel")
        
    with pytest.raises(ValueError, match="Unknown energy source 1"):
        analyze_energy_storage("suv", 150, 400, "magic_dust", "diesel")
