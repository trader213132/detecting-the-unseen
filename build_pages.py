"""Write the shared header (with its menus) and footer into every page of the website.

    python build_pages.py

Each page in docs/ has two pairs of markers:
    <!-- header:start --> ... <!-- header:end -->     <!-- footer:start --> ... <!-- footer:end -->
Everything between them is replaced, so a menu change is made once, here, for all pages.
"""
from pathlib import Path

DOCS = Path(__file__).parent / "docs"
REPO = "https://github.com/trader213132/detecting-the-unseen"
ARROW = '<svg width="10" height="8" viewBox="0 0 9.5 8" aria-hidden="true"><path d="M0.7 4H8.8M5.6 0.75 8.85 4 5.6 7.25"/></svg>'
CHEV = '<svg class="chev" width="8" height="5" viewBox="0 0 8 5" aria-hidden="true"><path d="M1 1l3 3 3-3"/></svg>'

# The study: the four chapters that tell the story, each with a figure preview.
STUDY = [("experiment.html", "The experiment", "A market where spoofing works, and seven detectors.", "replay"),
         ("results.html", "Results", "Spoofs against honest look-alikes and volatile markets.", "detectors"),
         ("teaching.html", "What kind of teaching works?", "Examples, a rule, or the law. And how to dodge it.", "ladder"),
         ("conclusion.html", "What it means", "The answer, its limits and the sources.", "answer")]
CHALLENGER_READY = False       # Part 4's chapter is listed only once its results are in
if CHALLENGER_READY:
    STUDY.insert(3, ("challenger.html", "An AI challenger", "A search program hunts for spoofs the law-based detector misses.", "challenger"))
EXPLORE = [("lab.html", "Research Lab", "Pick a market situation and see how every detector reacts.", "lab"),
           ("index.html#replay", "Watch one spoof", "The wall goes up, the order fills, the wall vanishes.", "replay")]
PAPER = [("report.html", "Research report"), ("summary.html", "Summary: the project in five minutes"),
         ("analytics.html", "Analytics explorer"), ("conclusion.html#references", "References")]
PAGES = {"index.html": "Home", "experiment.html": "The experiment", "results.html": "Results",
         "teaching.html": "Teaching", "conclusion.html": "What it means", "progress.html": "Progress",
         "lab.html": "Research Lab", "summary.html": "Summary", "analytics.html": "Analytics"}
if CHALLENGER_READY:
    PAGES = {**{k: v for k, v in PAGES.items() if k != "conclusion.html" and k not in ("progress.html", "lab.html", "summary.html", "analytics.html")},
             "challenger.html": "Challenger", **{k: v for k, v in PAGES.items() if k in ("conclusion.html", "progress.html", "lab.html", "summary.html", "analytics.html")}}


def img(name, w, h, lazy=True):
    lazy_attr = ' loading="lazy"' if lazy else ""
    return f'<img src="assets/menu/{name}.webp" alt="" width="{w}" height="{h}" decoding="async"{lazy_attr}>'


