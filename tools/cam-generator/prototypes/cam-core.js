/*
 * cam-core.js: shared cam kinematics for the cam generator prototypes.
 *
 * Conventions
 *   theta   cam angle, degrees in the public arrays, radians internally
 *   s       follower displacement (mm, or mm of arc at the roller for an
 *           oscillating follower)
 *   v, a, j derivatives of s with respect to cam angle in radians
 *           (mm/rad, mm/rad^2, mm/rad^3). Multiply by omega, omega^2,
 *           omega^3 for time derivatives.
 *   Cam rotates counter-clockwise. Profiles are returned in the cam frame.
 *
 * Production code should port this to pycalcs/cams.py so there is one source
 * of truth. The prototypes keep it in JS so every drag can recompute at 60 fps.
 */
(function (global) {
  'use strict';

  const TAU = 2 * Math.PI;
  const DEG = Math.PI / 180;
  const EPS = 1e-9;

  // ---------------------------------------------------------------------------
  // Normalized motion laws: u in [0, 1] -> [s, s', s'', s'''] with s(0)=0, s(1)=1
  // ---------------------------------------------------------------------------

  function cycloidal(u) {
    const t = TAU * u;
    return [u - Math.sin(t) / TAU, 1 - Math.cos(t), TAU * Math.sin(t), TAU * TAU * Math.cos(t)];
  }

  function harmonic(u) {
    const t = Math.PI * u;
    const p = Math.PI;
    return [0.5 * (1 - Math.cos(t)), 0.5 * p * Math.sin(t), 0.5 * p * p * Math.cos(t), -0.5 * p * p * p * Math.sin(t)];
  }

  function poly345(u) {
    return [
      10 * u ** 3 - 15 * u ** 4 + 6 * u ** 5,
      30 * u ** 2 - 60 * u ** 3 + 30 * u ** 4,
      60 * u - 180 * u ** 2 + 120 * u ** 3,
      60 - 360 * u + 360 * u ** 2,
    ];
  }

  function poly4567(u) {
    return [
      35 * u ** 4 - 84 * u ** 5 + 70 * u ** 6 - 20 * u ** 7,
      140 * u ** 3 - 420 * u ** 4 + 420 * u ** 5 - 140 * u ** 6,
      420 * u ** 2 - 1680 * u ** 3 + 2100 * u ** 4 - 840 * u ** 5,
      840 * u - 5040 * u ** 2 + 8400 * u ** 3 - 4200 * u ** 4,
    ];
  }

  // Constant velocity (straight line). Infinite acceleration at the ends, kept
  // only as a teaching example of what not to run at speed.
  function linear(u) {
    return [u, 1, 0, 0];
  }

  // Parabolic (constant acceleration). Finite acceleration, infinite jerk.
  function parabolic(u) {
    if (u < 0.5) return [2 * u * u, 4 * u, 4, 0];
    const w = 1 - u;
    return [1 - 2 * w * w, 4 * w, -4, 0];
  }

  /*
   * SCCA family (Sine-Constant-Cosine-Acceleration, Norton). b + c + d = 1.
   *   modified trapezoid  b = 0.25, c = 0.5, d = 0.25
   *   modified sine       b = 0.25, c = 0,   d = 0.75
   *   cycloidal           b = 0,    c = 0,   d = 1
   * The acceleration shape is built piecewise and integrated numerically once,
   * then normalized so s(1) = 1. Error is below 1e-8 of lift.
   */
  function sccaShape(b, c, d) {
    const z1 = b / 2;
    const z2 = (1 - d) / 2;
    const z3 = (1 + d) / 2;
    const z4 = 1 - b / 2;
    return function (x) {
      if (x < z1) return [Math.sin((Math.PI * x) / b), (Math.PI / b) * Math.cos((Math.PI * x) / b)];
      if (x < z2) return [1, 0];
      if (x < z3) {
        const t = (Math.PI * (x - z2)) / d;
        return [Math.cos(t), (-Math.PI / d) * Math.sin(t)];
      }
      if (x < z4) return [-1, 0];
      const t = (Math.PI * (1 - x)) / b;
      return [-Math.sin(t), (Math.PI / b) * Math.cos(t)];
    };
  }

  function makeScca(b, c, d) {
    const shape = sccaShape(b, c, d);
    const N = 8192;
    const acc = new Float64Array(N + 1);
    const vel = new Float64Array(N + 1);
    const dis = new Float64Array(N + 1);
    for (let i = 0; i <= N; i++) acc[i] = shape(i / N)[0];
    const h = 1 / N;
    for (let i = 1; i <= N; i++) {
      vel[i] = vel[i - 1] + 0.5 * h * (acc[i] + acc[i - 1]);
      dis[i] = dis[i - 1] + 0.5 * h * (vel[i] + vel[i - 1]) - (h * h * (acc[i] - acc[i - 1])) / 12;
    }
    const C = 1 / dis[N];
    return function (u) {
      const x = Math.min(1, Math.max(0, u)) * N;
      const i = Math.min(N - 1, Math.floor(x));
      const f = x - i;
      const [a, j] = shape(u);
      // Cubic-accurate displacement interpolation using the velocity at both ends.
      const s0 = dis[i];
      const s1 = dis[i + 1];
      const v0 = vel[i] * h;
      const v1 = vel[i + 1] * h;
      const f2 = f * f;
      const f3 = f2 * f;
      const s = (2 * f3 - 3 * f2 + 1) * s0 + (f3 - 2 * f2 + f) * v0 + (-2 * f3 + 3 * f2) * s1 + (f3 - f2) * v1;
      const v = vel[i] + f * (vel[i + 1] - vel[i]);
      return [C * s, C * v, C * a, C * j];
    };
  }

  const LAWS = {
    cycloidal: {
      name: 'Cycloidal',
      short: 'Cycloidal',
      fn: cycloidal,
      note: 'Smooth everywhere. Zero acceleration at both ends. A safe default for high speed.',
    },
    modified_sine: {
      name: 'Modified sine',
      short: 'Mod. sine',
      fn: makeScca(0.25, 0, 0.75),
      note: 'Lower peak velocity than cycloidal. Good for heavy loads where cam torque matters.',
    },
    modified_trapezoid: {
      name: 'Modified trapezoid',
      short: 'Mod. trap.',
      fn: makeScca(0.25, 0.5, 0.25),
      note: 'Lowest peak acceleration of the smooth laws. Common in indexers and pick-and-place.',
    },
    poly345: {
      name: '3-4-5 polynomial',
      short: '3-4-5',
      fn: poly345,
      note: 'Zero velocity and acceleration at the ends, jerk steps at the ends.',
    },
    poly4567: {
      name: '4-5-6-7 polynomial',
      short: '4-5-6-7',
      fn: poly4567,
      note: 'Zero jerk at the ends too. Gentlest start, at the price of higher peak acceleration.',
    },
    harmonic: {
      name: 'Simple harmonic',
      short: 'Harmonic',
      fn: harmonic,
      note: 'Acceleration jumps at both ends (infinite jerk). Fine at low speed only.',
    },
    parabolic: {
      name: 'Constant acceleration',
      short: 'Const. accel.',
      fn: parabolic,
      note: 'Lowest possible peak acceleration, but infinite jerk at three points.',
    },
    linear: {
      name: 'Constant velocity',
      short: 'Const. vel.',
      fn: linear,
      note: 'Infinite acceleration at the ends. Shown for contrast; never run it alone.',
    },
  };

  // Peak coefficients |s'|max, |s''|max, |s'''|max for each normalized law.
  function lawCoefficients(key) {
    const fn = LAWS[key].fn;
    let cv = 0;
    let ca = 0;
    let cj = 0;
    const N = 4000;
    for (let i = 0; i <= N; i++) {
      const [, v, a, j] = fn(i / N);
      cv = Math.max(cv, Math.abs(v));
      ca = Math.max(ca, Math.abs(a));
      cj = Math.max(cj, Math.abs(j));
    }
    // Discontinuities in s'' mean infinite jerk.
    const jumps = key === 'harmonic' || key === 'parabolic';
    const infiniteA = key === 'linear';
    return { cv, ca: infiniteA ? Infinity : ca, cj: jumps || infiniteA ? Infinity : cj };
  }

  // ---------------------------------------------------------------------------
  // Boundary-condition polynomials (Norton's "BC" method)
  // ---------------------------------------------------------------------------

  // Solve A x = b by Gaussian elimination with partial pivoting.
  function solve(A, b) {
    const n = b.length;
    const M = A.map((row, i) => [...row, b[i]]);
    for (let col = 0; col < n; col++) {
      let piv = col;
      for (let r = col + 1; r < n; r++) if (Math.abs(M[r][col]) > Math.abs(M[piv][col])) piv = r;
      [M[col], M[piv]] = [M[piv], M[col]];
      const p = M[col][col];
      if (Math.abs(p) < 1e-14) throw new Error('Singular boundary-condition system.');
      for (let r = col + 1; r < n; r++) {
        const f = M[r][col] / p;
        for (let k = col; k <= n; k++) M[r][k] -= f * M[col][k];
      }
    }
    const x = new Array(n).fill(0);
    for (let r = n - 1; r >= 0; r--) {
      let sum = M[r][n];
      for (let k = r + 1; k < n; k++) sum -= M[r][k] * x[k];
      x[r] = sum / M[r][r];
    }
    return x;
  }

  function fallingFactorial(m, k) {
    let p = 1;
    for (let i = 0; i < k; i++) p *= m - i;
    return p;
  }

  /*
   * Polynomial in u on [0, 1] meeting derivative conditions at both ends.
   * bc0, bc1: arrays [y, y', y'', ...] with derivatives taken in u.
   * Degree = bc0.length + bc1.length - 1. Returns coefficients c0..cn.
   */
  function bcPolynomial(bc0, bc1) {
    const n = bc0.length + bc1.length;
    const A = [];
    const b = [];
    bc0.forEach((val, k) => {
      const row = new Array(n).fill(0);
      row[k] = fallingFactorial(k, k);
      A.push(row);
      b.push(val);
    });
    bc1.forEach((val, k) => {
      const row = new Array(n).fill(0);
      for (let m = k; m < n; m++) row[m] = fallingFactorial(m, k);
      A.push(row);
      b.push(val);
    });
    return solve(A, b);
  }

  function polyEval(c, u) {
    // Returns [y, y', y'', y'''] at u.
    const out = [0, 0, 0, 0];
    for (let m = 0; m < c.length; m++) {
      for (let k = 0; k < 4 && k <= m; k++) out[k] += c[m] * fallingFactorial(m, k) * u ** (m - k);
    }
    return out;
  }

  // ---------------------------------------------------------------------------
  // Motion programs
  // ---------------------------------------------------------------------------

  function emptyMotion(n) {
    return {
      theta: new Float64Array(n + 1),
      s: new Float64Array(n + 1),
      v: new Float64Array(n + 1),
      a: new Float64Array(n + 1),
      j: new Float64Array(n + 1),
    };
  }

  /*
   * Build a motion from rise/fall/dwell segments.
   * segment: { type: 'rise'|'fall'|'dwell', duration: deg, lift: mm, law: key }
   * Lifts are positive; a fall subtracts. Durations should sum to 360.
   */
  function fromSegments(segments, opts = {}) {
    const n = opts.samples || 720;
    const total = segments.reduce((acc, sg) => acc + Number(sg.duration || 0), 0);
    const m = emptyMotion(n);
    const issues = [];
    if (Math.abs(total - 360) > 1e-6) issues.push(`Segment durations add to ${total.toFixed(1)}°, not 360°.`);
    let net = 0;
    segments.forEach((sg) => {
      if (sg.type === 'rise') net += Number(sg.lift);
      if (sg.type === 'fall') net -= Number(sg.lift);
    });
    if (Math.abs(net) > 1e-6) issues.push(`The follower ends ${net.toFixed(2)} mm from where it started.`);

    // Segment start angles and start heights
    const starts = [];
    let ang = 0;
    let h = 0;
    segments.forEach((sg) => {
      starts.push({ ang, h });
      ang += Number(sg.duration);
      if (sg.type === 'rise') h += Number(sg.lift);
      if (sg.type === 'fall') h -= Number(sg.lift);
    });
    const scale = total > 0 ? 360 / total : 1;

    let seg = 0;
    for (let i = 0; i <= n; i++) {
      const th = (360 * i) / n;
      m.theta[i] = th;
      const thScaled = th / scale;
      while (seg < segments.length - 1 && thScaled >= starts[seg].ang + Number(segments[seg].duration) - 1e-12) seg++;
      const sg = segments[seg];
      const st = starts[seg];
      const beta = Number(sg.duration) * scale * DEG;
      const u = Math.min(1, Math.max(0, (thScaled - st.ang) / Number(sg.duration)));
      if (sg.type === 'dwell' || !sg.type) {
        m.s[i] = st.h;
      } else {
        const dir = sg.type === 'rise' ? 1 : -1;
        const L = Number(sg.lift);
        const [ns, nv, na, nj] = (LAWS[sg.law] || LAWS.cycloidal).fn(u);
        m.s[i] = st.h + dir * L * ns;
        m.v[i] = (dir * L * nv) / beta;
        m.a[i] = (dir * L * na) / beta ** 2;
        m.j[i] = (dir * L * nj) / beta ** 3;
      }
    }
    m.issues = issues;
    m.lift = Math.max(...m.s) - Math.min(...m.s);
    return m;
  }

  /*
   * Build a motion from keyframes using boundary-condition polynomials.
   * keys: [{ theta: deg, s: mm, mode: 'stop'|'pass'|'free', v?: mm/rad }] sorted by
   *       theta, first at 0. The cycle closes back to keys[0] at 360.
   * spans: optional per-span overrides, spans[i] covers keys[i] -> keys[i+1]:
   *       { kind: 'auto'|'linear'|'law', law?: key }
   * order: 'quintic' (s,v,a matched) or 'septic' (s,v,a,j matched)
   */
  function fromKeyframes(keys, spans = [], opts = {}) {
    const n = opts.samples || 720;
    const order = opts.order || 'quintic';
    const K = keys.length;
    const pts = keys.map((k) => ({ ...k }));
    const span = (i) => spans[i] || { kind: 'auto' };
    const nextTheta = (i) => (i + 1 < K ? pts[i + 1].theta : 360);
    const nextS = (i) => pts[(i + 1) % K].s;
    const slope = (i) => (nextS(i) - pts[i].s) / ((nextTheta(i) - pts[i].theta) * DEG);

    // Resolve velocity at each key (mm/rad) and acceleration (mm/rad^2, always 0
    // except where a linear span forces it).
    const vel = new Array(K).fill(0);
    for (let i = 0; i < K; i++) {
      const prev = (i - 1 + K) % K;
      const inLinear = span(prev).kind === 'linear';
      const outLinear = span(i).kind === 'linear';
      if (outLinear) vel[i] = slope(i);
      else if (inLinear) vel[i] = slope(prev);
      else if (pts[i].mode === 'pass') {
        const sIn = slope(prev);
        const sOut = slope(i);
        // Monotone through-point: harmonic-mean slope keeps the curve from overshooting.
        vel[i] = sIn * sOut > 0 ? (2 * sIn * sOut) / (sIn + sOut) : 0;
      } else if (pts[i].mode === 'free' && Number.isFinite(pts[i].v)) vel[i] = pts[i].v;
      else vel[i] = 0;
    }

    const m = emptyMotion(n);
    const polys = [];
    for (let i = 0; i < K; i++) {
      const th0 = pts[i].theta;
      const th1 = nextTheta(i);
      const beta = (th1 - th0) * DEG;
      const sp = span(i);
      const s0 = pts[i].s;
      const s1 = nextS(i);
      if (sp.kind === 'linear') {
        polys.push({ th0, th1, beta, kind: 'linear', s0, s1 });
      } else if (sp.kind === 'law' && LAWS[sp.law] && Math.abs(vel[i]) < EPS && Math.abs(vel[(i + 1) % K]) < EPS) {
        polys.push({ th0, th1, beta, kind: 'law', law: sp.law, s0, s1 });
      } else {
        const v0 = vel[i] * beta;
        const v1 = vel[(i + 1) % K] * beta;
        const bc0 = order === 'septic' ? [s0, v0, 0, 0] : [s0, v0, 0];
        const bc1 = order === 'septic' ? [s1, v1, 0, 0] : [s1, v1, 0];
        polys.push({ th0, th1, beta, kind: 'poly', c: bcPolynomial(bc0, bc1) });
      }
    }

    let p = 0;
    for (let i = 0; i <= n; i++) {
      const th = (360 * i) / n;
      m.theta[i] = th;
      while (p < polys.length - 1 && th >= polys[p].th1 - 1e-12) p++;
      const P = polys[p];
      const u = Math.min(1, Math.max(0, (th - P.th0) / (P.th1 - P.th0)));
      let y;
      if (P.kind === 'linear') y = [P.s0 + (P.s1 - P.s0) * u, P.s1 - P.s0, 0, 0];
      else if (P.kind === 'law') {
        const r = LAWS[P.law].fn(u);
        const L = P.s1 - P.s0;
        y = [P.s0 + L * r[0], L * r[1], L * r[2], L * r[3]];
      } else y = polyEval(P.c, u);
      m.s[i] = y[0];
      m.v[i] = y[1] / P.beta;
      m.a[i] = y[2] / P.beta ** 2;
      m.j[i] = y[3] / P.beta ** 3;
    }
    m.issues = [];
    const sMin = Math.min(...m.s);
    if (sMin < -1e-6) m.issues.push(`The curve dips ${(-sMin).toFixed(2)} mm below the base circle. Raise a key or use stops.`);
    m.lift = Math.max(...m.s) - sMin;
    m.keyVelocity = vel;
    m.spans = polys;
    return m;
  }

  function stats(m, rpm) {
    const w = (rpm * TAU) / 60;
    let sMax = -Infinity;
    let sMin = Infinity;
    let vMax = 0;
    let aMax = 0;
    let aMin = 0;
    let jMax = 0;
    for (let i = 0; i < m.s.length; i++) {
      sMax = Math.max(sMax, m.s[i]);
      sMin = Math.min(sMin, m.s[i]);
      vMax = Math.max(vMax, Math.abs(m.v[i]));
      aMax = Math.max(aMax, m.a[i]);
      aMin = Math.min(aMin, m.a[i]);
      jMax = Math.max(jMax, Math.abs(m.j[i]));
    }
    return {
      omega: w,
      lift: sMax - sMin,
      vPeak: vMax * w, // mm/s
      aPeak: Math.max(aMax, -aMin) * w * w, // mm/s^2
      aPos: aMax * w * w,
      aNeg: aMin * w * w,
      jPeak: jMax * w ** 3, // mm/s^3
    };
  }

  // ---------------------------------------------------------------------------
  // Follower geometry
  // ---------------------------------------------------------------------------

  /*
   * follower: {
   *   type: 'roller' | 'flat' | 'oscillating',
   *   rb: base circle radius (mm), rr: roller radius (mm),
   *   e: offset of translating follower axis (mm, positive to the right),
   *   arm: oscillating arm length (mm), pivot: cam-centre-to-pivot distance (mm)
   * }
   * Fixed frame: cam centre at origin, translating follower moves along +y.
   * Oscillating pivot sits at (pivot, 0); the arm swings the roller outward.
   *
   * Returns the pitch point P (roller centre), its derivatives in theta, and the
   * follower's unit direction of motion, all in the fixed frame.
   */
  function pitchFixed(f, s, v, a) {
    if (f.type === 'oscillating') {
      const L = f.arm;
      const C = f.pivot;
      const rp = f.rb + f.rr;
      const cos0 = (C * C + L * L - rp * rp) / (2 * C * L);
      const psi0 = Math.acos(Math.max(-1, Math.min(1, cos0)));
      const P = psi0 + s / L;
      const dP = v / L;
      const ddP = a / L;
      const sn = Math.sin(P);
      const cs = Math.cos(P);
      return {
        x: C - L * cs,
        y: L * sn,
        dx: L * sn * dP,
        dy: L * cs * dP,
        ddx: L * cs * dP * dP + L * sn * ddP,
        ddy: -L * sn * dP * dP + L * cs * ddP,
        mx: sn,
        my: cs,
        psi: P,
        pivot: [C, 0],
      };
    }
    const rp = f.type === 'flat' ? f.rb : f.rb + f.rr;
    const e = f.type === 'flat' ? 0 : f.e || 0;
    const d = Math.sqrt(Math.max(rp * rp - e * e, 0));
    return { x: e, y: d + s, dx: 0, dy: v, ddx: 0, ddy: a, mx: 0, my: 1, d };
  }

  // Rotate a fixed-frame point/vector into the cam frame for cam angle th (rad).
  function toCam(x, y, th) {
    const c = Math.cos(th);
    const s = Math.sin(th);
    return [x * c + y * s, -x * s + y * c];
  }

  function toFixed(x, y, th) {
    const c = Math.cos(th);
    const s = Math.sin(th);
    return [x * c - y * s, x * s + y * c];
  }

  /*
   * Full profile analysis.
   * Returns cam-frame curves plus per-sample pressure angle (deg) and radii of
   * curvature (positive = convex).
   */
  function profile(m, f) {
    const n = m.s.length;
    const out = {
      pitchX: new Float64Array(n),
      pitchY: new Float64Array(n),
      surfX: new Float64Array(n),
      surfY: new Float64Array(n),
      pressure: new Float64Array(n),
      rhoPitch: new Float64Array(n),
      rhoSurf: new Float64Array(n),
      radius: new Float64Array(n),
    };
    const flat = f.type === 'flat';
    for (let i = 0; i < n; i++) {
      const th = m.theta[i] * DEG;
      const s = m.s[i];
      const v = m.v[i];
      const a = m.a[i];
      if (flat) {
        // Contact sits v mm sideways from the follower axis; rho = Rb + s + s''.
        const [cx, cy] = toCam(v, f.rb + s, th);
        out.surfX[i] = cx;
        out.surfY[i] = cy;
        out.pitchX[i] = cx;
        out.pitchY[i] = cy;
        out.pressure[i] = 0;
        out.rhoSurf[i] = f.rb + s + a;
        out.rhoPitch[i] = out.rhoSurf[i];
        out.radius[i] = Math.hypot(cx, cy);
        continue;
      }
      const P = pitchFixed(f, s, v, a);
      const c = Math.cos(th);
      const sn = Math.sin(th);
      // Cam-frame pitch point Q = R(-th) P and its theta derivatives.
      const x = P.x * c + P.y * sn;
      const y = -P.x * sn + P.y * c;
      const dx = P.dx * c - P.x * sn + P.dy * sn + P.y * c;
      const dy = -P.dx * sn - P.x * c + P.dy * c - P.y * sn;
      const ddx = P.ddx * c - 2 * P.dx * sn - P.x * c + P.ddy * sn + 2 * P.dy * c - P.y * sn;
      const ddy = -P.ddx * sn - 2 * P.dx * c + P.x * sn + P.ddy * c - 2 * P.dy * sn - P.y * c;
      const tn = Math.hypot(dx, dy) || EPS;
      // The pitch curve is traced clockwise in the cam frame, so convex => cross < 0.
      const cross = dx * ddy - dy * ddx;
      const rho = -(tn ** 3) / (Math.abs(cross) < EPS ? (cross < 0 ? -EPS : EPS) : cross);
      // Inward normal (toward the cam material).
      let nx = -dy / tn;
      let ny = dx / tn;
      if (nx * x + ny * y > 0) {
        nx = -nx;
        ny = -ny;
      }
      out.pitchX[i] = x;
      out.pitchY[i] = y;
      out.surfX[i] = x + f.rr * nx;
      out.surfY[i] = y + f.rr * ny;
      out.rhoPitch[i] = rho;
      out.rhoSurf[i] = rho - f.rr;
      out.radius[i] = Math.hypot(out.surfX[i], out.surfY[i]);
      // Pressure angle: between the common normal and the follower's motion, both in the fixed frame.
      const [fnx, fny] = toFixed(-nx, -ny, th);
      const dot = fnx * P.mx + fny * P.my;
      const crs = P.mx * fny - P.my * fnx;
      out.pressure[i] = Math.atan2(crs, dot) / DEG;
    }
    return out;
  }

  /*
   * Design checks. Limits follow common practice (Norton, Rothbart):
   *   translating roller: |phi| <= 30 deg; oscillating: <= 35 deg
   *   convex pitch radius >= 1.5 x roller radius to avoid cusps and high stress
   *   flat-faced: rho > 0 everywhere; face width >= v range + margin
   */
  function checks(m, f, prof, limits = {}) {
    const phiLimit = limits.phi || (f.type === 'oscillating' ? 35 : 30);
    const rhoFactor = limits.rhoFactor || 1.5;
    let phiMax = 0;
    let phiAt = 0;
    let rhoMin = Infinity;
    let rhoAt = 0;
    let concaveMin = Infinity;
    let rMax = 0;
    let undercut = 0;
    for (let i = 0; i < prof.pressure.length; i++) {
      const ph = Math.abs(prof.pressure[i]);
      if (ph > phiMax) {
        phiMax = ph;
        phiAt = m.theta[i];
      }
      const r = f.type === 'flat' ? prof.rhoSurf[i] : prof.rhoPitch[i];
      if (r > 0 && r < rhoMin) {
        rhoMin = r;
        rhoAt = m.theta[i];
      }
      if (r < 0) concaveMin = Math.min(concaveMin, -prof.rhoSurf[i]);
      if (f.type === 'flat' ? r <= 0 : r > 0 && r < f.rr) undercut++;
      rMax = Math.max(rMax, prof.radius[i]);
    }
    let vMin = Infinity;
    let vMax = -Infinity;
    for (let i = 0; i < m.v.length; i++) {
      vMin = Math.min(vMin, m.v[i]);
      vMax = Math.max(vMax, m.v[i]);
    }
    const result = {
      phiMax,
      phiAt,
      phiLimit,
      phiOk: phiMax <= phiLimit,
      rhoMin,
      rhoAt,
      concaveMin,
      undercut: undercut > 0,
      rhoOk: f.type === 'flat' ? undercut === 0 : rhoMin >= rhoFactor * f.rr && undercut === 0,
      rhoFactor,
      rMax,
      faceMin: vMin,
      faceMax: vMax,
      faceWidth: vMax - vMin,
    };
    if (f.type === 'oscillating') {
      const rp = f.rb + f.rr;
      result.geometryOk = rp < f.pivot + f.arm && rp > Math.abs(f.pivot - f.arm);
    } else if (f.type === 'roller') {
      result.geometryOk = Math.abs(f.e || 0) < f.rb + f.rr;
    } else result.geometryOk = true;
    result.ok = result.phiOk && result.rhoOk && result.geometryOk;
    return result;
  }

  // Fast pressure/curvature scan for design-space maps (translating roller).
  function quickScan(m, rb, rr, e) {
    const rp = rb + rr;
    if (Math.abs(e) >= rp) return { phiMax: 90, rhoMin: 0, valid: false };
    const d = Math.sqrt(rp * rp - e * e);
    let phiMax = 0;
    let rhoMin = Infinity;
    for (let i = 0; i < m.s.length; i++) {
      const s = m.s[i];
      const v = m.v[i];
      const a = m.a[i];
      const phi = Math.abs(Math.atan2(v - e, d + s));
      if (phi > phiMax) phiMax = phi;
      // Pitch-curve radius of curvature for an offset translating follower (Norton eq. 8.33 form).
      const D = d + s;
      const num = (D * D + (v - e) ** 2) ** 1.5;
      const den = D * D + (v - e) * (2 * v - e) - a * D;
      const rho = num / den;
      if (rho > 0 && rho < rhoMin) rhoMin = rho;
    }
    return { phiMax: phiMax / DEG, rhoMin, valid: true };
  }

  // Follower pose for animation at sample index i (fixed frame).
  function pose(m, f, prof, i) {
    const th = m.theta[i] * DEG;
    const out = { theta: th, s: m.s[i] };
    if (f.type === 'flat') {
      out.faceY = f.rb + m.s[i];
      out.contact = [m.v[i], f.rb + m.s[i]];
      out.normal = [0, 1];
      return out;
    }
    const P = pitchFixed(f, m.s[i], m.v[i], m.a[i]);
    out.center = [P.x, P.y];
    out.motion = [P.mx, P.my];
    out.psi = P.psi;
    out.pivot = P.pivot;
    const [cx, cy] = toFixed(prof.surfX[i], prof.surfY[i], th);
    out.contact = [cx, cy];
    const nx = P.x - cx;
    const ny = P.y - cy;
    const nn = Math.hypot(nx, ny) || 1;
    out.normal = [nx / nn, ny / nn];
    return out;
  }

  // ---------------------------------------------------------------------------
  // Dynamics: force closure, jump, torque
  // ---------------------------------------------------------------------------

  /*
   * Contact force for a spring-loaded translating follower.
   *   F_c = m a + c v + F0 + k s + F_ext
   * mass kg, k N/mm, preload N, damping N·s/m, external N (pushes toward cam).
   * Returns arrays in N and N·m, plus the jump speed in rpm.
   */
  function dynamics(m, p) {
    const w = (p.rpm * TAU) / 60;
    const n = m.s.length;
    const force = new Float64Array(n);
    const spring = new Float64Array(n);
    const inertia = new Float64Array(n);
    const torque = new Float64Array(n);
    let fMin = Infinity;
    let fMinAt = 0;
    let fMax = -Infinity;
    let tMax = 0;
    let tMin = 0;
    let tSq = 0;
    for (let i = 0; i < n; i++) {
      const acc = (m.a[i] * w * w) / 1000; // m/s^2
      const vel = (m.v[i] * w) / 1000; // m/s
      spring[i] = p.preload + p.k * m.s[i] + (p.external || 0);
      inertia[i] = p.mass * acc + (p.damping || 0) * vel;
      force[i] = spring[i] + inertia[i];
      torque[i] = (force[i] * m.v[i]) / 1000; // N * m/rad = N·m (pressure-angle friction ignored)
      if (force[i] < fMin) {
        fMin = force[i];
        fMinAt = m.theta[i];
      }
      fMax = Math.max(fMax, force[i]);
      tMax = Math.max(tMax, torque[i]);
      tMin = Math.min(tMin, torque[i]);
      if (i < n - 1) tSq += torque[i] * torque[i];
    }
    // Jump speed: smallest omega where min(F) hits zero. F is quadratic in omega per sample.
    let jumpW = Infinity;
    for (let i = 0; i < n; i++) {
      const A = (p.mass * m.a[i]) / 1000;
      const B = ((p.damping || 0) * m.v[i]) / 1000;
      const C = p.preload + p.k * m.s[i] + (p.external || 0);
      if (C <= 0) {
        jumpW = 0;
        break;
      }
      if (A < 0) {
        const disc = B * B - 4 * A * C;
        const root = (-B - Math.sqrt(disc)) / (2 * A);
        if (root > 0) jumpW = Math.min(jumpW, root);
      }
    }
    // Energy fluctuation for flywheel sizing: max swing of integral(T - Tmean) dtheta.
    let tMean = 0;
    for (let i = 0; i < n - 1; i++) tMean += torque[i];
    tMean /= n - 1;
    let e = 0;
    let eMax = 0;
    let eMin = 0;
    const dth = TAU / (n - 1);
    for (let i = 0; i < n - 1; i++) {
      e += (torque[i] - tMean) * dth;
      eMax = Math.max(eMax, e);
      eMin = Math.min(eMin, e);
    }
    return {
      force,
      spring,
      inertia,
      torque,
      fMin,
      fMinAt,
      fMax,
      tPeak: Math.max(tMax, -tMin),
      tRms: Math.sqrt(tSq / (n - 1)),
      powerPeak: Math.max(tMax, -tMin) * w,
      jumpRpm: (jumpW * 60) / TAU,
      deltaE: eMax - eMin,
      omega: w,
    };
  }

  /*
   * Smallest spring (k, preload) that keeps contact at the given speed with a
   * safety factor, minimizing the peak spring force. Linear program in (k, F0),
   * solved by scanning k because the objective is convex piecewise-linear in k.
   */
  function sizeSpring(m, mass, rpm, sf = 1.5, external = 0) {
    const w = (rpm * TAU) / 60;
    const need = Array.from(m.a, (a) => Math.max(0, (-sf * mass * a * w * w) / 1000) - external);
    const sMax = Math.max(...m.s);
    const preloadFor = (k) => Math.max(0, ...need.map((g, i) => g - k * m.s[i]));
    const kHi = sMax > 0 ? Math.max(...need) / Math.max(sMax * 0.05, 1e-6) : 0;
    let best = { k: 0, preload: preloadFor(0) };
    best.peak = best.preload;
    const steps = 400;
    for (let t = 1; t <= steps; t++) {
      const k = (kHi * t) / steps;
      const F0 = preloadFor(k);
      const peak = F0 + k * sMax;
      if (peak < best.peak - 1e-9) best = { k, preload: F0, peak };
    }
    // A practical spring always has some rate; enforce a floor of 5% of the peak force over the lift.
    if (best.k === 0 && sMax > 0) {
      const k = (0.05 * best.peak) / sMax;
      best = { k, preload: preloadFor(k), peak: preloadFor(k) + k * sMax };
    }
    return best;
  }

  // ---------------------------------------------------------------------------
  // Residual vibration of a single-degree-of-freedom follower after a rise
  // ---------------------------------------------------------------------------

  /*
   * Relative coordinate e = x - s obeys e'' + 2 zeta wn e' + wn^2 e = -s''(t).
   * ratio = rise time / natural period. Returns residual amplitude / lift.
   */
  function residual(lawKey, ratio, zeta = 0) {
    const fn = LAWS[lawKey].fn;
    const T = 1; // rise time (normalized)
    const wn = (TAU * ratio) / T;
    const steps = Math.max(400, Math.ceil(ratio * 80));
    const h = T / steps;
    let e = 0;
    let de = 0;
    const acc = (t) => fn(Math.min(1, Math.max(0, t / T)))[2] / (T * T);
    const f = (t, y0, y1) => [y1, -acc(t) - 2 * zeta * wn * y1 - wn * wn * y0];
    for (let k = 0; k < steps; k++) {
      const t = k * h;
      const k1 = f(t, e, de);
      const k2 = f(t + h / 2, e + (h / 2) * k1[0], de + (h / 2) * k1[1]);
      const k3 = f(t + h / 2, e + (h / 2) * k2[0], de + (h / 2) * k2[1]);
      const k4 = f(t + h, e + h * k3[0], de + h * k3[1]);
      e += (h / 6) * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0]);
      de += (h / 6) * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1]);
    }
    const wd = wn * Math.sqrt(Math.max(1 - zeta * zeta, 1e-9));
    return Math.sqrt(e * e + ((de + zeta * wn * e) / wd) ** 2);
  }

  // ---------------------------------------------------------------------------
  // Export helpers
  // ---------------------------------------------------------------------------

  // Adaptive resample so the chord sag stays under tol (mm).
  function resample(xs, ys, tol = 0.01, closed = true) {
    const n = xs.length - (closed ? 1 : 0);
    const out = [[xs[0], ys[0]]];
    let last = 0;
    for (let i = 1; i < n; i++) {
      // Max distance of intermediate points from the chord last -> i+1
      const ax = xs[last];
      const ay = ys[last];
      const bx = xs[i + 1 < xs.length ? i + 1 : 0];
      const by = ys[i + 1 < ys.length ? i + 1 : 0];
      const L = Math.hypot(bx - ax, by - ay) || EPS;
      let dev = 0;
      for (let k = last + 1; k <= i; k++) {
        const d = Math.abs((bx - ax) * (ay - ys[k]) - (ax - xs[k]) * (by - ay)) / L;
        if (d > dev) dev = d;
      }
      if (dev > tol) {
        out.push([xs[i], ys[i]]);
        last = i;
      }
    }
    if (!closed) out.push([xs[xs.length - 1], ys[ys.length - 1]]);
    return out;
  }

  function toDXF(polylines, extraEntities = []) {
    // polylines: [{ layer, points: [[x,y],...], closed }]. R12 LINE entities for portability.
    // extraEntities: pre-built entity strings such as dxfCircle() output.
    const L = ['0', 'SECTION', '2', 'HEADER', '9', '$INSUNITS', '70', '4', '0', 'ENDSEC', '0', 'SECTION', '2', 'ENTITIES'];
    polylines.forEach((pl) => {
      const pts = pl.points;
      const count = pl.closed ? pts.length : pts.length - 1;
      for (let i = 0; i < count; i++) {
        const a = pts[i];
        const b = pts[(i + 1) % pts.length];
        L.push('0', 'LINE', '8', pl.layer || '0', '10', a[0].toFixed(4), '20', a[1].toFixed(4), '30', '0', '11', b[0].toFixed(4), '21', b[1].toFixed(4), '31', '0');
      }
    });
    extraEntities.forEach((ent) => L.push(ent));
    L.push('0', 'ENDSEC', '0', 'EOF');
    return L.join('\n');
  }

  function dxfCircle(cx, cy, r, layer = '0') {
    return ['0', 'CIRCLE', '8', layer, '10', cx.toFixed(4), '20', cy.toFixed(4), '30', '0', '40', r.toFixed(4)].join('\n');
  }

  function presetSegments(key) {
    const P = {
      drdr: [
        { type: 'rise', duration: 120, lift: 20, law: 'cycloidal' },
        { type: 'dwell', duration: 60 },
        { type: 'fall', duration: 120, lift: 20, law: 'cycloidal' },
        { type: 'dwell', duration: 60 },
      ],
      rrr: [
        { type: 'rise', duration: 150, lift: 18, law: 'modified_sine' },
        { type: 'fall', duration: 150, lift: 18, law: 'modified_sine' },
        { type: 'dwell', duration: 60 },
      ],
      indexer: [
        { type: 'rise', duration: 90, lift: 25, law: 'modified_trapezoid' },
        { type: 'dwell', duration: 150 },
        { type: 'fall', duration: 90, lift: 25, law: 'modified_trapezoid' },
        { type: 'dwell', duration: 30 },
      ],
      valve: [
        { type: 'dwell', duration: 110 },
        { type: 'rise', duration: 70, lift: 10, law: 'poly4567' },
        { type: 'fall', duration: 70, lift: 10, law: 'poly4567' },
        { type: 'dwell', duration: 110 },
      ],
    };
    return JSON.parse(JSON.stringify(P[key] || P.drdr));
  }

  global.CamCore = {
    TAU,
    DEG,
    LAWS,
    lawCoefficients,
    bcPolynomial,
    polyEval,
    fromSegments,
    fromKeyframes,
    stats,
    profile,
    checks,
    quickScan,
    pose,
    pitchFixed,
    toCam,
    toFixed,
    dynamics,
    sizeSpring,
    residual,
    resample,
    toDXF,
    dxfCircle,
    presetSegments,
  };
})(typeof window !== 'undefined' ? window : globalThis);
