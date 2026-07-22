/* Shared behaviour for every page. Previously inlined per page; with nine
   localised pages it lives in one file. */
(function () {
  var year = document.getElementById("year");
  if (year) { year.textContent = new Date().getFullYear(); }

  // ── Mobile navigation ──────────────────────────────────────
  var toggle = document.querySelector(".nav-toggle");
  var list = document.getElementById("nav-list");
  if (toggle && list) {
    toggle.addEventListener("click", function () {
      var open = toggle.getAttribute("aria-expanded") === "true";
      toggle.setAttribute("aria-expanded", String(!open));
      list.classList.toggle("open", !open);
    });
    list.addEventListener("click", function (e) {
      if (e.target.tagName === "A") {
        toggle.setAttribute("aria-expanded", "false");
        list.classList.remove("open");
      }
    });
  }

  // ── Condense the header once the page has scrolled ─────────
  var head = document.querySelector(".site-head");
  if (head) {
    var onScroll = function () { head.classList.toggle("scrolled", window.scrollY > 24); };
    addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }

  // ── Reveal on scroll ───────────────────────────────────────
  var show = function (el) { el.classList.add("shown"); };

  if (matchMedia("(prefers-reduced-motion: reduce)").matches
      || !("IntersectionObserver" in window)) {
    document.querySelectorAll(".reveal").forEach(show);
    return;
  }

  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) { show(entry.target); io.unobserve(entry.target); }
    });
  }, { threshold: 0 });
  document.querySelectorAll(".reveal").forEach(function (el) { io.observe(el); });

  // Failsafe: nothing stays invisible because a callback was missed.
  setTimeout(function () {
    document.querySelectorAll(".reveal:not(.shown)").forEach(function (el) {
      if (el.getBoundingClientRect().top < innerHeight) { show(el); }
    });
  }, 1200);
})();
