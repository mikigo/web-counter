/**
 * web-counter frontend script
 *
 * Automatically discovers API base URL, scans DOM for data-* attributes,
 * reports visits and fills in count values. Silently fails on any error.
 * Supports SPA client-side navigation via MutationObserver.
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

  // --- Helpers ---
  function fmt(n) {
    return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  }

  function find(attr) {
    var el = document.querySelector("[" + attr + "]");
    return el || null;
  }

  function getStyleName() {
    return (
      (document.querySelector("[data-counter-style]") || {}).getAttribute("data-counter-style") || "default"
    );
  }

  function applyStyle(container, styleName) {
    if (!container || !container.tagName) return;
    var styles = {
      badge: "display:inline-block;background:#f0f0f0;border-radius:12px;padding:2px 8px;font-size:13px;",
      card: "display:inline-block;background:#fff;border-radius:6px;box-shadow:0 1px 4px rgba(0,0,0,0.1);padding:12px 16px;font-size:14px;",
      bordered: "display:inline-block;border:1px solid #e0e0e0;border-radius:3px;padding:4px 10px;font-size:13px;",
      default: "display:inline-block;",
    };
    container.style.cssText = styles[styleName] || styles["default"];
  }

  function findContainer(el) {
    // Walk up to find display:none container
    var p = el.parentElement;
    while (p) {
      if (p.style && p.style.display === "none") return p;
      p = p.parentElement;
    }
    return el;
  }

  // --- Main refresh logic (called on load + SPA navigation) ---
  function refresh() {
    var counters = {};
    counters.pvToday = find("data-pv-today");
    counters.uvToday = find("data-uv-today");
    counters.pvSite = find("data-pv-site");
    counters.uvSite = find("data-uv-site");
    counters.pvPage = find("data-pv-page");

    var paths = [];
    if (counters.pvPage) {
      paths.push(counters.pvPage.getAttribute("data-pv-page") || window.location.pathname);
    }
    document.querySelectorAll("[data-pv-page]").forEach(function (el) {
      var p = el.getAttribute("data-pv-page") || window.location.pathname;
      if (paths.indexOf(p) === -1) paths.push(p);
    });

    var styleName = getStyleName();

    try {
      var xhrVisit = new XMLHttpRequest();
      xhrVisit.open("POST", apiBase + "/api/visit", true);
      xhrVisit.setRequestHeader("Content-Type", "application/json");
      xhrVisit.timeout = 3000;
      xhrVisit.send(JSON.stringify({ path: window.location.pathname }));

      var xhrCount = new XMLHttpRequest();
      xhrCount.open("GET", apiBase + "/api/count?paths=" + encodeURIComponent(paths.join(",")), true);
      xhrCount.timeout = 3000;
      xhrCount.onload = function () {
        if (xhrCount.status !== 200) return;
        try {
          var d = JSON.parse(xhrCount.responseText);
          if (counters.pvToday) counters.pvToday.textContent = fmt(d.today_pv);
          if (counters.uvToday) counters.uvToday.textContent = fmt(d.today_uv);
          if (counters.pvSite) counters.pvSite.textContent = fmt(d.site_pv);
          if (counters.uvSite) counters.uvSite.textContent = fmt(d.site_uv);
          if (counters.pvPage && d.pages) {
            var pvKey = counters.pvPage.getAttribute("data-pv-page") || window.location.pathname;
            if (d.pages[pvKey] !== undefined) counters.pvPage.textContent = fmt(d.pages[pvKey]);
          }
          // Make all counter containers visible
          var allEls = [counters.pvToday, counters.uvToday, counters.pvSite, counters.uvSite, counters.pvPage];
          var seen = {};
          for (var i = 0; i < allEls.length; i++) {
            var el = allEls[i];
            if (!el) continue;
            var container = findContainer(el);
            if (!container || seen[container._wcId]) continue;
            container._wcId = 1; seen[container._wcId] = true;
            var s = (container.getAttribute && container.getAttribute("data-counter-style")) || "default";
            applyStyle(container, s);
          }
        } catch (e) { /* silent */ }
      };
      xhrCount.send();
    } catch (e) { /* silent */ }
  }

  // --- Initial run ---
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", refresh);
  } else {
    refresh();
  }

  // --- SPA support: watch for re-rendered counter elements ---
  if (typeof MutationObserver !== "undefined") {
    var debounce = null;
    var observer = new MutationObserver(function (mutations) {
      for (var i = 0; i < mutations.length; i++) {
        var added = mutations[i].addedNodes;
        for (var j = 0; j < added.length; j++) {
          var node = added[j];
          if (node.nodeType === 1) {
            // Check if added subtree contains counter elements
            if (node.hasAttribute && (
              node.hasAttribute("data-pv-today") || node.hasAttribute("data-uv-today") ||
              node.hasAttribute("data-pv-site") || node.hasAttribute("data-uv-site") ||
              node.hasAttribute("data-pv-page")
            )) {
              clearTimeout(debounce);
              debounce = setTimeout(refresh, 150);
              return;
            }
            if (node.querySelectorAll) {
              var found = node.querySelectorAll("[data-pv-today],[data-pv-site],[data-uv-today],[data-uv-site],[data-pv-page]");
              if (found.length > 0) {
                clearTimeout(debounce);
                debounce = setTimeout(refresh, 150);
                return;
              }
            }
          }
        }
      }
    });
    observer.observe(document.documentElement, { childList: true, subtree: true });
  }
})();
