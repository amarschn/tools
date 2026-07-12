/*
 * verdict.js — reusable pass/fail verdict banner for decision tools.
 *
 * Renders a single, prominent PASS / MARGINAL / FAIL banner above a tool's
 * detailed results, following the progressive-disclosure principle
 * (verdict -> why -> numbers). Dependency-free and self-contained: it injects
 * its own scoped styles once, so it looks consistent regardless of the host
 * tool's CSS, in both light and dark themes.
 *
 * Usage:
 *   <script src="/shared/verdict.js"></script>
 *   TransparentVerdict.render(containerEl, {
 *     status: "pass" | "marginal" | "fail",
 *     headline: "8 AWG copper, 40 A breaker, VD 2.5%",
 *     bindingConstraint: "voltage_drop",     // optional, human-readable-ized
 *     reasons: ["..."],                        // optional, shown for marginal/fail
 *     checks: { "Ampacity": true, "Voltage drop": false, ... }  // optional chips
 *   });
 */
(function () {
  "use strict";

  var STYLE_ID = "transparent-verdict-styles";

  var CSS = `
.tv-verdict{border-radius:12px;padding:18px 20px;margin:0 0 20px;color:#fff;
  font-family:inherit;box-shadow:0 2px 10px rgba(0,0,0,.15)}
.tv-verdict--pass{background:#0f766e}
.tv-verdict--marginal{background:#b45309}
.tv-verdict--fail{background:#b91c1c}
.tv-verdict__top{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.tv-verdict__badge{font-weight:800;letter-spacing:.06em;text-transform:uppercase;
  font-size:.78rem;background:rgba(255,255,255,.22);padding:4px 10px;border-radius:999px}
.tv-verdict__headline{font-size:1.05rem;font-weight:600;line-height:1.35}
.tv-verdict__binding{margin-top:8px;font-size:.85rem;opacity:.9}
.tv-verdict__reasons{margin:12px 0 0;padding-left:18px;font-size:.88rem;line-height:1.5}
.tv-verdict__reasons li{margin:2px 0}
.tv-verdict__checks{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}
.tv-chip{display:inline-flex;align-items:center;gap:6px;background:rgba(255,255,255,.16);
  padding:4px 10px;border-radius:999px;font-size:.8rem;font-weight:600}
.tv-chip__mark{font-weight:800}
`;

  function ensureStyles() {
    if (document.getElementById(STYLE_ID)) return;
    var s = document.createElement("style");
    s.id = STYLE_ID;
    s.textContent = CSS;
    document.head.appendChild(s);
  }

  function esc(str) {
    return String(str).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function humanize(key) {
    return String(key).replace(/_/g, " ").replace(/\b\w/g, function (m) {
      return m.toUpperCase();
    });
  }

  function badgeText(status) {
    return status === "pass" ? "Pass" : status === "marginal" ? "Marginal" : "Fail";
  }

  function render(container, v) {
    if (!container) return;
    ensureStyles();
    var status = (v.status || "fail").toLowerCase();

    var checksHtml = "";
    if (v.checks && Object.keys(v.checks).length) {
      checksHtml = '<div class="tv-verdict__checks">' +
        Object.keys(v.checks).map(function (name) {
          var ok = v.checks[name];
          return '<span class="tv-chip"><span class="tv-chip__mark">' +
            (ok ? "✓" : "✗") + "</span>" + esc(humanize(name)) + "</span>";
        }).join("") + "</div>";
    }

    var reasonsHtml = "";
    if (v.reasons && v.reasons.length && status !== "pass") {
      reasonsHtml = '<ul class="tv-verdict__reasons">' +
        v.reasons.map(function (r) { return "<li>" + esc(r) + "</li>"; }).join("") +
        "</ul>";
    }

    var bindingHtml = v.bindingConstraint
      ? '<div class="tv-verdict__binding">Governing constraint: ' +
        esc(humanize(v.bindingConstraint)) + "</div>"
      : "";

    container.innerHTML =
      '<div class="tv-verdict tv-verdict--' + status + '" role="status">' +
        '<div class="tv-verdict__top">' +
          '<span class="tv-verdict__badge">' + badgeText(status) + "</span>" +
          '<span class="tv-verdict__headline">' + esc(v.headline || "") + "</span>" +
        "</div>" +
        bindingHtml +
        reasonsHtml +
        checksHtml +
      "</div>";
  }

  window.TransparentVerdict = { render: render };
})();
