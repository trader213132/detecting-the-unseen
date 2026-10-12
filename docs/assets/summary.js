/* Summary page: cards and findings fade up as they scroll into view (skipped with reduced motion). */
(() => {
  const items = [...document.querySelectorAll("[data-reveal]")];
  if (!items.length || !("IntersectionObserver" in window) || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  // Stagger items that share a parent.
  items.forEach((n) => { const sibs = [...n.parentElement.children].filter((c) => c.hasAttribute("data-reveal")); n.style.setProperty("--d", `${sibs.indexOf(n) * 90}ms`); });
  document.documentElement.classList.add("reveal-ready");
  const io = new IntersectionObserver((entries) => entries.forEach((e) => {
    if (!e.isIntersecting) return;
    e.target.classList.add("is-in");
    io.unobserve(e.target);
  }), { threshold: 0.15, rootMargin: "0px 0px -40px 0px" });
  items.forEach((n) => io.observe(n));
})();