def header(page):
    here = lambda href: ' aria-current="page"' if href == page else ""
    solid = "" if page == "index.html" else " is-solid"
    rows = "\n".join(
        f'              <a class="dd-item{" is-active" if i == 0 else ""}" href="{h}" data-img="{i}"{here(h)}><strong>{t}</strong><span>{d}</span></a>'
        for i, (h, t, d, _) in enumerate(STUDY))
    first = lambda tag: tag.replace("<img ", '<img class="is-active" ', 1)
    media = "\n".join("              " + (first(img(im, 856, 716, False)) if i == 0 else img(im, 856, 716))
                      for i, (_, _, _, im) in enumerate(STUDY))
    cards = "\n".join(f'            <a class="dd-card" href="{h}"{here(h)}>{img(im, 432, 588)}<strong>{t}</strong><span>{d}</span></a>'
                      for h, t, d, im in EXPLORE)
    links = "\n".join(f'            <a class="dd-link" href="{h}"{here(h)}>{t}</a>' for h, t in PAPER)
    s_items = "\n".join(f'        <a class="sheet-item" href="{h}">{img(im, 856, 716)}<span><strong>{t}</strong><small>{d}</small></span></a>'
                        for h, t, d, im in STUDY)
    s_cards = "\n".join(f'        <a class="sheet-card" href="{h}">{img(im, 432, 588)}<strong>{t}</strong><small>{d}</small></a>'
                        for h, t, d, im in EXPLORE)
    s_links = "\n".join(f'        <a href="{h}">{t}</a>' for h, t in PAPER)
    return f'''  <header class="topbar{solid}" data-topbar>
    <div class="topbar__inner">
      <a class="wordmark" href="index.html" aria-label="Detecting the Unseen, home">
        <span class="wordmark__glyph" aria-hidden="true"><span></span><span></span><span></span></span>
        Detecting the Unseen
      </a>
      <nav class="menu" id="menu" aria-label="Main">
        <ul class="menu__links">
          <li><a class="menu__plain" href="summary.html"{here("summary.html")}>Summary</a></li>
          <li><button class="menu__trigger" type="button" data-menu="findings" aria-expanded="false" aria-controls="p-findings">The study{CHEV}</button></li>
          <li><button class="menu__trigger" type="button" data-menu="explore" aria-expanded="false" aria-controls="p-explore">Explore{CHEV}</button></li>
          <li><button class="menu__trigger" type="button" data-menu="paper" aria-expanded="false" aria-controls="p-paper">The paper{CHEV}</button></li>
          <li><a class="menu__plain" href="lab.html"{here("lab.html")}>Lab</a></li>
          <li><a class="menu__plain" href="progress.html"{here("progress.html")}>Progress</a></li>
        </ul>
        <!-- One container for all three menus: it morphs between them rather than closing and reopening. -->
        <div class="dd" id="dd">
          <div class="dd__panel dd-findings" id="p-findings" data-panel="findings">
            <div class="dd-list">
{rows}
            </div>
            <div class="dd-media" aria-hidden="true">
{media}
            </div>
          </div>
          <div class="dd__panel dd-explore" id="p-explore" data-panel="explore">
{cards}
          </div>
          <div class="dd__panel dd-paper" id="p-paper" data-panel="paper">
{links}
          </div>
        </div>
      </nav>
      <div class="topbar__actions">
        <button class="icon-button" type="button" id="theme-toggle" aria-label="Switch between light and dark theme">
          <i class="ph ph-moon theme-icon-light" aria-hidden="true"></i>
          <i class="ph ph-sun theme-icon-dark" aria-hidden="true"></i>
        </button>
        <a class="icon-button" href="{REPO}" data-repo-link aria-label="Code on GitHub"><i class="ph ph-github-logo" aria-hidden="true"></i></a>
        <a class="pill cta" href="report.html">Report</a>
        <button class="menu-btn" type="button" aria-label="Open menu" aria-expanded="false" aria-controls="sheet">
          <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path d="M2 5.5h12M2 10.5h12"/></svg>
        </button>
      </div>
    </div>
    <div class="sheet" id="sheet">
      <a class="sheet-summary" href="summary.html"><span><strong>Summary</strong><small>The question and the answer in plain words</small></span>{ARROW}</a>
      <h3>The study</h3>
      <div class="sheet-list">
{s_items}
      </div>
      <h3>Explore</h3>
      <div class="sheet-cards">
{s_cards}
      </div>
      <h3>The paper</h3>
      <div class="sheet-links">
{s_links}
        <a href="progress.html">Progress</a>
        <a href="{REPO}" data-repo-link>Code on GitHub</a>
      </div>
    </div>
  </header>'''


def footer(page):
    links = " · ".join(f'<a href="{h}"{" aria-current=page" if h == page else ""}>{t}</a>' for h, t in PAGES.items())
    return f'''  <footer class="footer">
    <div class="footer__inner">
      <p class="footer__links">{links} · <a href="report.html">Report</a> · <a href="{REPO}" data-repo-link>Code</a></p>
      <p>Research use only. Every spoof on this site happened inside an offline simulation, and an alert is never evidence of intent.</p>
      <p>Every number comes from the code in <a href="{REPO}" data-repo-link>the repository</a>. Data generated <time data-generated></time>.</p>
    </div>
  </footer>'''


def replace(text, name, new):
    start, end = f"<!-- {name}:start -->", f"<!-- {name}:end -->"
    a, b = text.index(start), text.index(end)
    return text[:a] + start + "\n" + new + "\n  " + text[b:]


def main():
    for page in PAGES:
        path = DOCS / page
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if "<!-- header:start -->" not in text:
            print(f"skipped {page}: no header markers")
            continue
        text = replace(text, "header", header(page))
        if "<!-- footer:start -->" in text:
            text = replace(text, "footer", footer(page))
        path.write_text(text, encoding="utf-8")
        print("updated", page)


if __name__ == "__main__":
    main()
