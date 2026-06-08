/**
 * web-counter frontend script (~1KB)
 *
 * Automatically discovers API base URL, scans DOM for data-* attributes,
 * reports visits and fills in count values. Silently fails on any error.
 */
(function () {
  "use strict";

  // --- API base URL discovery ---
  var scriptTag = document.currentScript;
  var apiBase =
    scriptTag.getAttribute("data-counter-api") ||
    (function () {
      var src = scriptTag.src;
      return src.substring(0, src.lastIndexOf("/"));
    })();

  // --- DOM scanning ---
  var counters = {};
  var paths = [];

  function find(attr) {
    var el = document.querySelector("[" + attr + "]");
    return el || null;
  }

  counters.pvToday = find("data-pv-today");
  counters.uvToday = find("data-uv-today");
  counters.pvSite = find("data-pv-site");
  counters.uvSite = find("data-uv-site");
  counters.pvPage = find("data-pv-page");

  if (counters.pvPage) {
    paths.push(
      counters.pvPage.getAttribute("data-pv-page") || window.location.pathname
    );
  }

  // Collect all unique paths from data-pv-page elements
  document.querySelectorAll("[data-pv-page]").forEach(function (el) {
    var p = el.getAttribute("data-pv-page") || window.location.pathname;
    if (paths.indexOf(p) === -1) paths.push(p);
  });

  // --- Helpers ---
  function fmt(n) {
    return n
      .toString()
      .replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  }

  function show(el, v) {
    if (el) el.textContent = fmt(v);
  }

  function applyStyle(styleName) {
    var container = document.querySelector(".counter-container");
    if (!container) {
      // Find first counter parent that's hidden
      var firstEl =
        counters.pvToday ||
        counters.uvToday ||
        counters.pvSite ||
        counters.uvSite ||
        counters.pvPage;
      if (firstEl) {
        // Walk up to find display:none container
        var p = firstEl.parentElement;
        while (p) {
          if (p.style && p.style.display === "none") {
            container = p;
            break;
          }
          p = p.parentElement;
        }
      }
    }

    if (!container && firstEl) container = firstEl;

    if (!container) return;

    var styles = {
      badge:
        "display:inline-block;background:#f0f0f0;border-radius:12px;padding:2px 8px;font-size:13px;",
      card: "display:inline-block;background:#fff;border-radius:6px;box-shadow:0 1px 4px rgba(0,0,0,0.1);padding:12px 16px;font-size:14px;",
      bordered:
        "display:inline-block;border:1px solid #e0e0e0;border-radius:3px;padding:4px 10px;font-size:13px;",
      default: "display:inline-block;",
    };

    var s = styles[styleName] || styles["default"];
    if (container.tagName) {
      container.style.cssText = s;
    }
  }

  var styleName =
    (
      document.querySelector("[data-counter-style]") || {}
    ).getAttribute("data-counter-style") || "default";

  // --- API calls ---
  function send() {
    try {
      var xhrVisit = new XMLHttpRequest();
      xhrVisit.open("POST", apiBase + "/api/visit", true);
      xhrVisit.setRequestHeader("Content-Type", "application/json");
      xhrVisit.timeout = 3000;
      xhrVisit.send(JSON.stringify({ path: window.location.pathname }));

      var xhrCount = new XMLHttpRequest();
      xhrCount.open(
        "GET",
        apiBase + "/api/count?paths=" + encodeURIComponent(paths.join(",")),
        true
      );
      xhrCount.timeout = 3000;
      xhrCount.onload = function () {
        if (xhrCount.status !== 200) return;
        try {
          var d = JSON.parse(xhrCount.responseText);
          show(counters.pvToday, d.today_pv);
          show(counters.uvToday, d.today_uv);
          show(counters.pvSite, d.site_pv);
          show(counters.uvSite, d.site_uv);
          if (counters.pvPage && d.pages) {
            var pvKey =
              counters.pvPage.getAttribute("data-pv-page") ||
              window.location.pathname;
            if (d.pages[pvKey] !== undefined) show(counters.pvPage, d.pages[pvKey]);
          }
          applyStyle(styleName);
        } catch (e) {
          /* silent */
        }
      };
      xhrCount.send();
    } catch (e) {
      /* silent */
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", send);
  } else {
    send();
  }
})();
