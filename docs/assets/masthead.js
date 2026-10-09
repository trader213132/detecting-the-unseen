/* Masthead behaviour: the opening sequence, the morphing dropdown, and the small-screen sheet. */
(() => {
  const root = document.documentElement;

  /* ---------- Opening sequence: plays once, after the fonts are in, then removes itself ---------- */
  if (root.classList.contains("intro")) {
    let started = false;
    const start = () => {
      if (started) return;
      started = true;
      requestAnimationFrame(() => requestAnimationFrame(() => {
        root.classList.add("intro-play");
        root.dataset.introAt = String(performance.now());
        dispatchEvent(new Event("intro:play"));
        const lake = document.querySelector(".lake-scene");
        const done = () => root.classList.remove("intro", "intro-play");
        lake?.addEventListener("animationend", (e) => { if (e.target === lake) done(); }, { once: true });
        setTimeout(done, 3000);
      }));
    };
    (document.fonts ? document.fonts.ready : Promise.resolve()).then(start);
    setTimeout(start, 700);
  }

  /* ---------- The dropdown: one container that morphs between three menus ---------- */
  const header = document.querySelector("[data-topbar]");
  const nav = document.getElementById("menu");
  const dd = document.getElementById("dd");
  if (!header || !nav || !dd) return;
  const ORDER = ["findings", "explore", "paper"];
  const PAD = 20;                          // lines each panel's text up with its trigger's text (8px + 12px)
  const triggers = [...nav.querySelectorAll(".menu__trigger")];
  const panels = Object.fromEntries([...dd.querySelectorAll(".dd__panel")].map((p) => [p.dataset.panel, p]));
  const trigger = (id) => triggers.find((t) => t.dataset.menu === id);
  let current = null, closeTimer = 0;

  function place(id) {
    const panel = panels[id], t = trigger(id);
    if (!panel || !t) return;
    const w = panel.offsetWidth, h = panel.offsetHeight;
    const hr = header.getBoundingClientRect(), tr = t.getBoundingClientRect();
    let x = Math.min(Math.max(tr.left - PAD, hr.left + 12), hr.right - w - 12);
    x -= (dd.offsetParent || header).getBoundingClientRect().left;
    dd.style.setProperty("--x", `${x}px`);
    dd.style.setProperty("--w", `${w}px`);
    dd.style.setProperty("--h", `${h}px`);
  }

  function open(id) {
    clearTimeout(closeTimer);
    if (id === current) return;
    const next = panels[id];
    if (!next) return;
    if (!current) {
      // First open: appear in place (scale and fade), without animating position or size.
      dd.classList.add("instant", "snap");
      Object.values(panels).forEach((p) => { p.classList.add("snap"); p.removeAttribute("data-state"); });
      place(id);
      void dd.offsetWidth;
      dd.classList.remove("snap");
      Object.values(panels).forEach((p) => p.classList.remove("snap"));
      dd.classList.add("open");
      requestAnimationFrame(() => dd.classList.remove("instant"));
    } else {
      // Switch: slide the content in the direction of travel while the container morphs to fit.
      const dir = ORDER.indexOf(id) > ORDER.indexOf(current) ? 1 : -1;
      panels[current].dataset.state = dir > 0 ? "exit-left" : "exit-right";
      next.classList.add("snap");
      next.dataset.state = dir > 0 ? "exit-right" : "exit-left";
      void next.offsetWidth;
      next.classList.remove("snap");
      place(id);
    }
    next.dataset.state = "active";
    triggers.forEach((t) => t.setAttribute("aria-expanded", String(t.dataset.menu === id)));
    current = id;
  }

  function close() {
    clearTimeout(closeTimer);
    dd.classList.remove("open");
    if (current) panels[current].removeAttribute("data-state");
    triggers.forEach((t) => t.setAttribute("aria-expanded", "false"));
    current = null;
  }
  const scheduleClose = (ms = 140) => { clearTimeout(closeTimer); closeTimer = setTimeout(close, ms); };

  triggers.forEach((t) => {
    t.addEventListener("pointerenter", (e) => { if (e.pointerType === "mouse") open(t.dataset.menu); });
    t.addEventListener("click", () => (current === t.dataset.menu ? close() : open(t.dataset.menu)));
    t.addEventListener("keydown", (e) => {          // keyboard: arrow down steps into the open menu
      if (e.key !== "ArrowDown") return;
      e.preventDefault();
      open(t.dataset.menu);
      requestAnimationFrame(() => panels[t.dataset.menu].querySelector("a")?.focus());
    });
  });
  document.getElementById("progress-link")?.addEventListener("pointerenter", (e) => { if (e.pointerType === "mouse") scheduleClose(60); });
  nav.addEventListener("pointerenter", () => clearTimeout(closeTimer));
  nav.addEventListener("pointerleave", (e) => { if (e.pointerType === "mouse") scheduleClose(); });
  nav.addEventListener("focusout", (e) => { if (!nav.contains(e.relatedTarget)) scheduleClose(0); });
  dd.addEventListener("click", (e) => { if (e.target.closest("a")) close(); });
  document.addEventListener("pointerdown", (e) => { if (current && !nav.contains(e.target)) close(); });
  addEventListener("resize", () => { if (current) place(current); }, { passive: true });

  // The preview images wait until the page has settled, or until someone reaches for the menu.
  const warm = () => dd.querySelectorAll('img[loading="lazy"]').forEach((img) => { img.loading = "eager"; });
  nav.addEventListener("pointerenter", warm, { once: true });
  nav.addEventListener("focusin", warm, { once: true });
  addEventListener("load", () => setTimeout(warm, 2500), { once: true });

  // Findings rows: hovering or focusing one brings up its figure.
  const rows = [...dd.querySelectorAll(".dd-item")], pics = [...dd.querySelectorAll(".dd-media img")];
  const show = (row) => {
    rows.forEach((r) => r.classList.toggle("is-active", r === row));
    pics.forEach((p, i) => p.classList.toggle("is-active", i === +row.dataset.img));
  };
  rows.forEach((r) => { r.addEventListener("pointerenter", () => show(r)); r.addEventListener("focus", () => show(r)); });

  /* ---------- Small screens: the sheet ---------- */
  const btn = header.querySelector(".menu-btn"), sheet = document.getElementById("sheet");
  const setSheet = (on) => {
    if (!btn || !sheet) return;
    sheet.classList.toggle("open", on);
    btn.setAttribute("aria-expanded", String(on));
    btn.setAttribute("aria-label", on ? "Close menu" : "Open menu");
  };
  btn?.addEventListener("click", (e) => { e.stopPropagation(); setSheet(!sheet.classList.contains("open")); });
  sheet?.addEventListener("click", (e) => { if (e.target.closest("a")) setSheet(false); });
  document.addEventListener("click", (e) => { if (sheet?.classList.contains("open") && !header.contains(e.target)) setSheet(false); });

  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    if (current) { const t = trigger(current); close(); t?.focus(); }
    if (sheet?.classList.contains("open")) { setSheet(false); btn?.focus(); }
  });
})();
