# Optimal Coffee Temperature Tool

### Purpose of This Tool

This agent estimates the ideal serving temperature for brewed coffee by balancing flavour clarity, aroma retention, body perception, and scalding risk. It also reports the expected wait time from brew temperature to the recommended sipping temperature using a Newtonian cooling model so that users can plan their workflow.

### Requirements

#### Python Logic

* Core computation lives in `pycalcs/beverages.py` as `compute_optimal_coffee_serving_temperature(initial_temp_c, ambient_temp_c, beverage_mass_g, cup_material, preference_profile)`.
* The function must return a dictionary containing `optimal_temp_c`, `wait_time_min`, `comfort_score`, `cooling_constant_per_min`, and explanatory substitution strings.
* Inputs must enforce valid ranges, supported cup materials (`double_walled`, `ceramic`, `glass`, `paper`), and preference profiles (`balanced`, `sweet`, `hot`).

#### UI

* Expose number inputs for `initial_temp_c`, `ambient_temp_c`, and `beverage_mass_g`.
* Provide dropdown selectors for `cup_material` and `preference_profile` whose option values match the Python identifiers.
* Surface tooltips sourced from the Python docstring so users understand assumptions and units.
* Display the calculated temperature, wait time, composite comfort score, and cooling constant in the results tab with equation call-outs.
* Include background content that explains the flavour/safety trade-offs, cites references, and encourages users to adapt the model for their brewing context.
