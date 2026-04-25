// Balje efficiency field for the fan-type selector.
//
// Model (kept deliberately simple so it is defensible as a screening tool):
//
//   D_s_opt(N_s) = exp(0.833 − 0.524·ln N_s + 0.008·ln² N_s)
//   η_peak(N_s)  = max_i  η_i · exp(−0.5·[ln(N_s/N_s_i)/σ_i]²)
//   η(N_s, D_s)  = η_peak(N_s) · exp(−β·[ln(D_s/D_s_opt(N_s))]²)
//
// The Cordier fit matches the production tool (index.html: cordierDsJs).
// η_peak is a max over per-family Gaussians in ln(N_s); by construction every
// family peak sits exactly on the Cordier line, and the 2D "islands" that read
// as machine territories emerge from the combination of family humps and
// off-ridge decay — not from arbitrary ellipse placement.
//
// Tunable parameters have a single source of truth in BALJE_FAMILIES and
// BALJE_OFF_RIDGE_BETA so they can be iterated without touching chart code.

(function attachBaljePhysics(scope) {
    const BALJE_FAMILIES = [
        // Peak specific speeds follow the tool's CORDIER_TYPES anchors.
        // η_i values come from the Balje / Dixon envelope: FC centrifugal peaks
        // around 0.80, BC centrifugal mid-0.80s, mixed-flow near 0.90, axials
        // slightly above. σ_i is in ln(N_s): σ=0.30 ⇒ ±e^0.30 ≈ ±1.35× in N_s
        // to 1/e.
        //
        // Drag / peripheral is intentionally omitted. The fan-type selector
        // does not screen that family, so including it adds a low-efficiency
        // island at very low N_s that the user can't act on.
        {
            id: 'centrifugal_fc',
            label: 'FC centrifugal',
            color: '#b7791f',
            nsPeak: 0.60,
            etaPeak: 0.80,
            sigma: 0.32,
        },
        {
            id: 'centrifugal_bc',
            label: 'BC centrifugal',
            color: '#475569',
            nsPeak: 0.90,
            etaPeak: 0.87,
            sigma: 0.36,
        },
        {
            id: 'mixed',
            label: 'Mixed-flow',
            color: '#0f766e',
            nsPeak: 1.90,
            etaPeak: 0.90,
            sigma: 0.32,
        },
        {
            id: 'axial',
            label: 'Axial',
            color: '#2563eb',
            nsPeak: 4.00,
            etaPeak: 0.93,
            sigma: 0.40,
        },
    ];

    // Off-ridge Gaussian decay rate in ln(D_s / D_s_opt).
    // β = 0.60 ⇒ efficiency falls to ~75% of peak at a factor-of-2 deviation in D_s.
    // Tuned against the efficiency drop-off visible in Balje (1981) Fig. 3.1.
    const BALJE_OFF_RIDGE_BETA = 0.60;

    const CORDIER_FIT = { a: 0.833, b: 0.524, c: 0.008 };

    function dsOpt(ns) {
        const lnNs = Math.log(Math.max(ns, 1e-9));
        return Math.exp(CORDIER_FIT.a - CORDIER_FIT.b * lnNs + CORDIER_FIT.c * lnNs * lnNs);
    }

    // Locally, invert dsOpt numerically to find N_s_opt(D_s) for duty-point
    // snapping. Bisection on ln(N_s) is cheap and keeps us independent from the
    // quadratic inversion edge cases.
    function nsOptFromDs(ds, bounds) {
        const target = Math.log(Math.max(ds, 1e-9));
        let lo = Math.log(bounds?.min ?? 0.01);
        let hi = Math.log(bounds?.max ?? 30);
        for (let i = 0; i < 60; i += 1) {
            const mid = 0.5 * (lo + hi);
            const dsMid = Math.log(dsOpt(Math.exp(mid)));
            // D_s is monotone decreasing in N_s over the practical range.
            if (dsMid > target) { lo = mid; } else { hi = mid; }
        }
        return Math.exp(0.5 * (lo + hi));
    }

    function etaPeak(ns, families) {
        const list = families || BALJE_FAMILIES;
        let best = 0;
        for (const fam of list) {
            const z = Math.log(Math.max(ns, 1e-9) / fam.nsPeak) / fam.sigma;
            const contribution = fam.etaPeak * Math.exp(-0.5 * z * z);
            if (contribution > best) best = contribution;
        }
        return best;
    }

    function etaAt(ns, ds, options = {}) {
        const peak = etaPeak(ns, options.families);
        const offset = Math.log(ds / dsOpt(ns));
        const beta = options.beta ?? BALJE_OFF_RIDGE_BETA;
        return peak * Math.exp(-beta * offset * offset);
    }

    function logSpace(min, max, count) {
        const logMin = Math.log10(min);
        const logMax = Math.log10(max);
        return Array.from({ length: count }, (_, i) => {
            const t = count === 1 ? 0 : i / (count - 1);
            return 10 ** (logMin + t * (logMax - logMin));
        });
    }

    function efficiencyField(options = {}) {
        const nsMin = options.nsMin ?? 0.03;
        const nsMax = options.nsMax ?? 20;
        const dsMin = options.dsMin ?? 0.3;
        const dsMax = options.dsMax ?? 60;
        const resolution = options.resolution ?? 220;
        const families = options.families || BALJE_FAMILIES;
        const beta = options.beta ?? BALJE_OFF_RIDGE_BETA;

        const nsValues = logSpace(nsMin, nsMax, resolution);
        const dsValues = logSpace(dsMin, dsMax, resolution);

        const z = dsValues.map((ds) => nsValues.map((ns) => etaAt(ns, ds, { families, beta })));

        return { ns: nsValues, ds: dsValues, z };
    }

    // Sample the Cordier line for plotting. Returns parallel arrays of N_s, D_s
    // and the corresponding ridge-peak efficiency at each sample.
    function cordierLocus(options = {}) {
        const nsMin = options.nsMin ?? 0.03;
        const nsMax = options.nsMax ?? 20;
        const resolution = options.resolution ?? 240;
        const families = options.families || BALJE_FAMILIES;
        const ns = logSpace(nsMin, nsMax, resolution);
        return {
            ns,
            ds: ns.map((value) => dsOpt(value)),
            eta: ns.map((value) => etaPeak(value, families)),
        };
    }

    // Family peak anchor points. By construction every anchor sits on the
    // Cordier line (ds = dsOpt(nsPeak)), so plotting them produces markers
    // that line up with the heavy black curve — addressing the prior drift bug.
    function familyAnchors(families) {
        const list = families || BALJE_FAMILIES;
        return list.map((fam) => ({
            id: fam.id,
            label: fam.label,
            color: fam.color,
            ns: fam.nsPeak,
            ds: dsOpt(fam.nsPeak),
            eta: fam.etaPeak,
        }));
    }

    scope.BALJE_PHYSICS = {
        FAMILIES: BALJE_FAMILIES,
        OFF_RIDGE_BETA: BALJE_OFF_RIDGE_BETA,
        CORDIER_FIT,
        dsOpt,
        nsOptFromDs,
        etaPeak,
        etaAt,
        logSpace,
        efficiencyField,
        cordierLocus,
        familyAnchors,
    };
}(typeof window !== 'undefined' ? window : globalThis));
