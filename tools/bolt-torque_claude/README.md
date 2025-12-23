# Bolt Torque Calculator (VDI 2230-Style Analysis)

## Purpose

This tool performs systematic analysis of preloaded bolted joints following the methodology outlined in **VDI 2230:2015**. It calculates assembly torque, bolt preload, joint stiffness, working loads, and safety factors for both ISO metric and SAE/ASTM imperial fasteners.

## Features

- **Dual Standard Support**: ISO metric (M6-M24) and SAE/UTS imperial (#6 through 1")
- **Comprehensive Grade Database**:
  - ISO: 4.6, 5.6, 8.8, 10.9, 12.9 (per ISO 898-1:2013)
  - SAE: Grade 2, 5, 8 (per SAE J429)
  - ASTM: A325, A490 (per ASTM F3125)
- **VDI 2230 Analysis**: Full joint stiffness, load factor, embedding loss calculation
- **Safety Factor Assessment**: Yield, clamping, fatigue, and shear slip verification
- **Interactive Visualizations**: Joint diagram, torque-tension curve, K-factor sensitivity
- **Uncertainty Quantification**: K-factor scatter and preload range estimation

## Inputs

### Fastener Parameters
| Parameter | Description | Units |
|-----------|-------------|-------|
| Fastener Standard | ISO Metric or SAE/UTS | - |
| Thread Size | Thread designation (e.g., M10x1.5, 1/2-13 UNC) | - |
| Bolt Grade | Material grade (e.g., 8.8, SAE Grade 5) | - |

### Joint Parameters
| Parameter | Description | Units |
|-----------|-------------|-------|
| Grip Length | Total clamped length | mm |
| Clamped Material | Material of clamped members | GPa (modulus) |
| Joint Type | Through-bolt or tap-bolt | - |

### Loading Parameters
| Parameter | Description | Units |
|-----------|-------------|-------|
| Axial Load | External tensile load per bolt | N |
| Shear Load | External shear load per bolt | N |
| Number of Bolts | Bolts in joint pattern | - |

### Assembly Parameters
| Parameter | Description | Units |
|-----------|-------------|-------|
| Tightening Method | Assembly method affecting scatter | - |
| Surface Condition | Thread/bearing lubrication | - |
| Operating Temperature | For thermal considerations | C |
| Surface Roughness | For embedding loss estimation | - |

## Outputs

### Primary Results
- **Assembly Torque**: Target tightening torque with uncertainty range (N-m)
- **Target Preload**: Initial bolt tension at 90% proof load (kN)
- **Minimum Preload**: Residual preload after scatter and embedding (kN)
- **K-Factor**: Nut factor with range for sensitivity

### Joint Characteristics
- **Bolt Stiffness (Kb)**: Axial stiffness of bolt (MN/m)
- **Joint Stiffness (Kj)**: Axial stiffness of clamped members (MN/m)
- **Load Factor (phi)**: Portion of external load carried by bolt
- **Embedding Loss**: Preload loss due to surface settling (kN)

### Safety Factors
- **SF_y**: Yield safety factor (target > 1.5)
- **SF_k**: Clamping safety factor (target > 1.5)
- **SF_D**: Fatigue safety factor (target > 2.0)
- **SF_G**: Shear slip safety factor (target > 1.5)

## Key Equations

### Torque-Tension Relationship
$$T = K \cdot d \cdot F_i$$

Where:
- T = Assembly torque (N-m)
- K = Nut factor (dimensionless, typically 0.10-0.25)
- d = Nominal bolt diameter (m)
- F_i = Bolt preload (N)

### Nut Factor (Long Form)
$$K = \frac{P}{2\pi d_2} + \frac{\mu_t}{\cos\alpha} + \frac{\mu_b \cdot D_m}{2d}$$

Where:
- P = Thread pitch
- d_2 = Pitch diameter
- mu_t = Thread friction coefficient
- mu_b = Bearing friction coefficient
- alpha = Thread half-angle (30 for 60 threads)
- D_m = Mean bearing diameter

### Load Factor
$$\phi_n = \frac{K_b}{K_b + K_j}$$

The load factor determines how external load is shared between bolt and joint.

### Working Loads
$$F_{b,max} = F_i + \phi_n \cdot F_a$$
$$F_{j,min} = F_i - (1 - \phi_n) \cdot F_a$$

### Yield Safety Factor
$$SF_y = \frac{R_{p0.2} \cdot A_s}{F_{b,max}}$$

## Assumptions & Limitations

### Assumptions
- Small deflection theory (linear elastic behavior)
- Concentric loading (no eccentric moments)
- Uniform contact pressure at bearing surfaces
- Static loading (fatigue assessment is approximate)
- Room temperature baseline (thermal effects not fully modeled)

### Limitations
- Does not consider thread stripping
- Fatigue calculation is simplified (use FEA for critical applications)
- Stiffness calculations use simplified multi-zone model
- Does not account for joint relaxation over time
- Assumes single shear plane for friction grip

## References

1. **VDI 2230:2015** - Systematic calculation of highly stressed bolted joints (German Mechanical Engineering Standard)
2. **ISO 898-1:2013** - Mechanical properties of fasteners made of carbon steel and alloy steel - Part 1: Bolts, screws and studs
3. **SAE J429** - Mechanical and Material Requirements for Externally Threaded Fasteners
4. **ASME B1.1** - Unified Inch Screw Threads (UN, UNR, and UNJ Thread Form)
5. **ISO 262** - ISO general purpose metric screw threads - Selected sizes for screws, bolts and nuts
6. **Bickford, J.H. (2007)** - *Introduction to the Design and Behavior of Bolted Joints*, 4th Edition, CRC Press
7. **Budynas & Nisbett** - *Shigley's Mechanical Engineering Design*, 11th Edition, Chapter 8

## K-Factor Reference Table

| Condition | K_min | K_typical | K_max | Notes |
|-----------|-------|-----------|-------|-------|
| Dry Steel | 0.16 | 0.20 | 0.25 | Unlubricated, degreased |
| Oiled | 0.12 | 0.15 | 0.18 | Light machine oil |
| Moly Lube | 0.08 | 0.11 | 0.14 | MoS2 paste or spray |
| Cadmium Plated | 0.10 | 0.13 | 0.16 | Cad plate, as-received |
| Zinc Plated Dry | 0.17 | 0.20 | 0.23 | Zinc plate, no oil |
| Zinc Plated Oiled | 0.13 | 0.16 | 0.19 | Zinc plate with oil |
| Phosphate + Oil | 0.11 | 0.14 | 0.17 | Parkerized + oil |
| PTFE Coated | 0.06 | 0.09 | 0.12 | Fluoropolymer coating |
| Stainless Dry | 0.25 | 0.30 | 0.35 | Requires anti-seize! |
| Stainless Lubed | 0.14 | 0.17 | 0.20 | With anti-seize |

*Source: Bickford (2007), VDI 2230:2015*
