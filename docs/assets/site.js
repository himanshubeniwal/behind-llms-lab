// Behind the Secrets of LLMs, lab website: theme, menu, copy buttons, tabs, table of contents.
(function () {
  "use strict";
  var store = {
    get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) { /* private mode */ } }
  };

  // ---- dark / light
  var themeBtn = document.querySelector(".theme-toggle");
  if (themeBtn) {
    themeBtn.addEventListener("click", function () {
      var next = document.documentElement.dataset.theme === "light" ? "dark" : "light";
      document.documentElement.dataset.theme = next;
      store.set("theme", next);
    });
  }

  // ---- menu on small screens
  var navBtn = document.querySelector(".nav-toggle"), nav = document.getElementById("nav");
  if (navBtn && nav) {
    navBtn.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      navBtn.setAttribute("aria-expanded", String(open));
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && nav.classList.contains("open")) {
        nav.classList.remove("open");
        navBtn.setAttribute("aria-expanded", "false");
        navBtn.focus();
      }
    });
  }

  // ---- copy buttons
  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) return navigator.clipboard.writeText(text);
    return new Promise(function (resolve, reject) {
      var ta = document.createElement("textarea");
      ta.value = text; ta.style.position = "fixed"; ta.style.opacity = "0";
      document.body.appendChild(ta); ta.select();
      try { document.execCommand("copy") ? resolve() : reject(); } catch (e) { reject(e); }
      ta.remove();
    });
  }
  document.addEventListener("click", function (e) {
    var btn = e.target.closest(".copy");
    if (!btn) return;
    var code = btn.closest(".code").querySelector("pre");
    copyText(code.textContent.replace(/\n$/, "")).then(function () {
      btn.textContent = "Copied"; btn.classList.add("done");
      setTimeout(function () { btn.textContent = "Copy"; btn.classList.remove("done"); }, 1600);
    }, function () { btn.textContent = "Select and copy by hand"; });
  });

  // ---- tabs
  document.querySelectorAll("[data-tabs]").forEach(function (box) {
    var tabs = Array.prototype.slice.call(box.querySelectorAll('[role="tab"]'));
    function select(tab, focus) {
      tabs.forEach(function (t) {
        var on = t === tab;
        t.setAttribute("aria-selected", String(on));
        t.tabIndex = on ? 0 : -1;
        document.getElementById(t.getAttribute("aria-controls")).hidden = !on;
      });
      if (focus) tab.focus();
    }
    tabs.forEach(function (tab, i) {
      tab.addEventListener("click", function () { select(tab); });
      tab.addEventListener("keydown", function (e) {
        if (e.key === "ArrowRight") select(tabs[(i + 1) % tabs.length], true);
        if (e.key === "ArrowLeft") select(tabs[(i - 1 + tabs.length) % tabs.length], true);
      });
    });
    select(tabs[0]);
  });

  // ---- table of contents: mark the section you are reading
  var tocLinks = Array.prototype.slice.call(document.querySelectorAll(".toc a"));
  if (tocLinks.length) {
    var heads = tocLinks.map(function (a) { return document.getElementById(a.getAttribute("href").slice(1)); });
    var ticking = false;
    var mark = function () {
      ticking = false;
      var current = 0;
      heads.forEach(function (h, i) { if (h && h.getBoundingClientRect().top < 140) current = i; });
      tocLinks.forEach(function (a, i) { a.classList.toggle("active", i === current); });
    };
    window.addEventListener("scroll", function () {
      if (!ticking) { ticking = true; requestAnimationFrame(mark); }
    }, { passive: true });
    mark();
  }

  // ---- put the student's ZIH login into the commands (kept in this browser only)
  var zihSpans = document.querySelectorAll(".zih"), zihInputs = document.querySelectorAll(".zih-input");
  function applyLogin(value) {
    var clean = (value || "").toLowerCase().replace(/[^a-z0-9_-]/g, "").slice(0, 32);
    zihSpans.forEach(function (s) { s.textContent = clean || "<zih-login>"; });
    zihInputs.forEach(function (i) { if (i.value !== clean) i.value = clean; });
    return clean;
  }
  applyLogin(store.get("zih-login"));
  zihInputs.forEach(function (input) {
    input.addEventListener("input", function () { store.set("zih-login", applyLogin(input.value)); });
  });

  // ---- the black box on the first page
  document.querySelectorAll("[data-bb-toggle]").forEach(function (btn) {
    var bb = btn.closest(".bb");
    btn.addEventListener("click", function () {
      var open = bb.dataset.open !== "true";
      bb.dataset.open = String(open);
      btn.setAttribute("aria-pressed", String(open));
      btn.textContent = open ? "Close the box" : "Open the box";
    });
  });
})();
