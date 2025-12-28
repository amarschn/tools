# Orders of Magnitude Atlas

## Purpose

This tool helps build intuition for the scale of engineering quantities by mapping log10 orders of magnitude to real-world anchors. Users select a domain and explore the ordered anchor list plus multiple visualization styles.

## Requirements

### Inputs

- Domain selection (length, mass, time, energy, power, pressure, data size).

### Outputs

- Anchor list ordered by log10 magnitude with base and scaled values.
- Span in decades between the smallest and largest anchors.
- Ratio between the smallest and largest anchors.
- Anchor count for the selected domain.
- Multiple visualization modes (constellation map, bars, bands, spine, histogram, cards).

### Assumptions & Limitations

- Anchor values are approximate and rounded to emphasize scale rather than precision.
- All magnitudes use base-10 (log10) scaling.
- Mass is formatted using grams for prefix display while base values remain in kilograms.
- The tool does not perform unit conversions beyond SI prefix scaling.

### References

- Common engineering approximations and widely cited fact sheets (CODATA, NASA, IEA), rounded for educational clarity.
