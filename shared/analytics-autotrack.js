/*
 * analytics-autotrack.js — zero-config GA4 demand instrumentation.
 *
 * Fires a GA4 `export_action` event when a user clicks anything that looks like
 * an export / download / copy control. This gives us a demand signal for which
 * tools people would pay to get an artifact out of — without touching each
 * tool's own JS.
 *
 * No-op when gtag is absent (e.g. local dev), so it is always safe to include.
 * Match an element explicitly with `data-track="export"` to override heuristics.
 */
(function () {
  "use strict";

  // Words that signal "the user is trying to get an artifact out".
  var SIGNAL = /(export|download|\.csv|csv|xlsx|excel|\.pdf|pdf|copy|save\b)/i;

  function toolSlug() {
    var m = window.location.pathname.match(/\/tools\/([^/]+)\//);
    return m ? m[1] : "unknown";
  }

  function describe(el) {
    // Prefer an explicit label, then visible text, then id/class.
    var label =
      el.getAttribute("data-track-label") ||
      (el.textContent || "").trim().slice(0, 60) ||
      el.id ||
      el.className;
    return (label || "unlabeled").toString();
  }

  function looksExporty(el) {
    if (el.getAttribute("data-track") === "export") return true;
    if (el.getAttribute("data-track") === "off") return false;
    var hay = [
      el.id,
      el.className,
      el.getAttribute("aria-label") || "",
      el.getAttribute("download") != null ? "download" : "",
      (el.textContent || "").slice(0, 80),
    ].join(" ");
    return SIGNAL.test(hay);
  }

  document.addEventListener(
    "click",
    function (evt) {
      if (typeof window.gtag !== "function") return;
      var el = evt.target;
      // Walk up to the nearest button/anchor so clicks on inner spans count.
      while (el && el !== document.body) {
        if (el.tagName === "BUTTON" || el.tagName === "A" ||
            el.getAttribute && el.getAttribute("data-track")) {
          if (looksExporty(el)) {
            window.gtag("event", "export_action", {
              tool: toolSlug(),
              control: describe(el),
            });
          }
          return;
        }
        el = el.parentElement;
      }
    },
    true
  );
})();
