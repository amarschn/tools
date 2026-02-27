# Structural Resonance Quick-Checker

## Purpose
Estimates the structural natural frequencies of flat rectangular plates and cylindrical shells (rings). 

This tool is designed to support eNVH (Electrified Noise, Vibration, and Harshness) analysis during the early stages of electric motor and inverter design. By rapidly estimating the natural frequencies of motor housings or inverter covers, engineers can check if these frequencies coincide with electromagnetic excitation frequencies (such as the prominent spatial orders driven by motor pole/slot combinations) and avoid structural resonance.

## Features
- Calculates natural frequencies for both simply-supported flat plates and cylindrical rings.
- Supports the fundamental "breathing" mode (n=0) and inextensional ovaling/bending modes (n>=2) for cylinders.
- Includes presets for common engineering materials (Steel, Aluminum 6061, Cast Iron, Titanium) as well as custom material properties.
- Interactive tabbed interface for geometry and material inputs.

## Requirements
- Python back-end using Pyodide (no server required).
- No external Python dependencies required beyond the standard library.
