# Composite Wall Heat Loss

## Purpose

Calculate steady heat flow through a stack of solid layers, with optional
convection films at either face. The tool reports heat flow in W and BTU/hr,
interface temperatures, and the resistance contributed by each layer.

## Requirements and scope

The model assumes one-dimensional conduction, constant material conductivity,
uniform area, and perfect contact between layers. It excludes thermal bridges,
air leakage, radiation, moisture transport, and transient heat storage. Material
names are labels; users supply conductivity values from their own material data.

The default wall is ready to calculate on load. Inputs use square metres,
degrees Celsius, and W/(m·K). Layer thickness can be entered in mm, m, or inches;
changing units converts every layer. Each layer has its own labeled section with
name, thickness, and conductivity, ordered from interior to exterior. Use
**+ Add layer** to append a material, or the minus button on a section to remove
it. At least one layer is required; the UI has no three-layer limit. Removing a
middle layer preserves the other layers' values and renumbers their sections.
New layers start at the equivalent of 10 mm and 0.2 W/(m·K), with a custom label.
These values are placeholders to replace with material data.

Each boundary can be an air temperature or a measured surface temperature.
An air boundary includes a positive convection coefficient in W/(m²·K).
A surface boundary omits that film. Zero or an invalid coefficient is rejected
when an air boundary is selected. Positive heat flow is from interior to exterior;
negative heat flow represents heat gain.

## Results and verification

The right-hand panel has Results and Background tabs. Results is selected on load,
except when a shared link points to a Background section. The wall inputs remain
visible when switching tabs. Heat flow appears first,
followed by U-value, heat flux, area-normalized R-value,
and US R-value. Clicking a result opens its substituted calculation. The
resistance table and interface temperatures are available in an expandable panel.

Whole-wall thermal resistance has units K/W and depends on wall area.
Area-normalized R-value has units m²·K/W; US R-value has units
hr·ft²·°F/BTU. The two area-normalized values describe the same assembly in
different units. They must not be confused with whole-wall resistance.

The temperature plot uses physical distance through the solids on its horizontal
axis. Both axes are linear and labeled with units. Films appear as temperature
drops at the wall faces without adding a fictitious thickness. Layer numbers
match the input order; hover labels identify interfaces.

A worked example and numbered governing equations appear in the Background tab.
Equations and substituted values come from the Python module. The browser formats
results and converts length inputs; it does not implement the thermal model.

## Default check

The default inputs are:

| Input | Value |
| --- | --- |
| Wall area | 10 m² |
| Interior / exterior air temperature | 21 / −5 °C |
| Layer 1 | 200 mm at 0.038 W/(m·K) |
| Layer 2 | 20 mm at 0.21 W/(m·K) |
| Layer 3 | 10 mm at 0.72 W/(m·K) |
| Interior / exterior convection coefficient | 8 / 25 W/(m²·K) |

Expected results are approximately **46.9544 W**, 160.2151 BTU/hr,
U = 0.180594 W/(m²·K), R = 5.537284879 m²·K/W, and
US R = 31.4422 hr·ft²·°F/BTU. Whole-wall resistance is 0.553728 K/W.
Doubling wall area doubles heat flow and halves whole-wall resistance, while
U-value and area-normalized R-values remain unchanged.

## Sharing and export

Copy link saves the complete form, including all current layers, thickness units,
blank fields, and the air/surface choice at each boundary. This page uses
a local URL serializer because omitting blank values or replaying unit-change
events would alter a restored model. Older metre-based links and links specifying
one, two, or three layers remain supported. New links contain a record for every
layer. A restored count beyond the three legacy defaults requires complete,
consecutive supplied layer records, so an arbitrary count cannot allocate empty
sections. Background table-of-contents fragments open the matching tab.

CSV export contains the last calculated inputs, SI and US results, individual
resistances, and interface temperatures with physical and cumulative-resistance
coordinates. Numeric values retain calculation precision. Input changes mark
results as stale and disable export until the next successful calculation.

## Implementation

- `pycalcs/heat_transfer.py`: `composite_wall_analysis`, thermal equations,
  validation, conversion constants, and substituted calculations.
- `index.html`: advanced-template layout patterns, explicit Calculate action,
  loading/error state, accessible field help, and Plotly temperature profile.
- `../../tests/test_composite_wall.py`: analytical checks, boundary combinations,
  area scaling, reversed heat flow, and invalid-input cases.

Settings provide Light, Dark, and Auto themes, comfortable/compact spacing, and
display precision. Preferences persist locally. Browser calculations run through
Pyodide and require access to its CDN on first load.

## Browser checks

1. Load the default wall and compare with the values above.
2. Change thickness units between mm, m, and inches; results should agree.
3. Add at least five layers, remove a middle layer, and confirm the surviving
   names, thicknesses, and conductivities are preserved. Remove down to one layer
   and confirm its minus button is disabled.
4. Change each boundary independently to a surface temperature; its film row
   disappears and the profile endpoint becomes a surface temperature.
5. Enter an invalid film coefficient and confirm an error rather than silent
   omission. Check zero and reversed temperature differences.
6. Verify the chart, inputs, copy link, and export in light and dark themes.
7. Open a shared link with at least five layers, nondefault units, and surface
   boundaries; recalculate and compare results. Download the CSV and compare its
   values with the page.
8. Verify Results/Background tab clicks and arrow-key navigation, including a
   shared link to a Background section. Switch tabs after resizing to mobile;
   the temperature plot and equations should fit their panel.
