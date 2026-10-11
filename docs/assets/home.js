/* Home page sections: the sentence that lights up word by word as you scroll, the finding cards
   that settle back as the next one slides over them, and the mosaic's endless columns. */
(() => {
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------- Words light up with scroll ---------- */
  const text = document.querySelector("[data-reveal]");
  if (text && !reduced) {
    text.setAttribute("aria-label", text.textContent);
    const words = text.textContent.split(/(\s+)/);
    text.textContent = "";
    const spans = words.map((w) => {
      if (/^\s+$/.test(w)) { text.append(w); return null; }
      const s = document.createElement("span");
      s.className = "w"; s.textContent = w; s.setAttribute("aria-hidden", "true");
      text.append(s);
      return s;
    }).filter(Boolean);
    const update = () => {
      const r = text.getBoundingClientRect(), vh = innerHeight;
      // 0 when the text's top reaches 80% of the screen, 1 when its bottom reaches 20%.
      const p = Math.min(1, Math.max(0, (vh * 0.8 - r.top) / (r.height + vh * 0.6)));
      spans.forEach((s, i) => {
        const at = i / spans.length;
        s.style.setProperty("--o", String(0.18 + 0.82 * Math.min(1, Math.max(0, (p - at) * spans.length / 4))));
      });
    };
    let queued = false;
    addEventListener("scroll", () => { if (!queued) { queued = true; requestAnimationFrame(() => { queued = false; update(); }); } }, { passive: true });
    update();
  }

  /* ---------- Finding cards: each settles back as the next slides over ---------- */
  const stack = document.querySelector("[data-stack]");
  if (stack) {
    const cards = [...stack.querySelectorAll(".stack-card")];
    if (!reduced) {
      const n = cards.length;
      const update = () => {
        const r = stack.getBoundingClientRect();
        const progress = Math.min(1, Math.max(0, -r.top / Math.max(1, r.height - innerHeight)));
        cards.forEach((card, i) => {
          const target = 1 - (n - 1 - i) * 0.04;          // earlier cards end smaller
          const local = Math.min(1, Math.max(0, progress * n - i));
          card.style.setProperty("--scale", String(1 - (1 - target) * local));
        });
      };
      let queued = false;
      addEventListener("scroll", () => { if (!queued) { queued = true; requestAnimationFrame(() => { queued = false; update(); }); } }, { passive: true });
      update();
    }
  }

  /* ---------- Mosaic: each column holds its tiles twice, so moving by half loops seamlessly ---------- */
  document.querySelectorAll("[data-mosaic] .mosaic__col").forEach((col) => {
    [...col.children].forEach((tile) => col.append(tile.cloneNode(true)));
  });
})();
