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

  function getStyleName(el) {
    el = el || document.querySelector("[data-counter-style]");
    return (el && el.getAttribute) ? (el.getAttribute("data-counter-style") || "default") : "default";
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

  // --- State ---
  var _lastRefresh = 0;
  var _lastPath = "";

  // --- Main refresh logic (called on load + SPA navigation) ---
  function refresh() {
    // Cooldown: prevent double-trigger from MutationObserver + DOMContentLoaded
    var now = Date.now();
    if (now - _lastRefresh < 800) return;
    _lastRefresh = now;

    var currentPath = window.location.pathname;

    // Only record visit if path actually changed (dedupe navigation events)
    var isNewPage = currentPath !== _lastPath;

    var counters = {};
    counters.pvToday = find("data-pv-today");
    counters.uvToday = find("data-uv-today");
    counters.pvSite = find("data-pv-site");
    counters.uvSite = find("data-uv-site");
    counters.pvPage = find("data-pv-page");

    // Collect page paths for count query
    var pagePaths = [];
    document.querySelectorAll("[data-pv-page]").forEach(function (el) {
      var p = el.getAttribute("data-pv-page") || currentPath;
      if (p && pagePaths.indexOf(p) === -1) pagePaths.push(p);
    });
    // Fallback: always include current page path
    if (pagePaths.length === 0 && counters.pvPage) {
      pagePaths.push(currentPath);
    }

    // Cache the path used for pvPage lookup
    var pvPageKey = counters.pvPage
      ? (counters.pvPage.getAttribute("data-pv-page") || currentPath)
      : "";

    // --- Query count and update DOM ---
    function fetchCount() {
      try {
        var xhrCount = new XMLHttpRequest();
        xhrCount.open("GET", apiBase + "/api/count?paths=" + encodeURIComponent(pagePaths.join(",")), true);
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
              if (d.pages[pvPageKey] !== undefined) {
                counters.pvPage.textContent = fmt(d.pages[pvPageKey]);
              }
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

    // If new page, send visit first then query count (ensures count includes this visit)
    if (isNewPage) {
      try {
        var xhrVisit = new XMLHttpRequest();
        xhrVisit.open("POST", apiBase + "/api/visit", true);
        xhrVisit.setRequestHeader("Content-Type", "application/json");
        xhrVisit.timeout = 3000;
        xhrVisit.onloadend = function () { fetchCount(); };
        xhrVisit.send(JSON.stringify({ path: currentPath, title: document.title }));
        _lastPath = currentPath;
      } catch (e) { /* silent */ }
    } else {
      fetchCount();
    }
  }

  // --- Top pages widget (data-pv-top) ---
  function loadTopWidget() {
    var lists = document.querySelectorAll("[data-pv-top]");
    lists.forEach(function (list) {
      var limit = parseInt(list.getAttribute("data-pv-top")) || 10;
      list.style.display = "none";
      try {
        var xhr = new XMLHttpRequest();
        xhr.open("GET", apiBase + "/api/top?limit=" + limit, true);
        xhr.timeout = 3000;
        xhr.onload = function () {
          if (xhr.status !== 200) return;
          try {
            var pages = JSON.parse(xhr.responseText);
            var html = "";
            pages.forEach(function (p, i) {
              html += "<li><a href=\"" + p.path + "\">" + (p.title || p.path) + "</a> <span>(" + fmt(p.count) + ")</span></li>";
            });
            list.innerHTML = html;
            list.style.display = "";
          } catch (e) { /* silent */ }
        };
        xhr.send();
      } catch (e) { /* silent */ }
    });
  }

  // --- Initial run ---
  function init() {
    refresh();
    loadTopWidget();
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
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
            if (node.hasAttribute && (
              node.hasAttribute("data-pv-today") || node.hasAttribute("data-uv-today") ||
              node.hasAttribute("data-pv-site") || node.hasAttribute("data-uv-site") ||
              node.hasAttribute("data-pv-page")
            )) {
              clearTimeout(debounce);
              debounce = setTimeout(function () { refresh(); loadTopWidget(); }, 150);
              return;
            }
            if (node.querySelectorAll) {
              var found = node.querySelectorAll("[data-pv-today],[data-pv-site],[data-uv-today],[data-uv-site],[data-pv-page]");
              if (found.length > 0) {
                clearTimeout(debounce);
                debounce = setTimeout(function () { refresh(); loadTopWidget(); }, 150);
                return;
              }
            }
            // Also check for top widget re-render
            if (node.hasAttribute && node.hasAttribute("data-pv-top")) {
              clearTimeout(debounce);
              debounce = setTimeout(function () { refresh(); loadTopWidget(); }, 150);
              return;
            }
            if (node.querySelectorAll) {
              var foundTop = node.querySelectorAll("[data-pv-top]");
              if (foundTop.length > 0) {
                clearTimeout(debounce);
                debounce = setTimeout(function () { refresh(); loadTopWidget(); }, 150);
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
