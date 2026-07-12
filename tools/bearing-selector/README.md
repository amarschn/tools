# Bearing Selector

A bore-first concept selector for comparing rolling-bearing families at one constant duty point.

## Purpose

The tool helps an engineer answer an early design question: given the required shaft bore and the resolved loads at one bearing, which bearing family is a sensible place to start?

It compares one representative NTN series in each of five families:

- 62-series deep-groove ball bearings
- 72-series, 30-degree single-row angular-contact ball bearings
- NU-EA cylindrical roller bearings
- 4T-320 metric tapered roller bearings
- 222-EA spherical roller bearings

The embedded v1 catalog contains one bearing per family at 25, 30, 35, 40, 45, and 50 mm bore: 30 traceable records in total.

## Requirements

The selector must:

- accept radial load, axial load, rotational speed, and shaft bore as the minimal inputs;
- use loads resolved at one bearing, not total shaft loads;
- compare equal-bore candidates without implying that their outside dimensions are equal;
- calculate NTN equivalent dynamic and static radial loads using family-specific factors;
- calculate basic L10 life at 90 percent reliability;
- check user-required life, static safety, and the selected grease/oil catalog speed limit;
- exclude NU cylindrical bearings whenever axial load is present;
- warn that angular-contact and tapered bearings normally require an opposed-pair calculation;
- show equations, substituted values, intermediate loads, and official catalog links;
- expose all candidates rather than hiding failed or inapplicable options;
- support SI and US load display while keeping the Python core in SI units;
- export the complete analysis as JSON.

## Calculation Core

The single source of calculation truth is [`pycalcs/bearings.py`](../../pycalcs/bearings.py). The browser page only gathers inputs and renders its result payload.

For each applicable candidate the core calculates:

1. Equivalent dynamic radial load, `P = X Fr + Y Fa`
2. Basic rating life, `L10h = 10^6 / (60 n) × (C / P)^p`
3. Equivalent static radial load, `P0 = max(X0 Fr + Y0 Fa, Fr)`
4. Basic static safety, `s0 = C0 / P0`
5. Catalog speed margin, `n_limit / n`

The life exponent is `p = 3` for ball bearings and `p = 10/3` for roller bearings.

## Recommendation Logic

A candidate qualifies only when it:

- meets the requested L10 life;
- meets the requested static safety factor;
- operates at or below the selected catalog allowable speed; and
- remains inside NTN's stated load range for the basic-life equation.

The top result is chosen only from qualifying candidates. Family suitability for the applied axial/radial ratio is considered first, then envelope size. If no candidate qualifies, the tool reports the closest result as marginal or unacceptable instead of presenting it as approved.

This is deliberately a transparent heuristic. Cost, availability, friction, stiffness, precision class, sealing, arrangement, and maintainability still require engineering judgment.

## Important Boundaries

This tool is not a final bearing or shaft-arrangement design. It does not calculate:

- shaft reactions or moment distribution;
- induced axial loads in angular-contact or tapered pairs;
- preload or endplay;
- modified life factors such as lubrication viscosity and contamination;
- fits, internal clearance, misalignment limits, temperature, seals, or mounting;
- variable-duty equivalent loads;
- reliability other than the basic L10 basis.

The catalog ratings and allowable speeds are manufacturer-specific. A similarly dimensioned bearing from another manufacturer may have different ratings.

## Test Cases

The JSON files under `test-cases/` are executable regression examples:

- radial-only electric motor duty;
- belt-drive combined loading;
- high-speed oil-lubricated screening;
- heavy loading where the catalog slice is marginal;
- axial-dominant paired-bearing duty.

`tests/test_bearings.py` executes every file so the examples cannot silently drift away from the calculation core.

## Official References

- [NTN Ball and Roller Bearings, catalog No. 2203/E](https://www.ntnglobal.com/en/products/catalog/en/2203/index.html)
- [Load ratings and bearing life](https://www.ntnglobal.com/en/products/catalog/pdf/2203E_a03.pdf)
- [Bearing load calculation](https://www.ntnglobal.com/en/products/catalog/pdf/2203E_a04.pdf)
- [Deep-groove ball bearing tables](https://www.ntnglobal.com/en/products/catalog/pdf/2203E_b02.pdf)
- [Angular-contact ball bearing tables](https://www.ntnglobal.com/en/products/catalog/pdf/2203E_b04.pdf)
- [Cylindrical roller bearing tables](https://www.ntnglobal.com/en/products/catalog/pdf/2203E_b06.pdf)
- [Tapered roller bearing tables](https://www.ntnglobal.com/en/products/catalog/pdf/2203E_b07.pdf)
- [Spherical roller bearing tables](https://www.ntnglobal.com/en/products/catalog/pdf/2203E_b08.pdf)

Catalog data were transcribed for engineering screening and should be checked against the current NTN catalog before procurement or release.
