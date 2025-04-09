import math
import json

# Calculate system reliability for a series system.
# For each component, failure rate λ = 1/MTBF.
# Total failure rate is the sum of the individual λ’s.
# System reliability over mission time T: R = exp(-λ_total * T)
def calculate_system_reliability(component_mtbf, mission_time):
    lambdas = [1.0 / mtbf for mtbf in component_mtbf]
    total_lambda = sum(lambdas)
    system_mtbf = 1.0 / total_lambda if total_lambda > 0 else float('inf')
    system_reliability = math.exp(-total_lambda * mission_time)
    # Also compute each component’s reliability over the mission time.
    individual_reliabilities = [math.exp(-(1.0 / mtbf) * mission_time) for mtbf in component_mtbf]
    return {
        "totalLambda": total_lambda,
        "systemMTBF": system_mtbf,
        "systemReliability": system_reliability,
        "individualReliabilities": individual_reliabilities
    }

# Perform basic reliability allocation.
# For a series system with equal components, each must achieve:
# R_component = (R_system_target)^(1/num_components),
# and the corresponding failure rate is found from R = exp(-λ * T)
def reliability_allocation(system_target_reliability, num_components, mission_time):
    required_component_reliability = system_target_reliability ** (1.0 / num_components)
    required_lambda = -math.log(required_component_reliability) / mission_time if mission_time > 0 else 0
    required_mtbf = 1.0 / required_lambda if required_lambda > 0 else float('inf')
    return {
        "requiredComponentReliability": required_component_reliability,
        "requiredLambda": required_lambda,
        "requiredMTBF": required_mtbf
    }

# Main function that combines both reliability calculation and allocation.
# The input parameters are provided from JavaScript.
#  - component_mtbf_str: a comma-separated string of component MTBF values (in hours)
#  - mission_time: the mission time (hours)
#  - system_target_reliability: (optional) target reliability for system allocation (between 0 and 1)
#  - num_components_allocation: (optional) number of components used for allocation
def reliability_calculate(component_mtbf_str, mission_time, system_target_reliability=None, num_components_allocation=None):
    try:
        component_mtbf = [float(x.strip()) for x in component_mtbf_str.split(",") if x.strip()]
    except Exception:
        return {"error": "Invalid component MTBF values. Ensure they are numbers separated by commas."}

    calc_results = calculate_system_reliability(component_mtbf, mission_time)
    
    allocation_results = None
    if system_target_reliability is not None and num_components_allocation is not None:
        allocation_results = reliability_allocation(system_target_reliability, num_components_allocation, mission_time)

    return {
       "calculation": calc_results,
       "allocation": allocation_results
    }

# This function is the main entry point called by JavaScript.
def main():
    # These globals are set from the JS code via Pyodide.
    component_mtbf_str = globals().get("component_mtbf_str", "")
    mission_time = float(globals().get("mission_time", "100"))
    system_target_reliability = globals().get("system_target_reliability", None)
    num_components_allocation = globals().get("num_components_allocation", None)

    if system_target_reliability is not None:
        system_target_reliability = float(system_target_reliability)
    if num_components_allocation is not None:
        num_components_allocation = int(num_components_allocation)
        
    result = reliability_calculate(component_mtbf_str, mission_time, system_target_reliability, num_components_allocation)
    return json.dumps(result)

if __name__ == "__main__":
    print(main())
