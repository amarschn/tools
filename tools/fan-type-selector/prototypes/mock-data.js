window.FAN_SELECTOR_PROTOTYPE_DATA = {
    duty: {
        flow: "1.00 m3/s",
        pressure: "500 Pa static",
        density: "1.204 kg/m3",
        packaging: "Target passage velocity 10.0 m/s -> 0.100 m2 equivalent area",
    },
    recommendation: {
        type: "Backward-Curved Centrifugal",
        shortType: "BC Centrifugal",
        family: "Radial",
        summary:
            "N_s = 0.80 and Cordier D_s = 2.12 imply a wheel around 573 mm at 1097 RPM for the current duty.",
        practical:
            "90-degree turn, deeper housing, compact face area. Acoustic risk is low, drive fit is custom speed fit, and architecture margin is high.",
        nextStep:
            "Carry the duty into the curve explorer with BC and FC loaded side by side for real fan review.",
    },
    metrics: [
        {
            label: "Predicted wheel",
            value: "573 mm",
            caption: "First packaging number to check",
        },
        {
            label: "Nominal sizes",
            value: "560 / 630 mm",
            caption: "Nearest practical hardware bracket",
        },
        {
            label: "Wheel speed",
            value: "1097 RPM",
            caption: "Screened from specific speed",
        },
        {
            label: "Drive fit",
            value: "Custom speed fit",
            caption: "Nearest nominal speed 900 RPM",
        },
        {
            label: "Acoustic risk",
            value: "Low",
            caption: "Tip speed 21.1 m/s",
        },
        {
            label: "Architecture margin",
            value: "High",
            caption: "Comfortably inside BC band",
        },
        {
            label: "Est. shaft power",
            value: "0.59 kW",
            caption: "At 84.4% estimated peak efficiency",
        },
    ],
    recommendationContext: {
        strengths: [
            "N_s = 0.80 sits inside the backward-curved centrifugal operating range.",
            "Comfortably inside the BC band, which usually means a robust efficiency-first radial fit.",
            "Non-overloading or stable loading behavior is favorable here.",
        ],
        watchouts: [
            "Not especially close to a nominal 900 RPM drive speed; expect belt trim, gearbox, or broad-range variable speed.",
            "Vendor curves still decide the final stall and surge margin.",
        ],
        runnerUp:
            "Mixed Flow is the nearest alternate at 73% fit. It trades some pressure comfort for a cleaner inline package.",
    },
    hardware: {
        packagingSignature: "90-degree turn, deeper housing, compact face area.",
        wheelNote:
            "The equivalent passage is smaller than the predicted wheel. Expect a tighter transition or stronger radial-style packaging bias.",
        driveNote:
            "Very likely needs some ratio trim rather than dropping onto a standard direct-drive induction motor speed.",
        sizeNote:
            "Continuous estimate is 573 mm, so the first real hardware checks are 560 and 630 mm wheels.",
    },
    candidates: [
        {
            name: "Backward-Curved Centrifugal",
            fit: "85%",
            wheel: "573 mm",
            speed: "1097 RPM",
            acoustic: "Low",
            drive: "Custom",
            margin: "High",
            note: "Efficiency-first radial fit with the strongest pressure tolerance.",
        },
        {
            name: "Mixed Flow",
            fit: "73%",
            wheel: "429 mm",
            speed: "2470 RPM",
            acoustic: "Medium",
            drive: "Near 3000 RPM",
            margin: "Moderate",
            note: "Inline fallback if the 90-degree turn is unacceptable.",
        },
        {
            name: "Axial",
            fit: "61%",
            wheel: "337 mm",
            speed: "4815 RPM",
            acoustic: "High",
            drive: "High-speed",
            margin: "Tight",
            note: "Flow-friendly but pressure-loaded and likely noisy for this duty.",
        },
        {
            name: "Forward-Curved Centrifugal",
            fit: "58%",
            wheel: "664 mm",
            speed: "754 RPM",
            acoustic: "Low",
            drive: "Near 900 RPM",
            margin: "Moderate",
            note: "Compact low-speed branch, but hump-region behavior needs more care.",
        },
    ],
    trace: [
        {
            title: "Specific Speed",
            value: "0.80 [—]",
            equation: "omega_s = omega * sqrt(Q) / (DeltaP / rho)^(3/4)",
            explanation:
                "This is the dimensionless coordinate doing most of the architecture screening work.",
        },
        {
            title: "Predicted Wheel Diameter",
            value: "573 mm",
            equation: "D = delta_s * sqrt(Q) / (DeltaP / rho)^(1/4)",
            explanation:
                "This is the first physical number to compare against packaging and standard hardware sizes.",
        },
        {
            title: "Drive Fit",
            value: "Custom speed fit",
            equation: "epsilon_N = min |(N - N_i) / N_i|",
            explanation:
                "Checks whether the screened RPM sits near common direct-drive motor families.",
        },
        {
            title: "Acoustic Risk",
            value: "Low",
            equation: "R_ac = 0.65 R_U + 0.20 R_V + 0.15 (1 - M)",
            explanation:
                "A comparative proxy built from tip speed, passage velocity, and architecture margin.",
        },
        {
            title: "Architecture Score",
            value: "85%",
            equation: "S = w_N S_N + w_eta S_eta + w_U S_U + w_A S_A",
            explanation:
                "The final heuristic score ranks the candidate types after the physical checks are formed.",
        },
    ],
};
