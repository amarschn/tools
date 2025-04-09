# Wire Sizing Reference Data

This document contains supplementary data used by or relevant to the Wire Sizing Calculator.

## Common Insulation Temperature Ratings

| Type        | Max Operating Temp (°C) | Common Use       | NEC Table Reference |
|-------------|-------------------------|------------------|---------------------|
| TW          | 60°C                    | Basic, dry/damp  | 310.104(A)          |
| THW, THWN   | 75°C                    | General purpose  | 310.104(A)          |
| THHN, XHHW  | 90°C                    | High temp, dry   | 310.104(A)          |
| XHHW-2      | 90°C                    | High temp, wet   | 310.104(A)          |
| USE-2       | 90°C                    | Underground      | 310.104(A)          |
| FEP (Teflon)| 200°C                   | High temp, plenum| 310.104(A)          |
| Silicone    | 150°C - 200°C           | High temp, flex  | (Varies)            |
| PVC         | 60°C - 105°C            | Appliance wire   | (Varies)            |

*Note: NEC 110.14(C) limits circuit ampacity based on the lowest temperature rating of any connected termination, device, or conductor.*

## Material Properties (Approx. at 20°C)

| Material  | Resistivity (ρ) (Ω·m) | Temp Coefficient (α) (/°C) |
|-----------|-------------------------|----------------------------|
| Copper    | 1.68 x 10⁻⁸             | 0.00393                    |
| Aluminum  | 2.65 x 10⁻⁸             | 0.00403                    |

## AWG Sizes and Approx. Area

| AWG     | Area (mm²) | Approx. Diam (mm) |
|---------|------------|-------------------|
| 18      | 0.823      | 1.02              |
| 16      | 1.31       | 1.29              |
| 14      | 2.08       | 1.63              |
| 12      | 3.31       | 2.05              |
| 10      | 5.26       | 2.59              |
| 8       | 8.37       | 3.26              |
| 6       | 13.3       | 4.11              |
| 4       | 21.15      | 5.19              |
| 2       | 33.6       | 6.54              |
| 1       | 42.4       | 7.35              |
| 1/0     | 53.5       | 8.25              |
| 2/0     | 67.4       | 9.27              |
| 3/0     | 85.0       | 10.4              |
| 4/0     | 107.2      | 11.7              |
| 250 kcmil| 127        | 12.7              |
| ...     | ...        | ...               |

*(kcmil = thousand circular mils)*

## Key NEC Tables (Reference)

- **NEC Table 310.16:** Ampacities of Insulated Conductors (Raceway, Cable, or Earth, based on 30°C Ambient). *Primary source for base ampacity.*
- **NEC Table 310.17:** Ampacities of Insulated Conductors (Free Air, based on 30°C Ambient).
- **NEC Table 310.15(B)(1):** Ambient Temperature Correction Factors.
- **NEC Table 310.15(C)(1):** Adjustment Factors for More Than Three Current-Carrying Conductors.
- **NEC Chapter 9, Table 8:** Conductor Properties (Resistance, Reactance).