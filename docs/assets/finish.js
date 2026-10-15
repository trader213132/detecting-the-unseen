/* Finishing touches (October 2026): the sliding contents marker, the footer's one reveal and its
   back-to-top button, and the learning chapter's verdict row. Loaded once on every page from the footer.
   Everything degrades to the plain page without JavaScript or with reduced motion. */
(() => {
  "use strict";
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const raf = (fn) => { let q = false; return () => { if (q) return; q = true; requestAnimationFrame(() => { q = false; fn(); }); }; };

  // ---- 1. The contents marker: one bar that slides to the section being read -------------------------
  const toc = document.querySelector(".toc");
  const list = toc && toc.querySelector("ol");
  if (list) {
    toc.classList.add("toc--js");
    const marker = document.createElement("span");
    marker.className = "toc__marker";
    marker.setAttribute("aria-hidden", "true");
    list.appendChild(marker);
    const place = () => {
      const a = list.querySelector('a[aria-current="true"]');
      if (!a) { marker.style.opacity = "0"; return; }
      marker.style.setProperty("--y", `${a.offsetTop}px`);
      marker.style.setProperty("--h", `${a.offsetHeight}px`);
      marker.style.opacity = "1";
    };
    new MutationObserver(place).observe(list, { attributes: true, subtree: true, attributeFilter: ["aria-current"] });
    addEventListener("resize", raf(place), { passive: true });
    if (document.fonts) document.fonts.ready.then(place);
    place();
  }

  // ---- 2. The footer: the name rises once; back to top ---------------------------------------------------
  const foot = document.querySelector(".wayfinder");
  if (foot) {
    if (!reduced && "IntersectionObserver" in window) {
      foot.classList.add("wayfinder--armed");
      const io = new IntersectionObserver(([e]) => {
        if (!e.isIntersecting) return;
        io.disconnect();
        requestAnimationFrame(() => foot.classList.add("wayfinder--in"));
      }, { threshold: 0.2, rootMargin: "0px 0px -10% 0px" });
      io.observe(foot);
    }
    const top = foot.querySelector(".wayfinder__top");
    if (top) top.addEventListener("click", () => {
      window.scrollTo({ top: 0, behavior: reduced ? "auto" : "smooth" });
      const target = document.getElementById("top") || document.querySelector("main");
      if (target) { if (!target.hasAttribute("tabindex")) target.setAttribute("tabindex", "-1"); target.focus({ preventScroll: true }); }
    });
  }

  // ---- 3. The learning chapter's verdict row ---------------------------------------------------------------
  const verdict = document.querySelector("[data-verdict]");
  if (verdict && !reduced && "IntersectionObserver" in window) {
    const tokens = [...verdict.querySelectorAll(".verdict__token")];
    const n = verdict.querySelector(".verdict__n");
    const value = n ? n.textContent : "";
    let x = 20261015;                                                    // the same scatter on every visit
    const next = () => { x = (Math.imul(x, 1664525) + 1013904223) >>> 0; return x / 2 ** 32; };
    tokens.forEach((t) => {
      t.querySelector(".verdict__dot").style.setProperty("--from-x", `${Math.round(next() * 48 - 24)}px`);
      t.classList.add("is-armed");
    });
    verdict.classList.add("verdict--armed");
    if (n) n.textContent = "?";
    const io = new IntersectionObserver(([e]) => {
      if (!e.isIntersecting) return;
      io.disconnect();
      tokens.forEach((t, i) => setTimeout(() => { t.classList.add("is-landing"); t.classList.remove("is-armed"); }, i * 90));
      setTimeout(() => {
        verdict.classList.remove("verdict--armed");
        setTimeout(() => { if (n) n.textContent = value; }, 150);
      }, (tokens.length - 1) * 90 + 700);
    }, { threshold: 0.4 });
    io.observe(verdict);
  }
})();
