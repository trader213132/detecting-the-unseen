/* Existing home choreography with shared motion preferences and an offscreen budget. */
(() => {
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const stopped = () => reduced.matches || document.documentElement.dataset.motion === 'paused';
  const text = document.querySelector('[data-reveal]');
  const stack = document.querySelector('[data-stack]');
  const cards = [...(stack?.querySelectorAll('.stack-card') || [])];
  const spans = [];
  if (text) {
    text.setAttribute('aria-label', text.textContent);
    const words = text.textContent.split(/(\s+)/);
    text.textContent = '';
    words.forEach(word => {
      if (/^\s+$/.test(word)) { text.append(word); return; }
      const span = document.createElement('span');
      span.className = 'w'; span.textContent = word; span.setAttribute('aria-hidden', 'true');
      text.append(span); spans.push(span);
    });
  }
  const mosaics = [...document.querySelectorAll('[data-mosaic]')];
  const visible = new Set();
  mosaics.forEach(mosaic => {
    mosaic.querySelectorAll('.mosaic__col').forEach(col => {
      [...col.children].forEach(tile => {
        const copy = tile.cloneNode(true);
        copy.setAttribute('aria-hidden', 'true'); copy.inert = true; copy.removeAttribute('id');
        col.append(copy);
      });
    });
  });
  function mosaicState() {
    mosaics.forEach(mosaic => mosaic.classList.toggle('motion-resting',
      stopped() || document.hidden || !visible.has(mosaic)));
  }
  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver(entries => {
      entries.forEach(e => e.isIntersecting ? visible.add(e.target) : visible.delete(e.target));
      mosaicState();
    });
    mosaics.forEach(mosaic => io.observe(mosaic));
  } else mosaics.forEach(mosaic => visible.add(mosaic));
  let queued = false;
  function update() {
    queued = false;
    if (document.hidden) return;
    const off = stopped();
    if (text) {
      const r = text.getBoundingClientRect();
      const p = Math.min(1, Math.max(0, (innerHeight * 0.8 - r.top) / (r.height + innerHeight * 0.6)));
      spans.forEach((span, i) => span.style.setProperty('--o', String(off ? 1 :
        0.18 + 0.82 * Math.min(1, Math.max(0, (p - i / spans.length) * spans.length / 4)))));
    }
    if (stack) {
      const r = stack.getBoundingClientRect();
      const progress = Math.min(1, Math.max(0, -r.top / Math.max(1, r.height - innerHeight)));
      cards.forEach((card, i) => {
        const local = Math.min(1, Math.max(0, progress * cards.length - i));
        card.style.setProperty('--scale', String(off ? 1 : 1 - (cards.length - 1 - i) * 0.04 * local));
      });
    }
  }
  function queue() { if (!queued) { queued = true; requestAnimationFrame(update); } }
  function preference() { mosaicState(); queue(); }
  addEventListener('scroll', queue, { passive: true });
  addEventListener('resize', queue, { passive: true });
  addEventListener('motionchange', preference);
  reduced.addEventListener('change', preference);
  document.addEventListener('visibilitychange', preference);
  preference();
})();
