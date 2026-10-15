/* Replay saved probabilities, never live training or invented observations. */
(() => {
  const data = window.EMERGENCE;
  const stage = document.querySelector('[data-learning-stage]');
  if (!data || !stage || !data.training.length) return;
  const $ = (s) => document.querySelector(s);
  const condition = $('#learning-condition'), learner = $('#learning-learner');
  const scrub = $('#learning-round'), play = $('#learning-play'), status = $('#learning-status');
  const reduce = matchMedia('(prefers-reduced-motion: reduce)');
  const knobs = [
    ['aggression', 'Client order', [['0', 'Wait at best price'], ['1', 'Improve by one tick'], ['2', 'Cross the spread']]],
    ['extra_side', 'Extra order', [['0', 'None'], ['1', 'Same side'], ['-1', 'Opposite side']]],
    ['extra_size', 'Extra size', ['1', '2', '4', '8', '16'].map(v => [v, `${v}× typical`])],
    ['extra_distance', 'Distance', ['0', '1', '2', '3', '4', '5', '6'].map(v => [v, `${v} ticks back`])],
    ['extra_life', 'Cancellation', [['fill', 'When client fills'], ['5', 'After 5 steps'], ['15', 'After 15 steps'], ['30', 'At horizon']]],
  ];
  const nodes = [];
  const make = (tag, parent, text) => { const n = document.createElement(tag); if (text) n.textContent = text; parent.append(n); return n; };
  stage.replaceChildren();
  knobs.forEach(([key, label, options]) => {
    const row = make('div', stage); row.className = 'learning-choices'; make('h3', row, label);
    const list = make('div', row); list.className = 'learning-options';
    options.forEach(([value, label]) => {
      const item = make('div', list); item.className = 'learning-option'; item.dataset.option = `${key}:${value}`;
      make('span', item, label);
      const track = make('span', item); track.className = 'prob-track'; track.setAttribute('aria-hidden', 'true');
      const fill = make('span', track); fill.className = 'prob-fill';
      const number = make('output', item); number.setAttribute('aria-label', `${label} probability`);
      nodes.push({key: `p_${key}_${value}`, fill, number});
    });
  });
  let series = [], frame = 0, playing = false, last = 0;
  function stop() { playing = false; cancelAnimationFrame(frame); play.textContent = 'Play learning'; play.setAttribute('aria-pressed', 'false'); }
  function draw() {
    const r = series[Number(scrub.value)]; if (!r) return;
    nodes.forEach(n => { n.fill.style.setProperty('--probability', r[n.key]); n.number.textContent = `${(r[n.key]*100).toFixed(1)}%`; });
    $('#learning-round-label').textContent = `Round ${r.iteration + 1} of ${series.length}`;
    status.textContent = `This training batch: ${r.reward.toFixed(3)} ticks per client lot; ${(100*r.signature_share).toFixed(1)}% of sampled choices matched the predeclared signature. This is not a manipulation verdict.`;
  }
  function select() { stop(); series = data.training.filter(r => r.fine === Number(condition.value) && r.learner === Number(learner.value)); scrub.max = series.length - 1; scrub.value = scrub.max; draw(); }
  function tick(t) {
    if (!playing) return;
    if (t-last >= 160) { last=t; scrub.value=Number(scrub.value)+1; draw(); }
    if (Number(scrub.value)>=series.length-1) { stop(); return; }
    frame=requestAnimationFrame(tick);
  }
  play.addEventListener('click', () => {
    if (playing) { stop(); return; }
    if (reduce.matches) { scrub.value=scrub.max; draw(); status.textContent += ' Reduced motion: final round shown. Use the slider to inspect earlier rounds.'; return; }
    if (Number(scrub.value)>=series.length-1) scrub.value=0;
    playing=true; last=performance.now(); play.textContent='Pause learning'; play.setAttribute('aria-pressed', 'true'); frame=requestAnimationFrame(tick);
  });
  condition.addEventListener('change', select); learner.addEventListener('change', select);
  scrub.addEventListener('input', () => { stop(); draw(); });
  document.addEventListener('visibilitychange', () => { if (document.hidden) stop(); });
  reduce.addEventListener('change', stop);
  if ('IntersectionObserver' in window) new IntersectionObserver(entries => { if (!entries[0].isIntersecting) stop(); }).observe(stage);
  const market = $('#learning-market');
  market.addEventListener('change', () => {
    document.querySelectorAll('[data-market-table]').forEach(el => { el.hidden = el.dataset.marketTable !== market.value; });
    $('#market-status').textContent = `Showing ${market.selectedOptions[0].textContent.toLowerCase()}. Each row uses ${data.manifest.config.test} matched test sessions.`;
  });
  document.querySelectorAll('[data-market-table]').forEach(el => { el.hidden = el.dataset.marketTable !== market.value; });
  $('[data-learning-controls]').hidden=false; $('[data-market-controls]').hidden=false;
  select();
})();
