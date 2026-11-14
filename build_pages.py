"""Write the shared header (with its menus) and footer into every page of the website.

    python build_pages.py

Each page in docs/ has two pairs of markers:
    <!-- header:start --> ... <!-- header:end -->     <!-- footer:start --> ... <!-- footer:end -->
Everything between them is replaced, so a menu change is made once, here, for all pages.

The site is organised in four groups, the same in the desktop menu, the phone menu and the footer:
    Simulations   every interactive replay and lab (also listed on simulations.html, the flask icon)
    Explanations  the chapters, in reading order
    Scholarship   the portfolio and the Economics pilot
    Paper         summary, report, references, progress
"""
from pathlib import Path

DOCS = Path(__file__).parent / "docs"
REPO = "https://github.com/trader213132/detecting-the-unseen"
ARROW = '<svg width="10" height="8" viewBox="0 0 9.5 8" aria-hidden="true"><path d="M0.7 4H8.8M5.6 0.75 8.85 4 5.6 7.25"/></svg>'
CHEV = '<svg class="chev" width="8" height="5" viewBox="0 0 8 5" aria-hidden="true"><path d="M1 1l3 3 3-3"/></svg>'

# Explanations: the chapters that tell the story, in reading order, each with a figure preview.
STUDY = [("learning.html", "The learning experiment", "What an AI trader learns, with held-out controls.", "learning"),
         ("experiment.html", "The detector foundation", "A market where spoofing works, and seven detectors.", "replay"),
         ("results.html", "Results", "Spoofs against honest look-alikes and volatile markets.", "detectors"),
         ("teaching.html", "What kind of teaching works?", "Examples, a rule, or the law. And how to dodge it.", "ladder"),
         ("challenger.html", "An AI challenger", "A search program hunts for spoofs the law-based detector misses.", "challenger"),
         ("conclusion.html", "What it means", "The answer, its limits and the sources.", "answer")]

# Simulations: (page, title, one line, Phosphor icon, kind, explained in (page, title)).
# The same list drives the menu, the phone menu, the footer and the simulations.html hub.
SIMS = [("index.html#replay", "Watch one spoof", "A fake wall goes up, the order fills, the wall vanishes.", "play-circle", "Replay",
         ("experiment.html", "The detector foundation")),
        ("lab.html", "Research Lab", "Pick a market situation and see how every detector reacts.", "sliders-horizontal", "Lab",
         ("results.html", "Results")),
        ("surveillance.html", "Surveillance Lab", "A spoof and an honest change of mind, side by side.", "binoculars", "Replay",
         ("teaching.html", "What kind of teaching works?")),
        ("challenger.html#challenger", "AI challenger", "Watch a search program hunt for spoofs the detector misses.", "crosshair", "Replay",
         ("challenger.html", "An AI challenger")),
        ("learning.html#learning-replay", "Learning replay", "Step through what six AI traders learned, round by round.", "brain", "Replay",
         ("learning.html", "The learning experiment")),
        ("break-even.html", "Break-Even Lab", "When does a spoof pay? 48 simulated markets.", "scales", "Lab",
         ("scholarship.html#economics", "Economics proposal")),
        ("analytics.html", "Analytics explorer", "Filter and compare every result table.", "chart-bar", "Charts",
         ("report.html", "Research report")),
        ("scholarship.html#mathematics", "Base-rate calculator", "How often is an alert right? Bayes, interactively.", "percent", "Calculator",
         ("scholarship.html#mathematics", "Mathematics proposal"))]

SCHOLAR = [("scholarship.html", "Scholarship portfolio"), ("break-even.html", "Break-Even Lab: when does manipulation pay?"),
           ("surveillance.html", "Surveillance Lab: two traders, one footprint")]
PAPER = [("summary.html", "Summary: the project in five minutes"), ("report.html", "Research report"), ("report.pdf", "Report as PDF"),
         ("conclusion.html#references", "References"), ("progress.html", "Progress")]

PAGES = {"index.html": "Home", "simulations.html": "Simulations", "learning.html": "Learning experiment", "experiment.html": "The experiment",
         "results.html": "Results", "teaching.html": "Teaching", "challenger.html": "Challenger", "conclusion.html": "What it means",
         "progress.html": "Progress", "lab.html": "Research Lab", "summary.html": "Summary", "analytics.html": "Analytics",
         "scholarship.html": "Scholarship Research", "break-even.html": "Break-Even Lab", "surveillance.html": "Surveillance Lab"}

# What each menu picture shows, in one line (the menu shows it under the picture)
CAPTIONS = {"learning": "What the AI trader chose after 100 rounds of learning. Pink: an extra order on the opposite side.",
            "replay": "One spoof replayed: the fake wall (pink) beside the real order book.",
            "detectors": "Who catches what: the share of spoofs each detector flags, by order size.",
            "ladder": "The ladder of teaching: spoofs caught (pink) and honest orders flagged (grey).",
            "challenger": "The challenger learning: the best payoff it found, round by round, per detector.",
            "answer": "Spoof or honest order? 0.5 is a coin toss; lower means honest orders look stranger."}


def img(name, w, h, lazy=True):
    lazy_attr = ' loading="lazy"' if lazy else ""
    return f'<img src="assets/menu/{name}.webp" alt="" width="{w}" height="{h}" decoding="async"{lazy_attr}>'


def header(page):
    here = lambda href: ' aria-current="page"' if href == page else ""
    solid = "" if page == "index.html" else " is-solid"
    rows = "\n".join(
        f'              <a class="dd-item{" is-active" if i == 0 else ""}" href="{h}" data-img="{i}"{here(h)}><strong><span class="dd-num">{i + 1:02d}</span>{t}</strong><span>{d}</span></a>'
        for i, (h, t, d, _) in enumerate(STUDY))
    first = lambda tag: tag.replace("<img ", '<img class="is-active" ', 1)
    media = "\n".join("              " + (first(img(im, 856, 716, False)) if i == 0 else img(im, 856, 716)).replace("<img ", f'<img data-cap="{CAPTIONS.get(im, "")}" ', 1)
                      for i, (_, _, _, im) in enumerate(STUDY))
    media += f'\n              <p class="dd-cap">{CAPTIONS.get(STUDY[0][3], "")}</p>'
    sims = "\n".join(f'            <a class="dd-sim" href="{h}"{here(h)}><i class="ph ph-{ic} dd-sim__icon" aria-hidden="true"></i>'
                     f'<span><strong>{t}</strong><span>{d}</span></span></a>' for h, t, d, ic, _, _ in SIMS)
    links = "\n".join(f'            <a class="dd-link" href="{h}"{here(h)}>{t}</a>' for h, t in PAPER)
    scholar = "\n".join(f'            <a class="dd-link" href="{h}"{here(h)}>{t}</a>' for h, t in SCHOLAR)
    s_items = "\n".join(f'        <a class="sheet-item" href="{h}">{img(im, 856, 716)}<span><strong>{t}</strong><small>{d}</small></span></a>'
                        for h, t, d, im in STUDY)
    s_sims = "\n".join(f'        <a class="sheet-sim" href="{h}"><i class="ph ph-{ic}" aria-hidden="true"></i><span><strong>{t}</strong><small>{d}</small></span></a>'
                       for h, t, d, ic, _, _ in SIMS)
    s_scholar = "\n".join(f'        <a href="{h}">{t}</a>' for h, t in SCHOLAR)
    s_links = "\n".join(f'        <a href="{h}">{t}</a>' for h, t in PAPER)
    return f'''  <header class="topbar{solid}" data-topbar>
    <div class="topbar__inner">
      <a class="wordmark" href="index.html" aria-label="Detecting the Unseen, home">
        <span class="wordmark__glyph" aria-hidden="true"><span></span><span></span><span></span></span>
        Detecting the Unseen
      </a>
      <nav class="menu" id="menu" aria-label="Main">
        <ul class="menu__links">
          <li><a class="menu__plain" href="index.html#start">Start here</a></li>
          <li><button class="menu__trigger" type="button" data-menu="sims" aria-expanded="false" aria-controls="p-sims">Simulations{CHEV}</button></li>
          <li><button class="menu__trigger" type="button" data-menu="findings" aria-expanded="false" aria-controls="p-findings">Explanations{CHEV}</button></li>
          <li><button class="menu__trigger" type="button" data-menu="scholar" aria-expanded="false" aria-controls="p-scholar">Scholarship{CHEV}</button></li>
          <li><button class="menu__trigger" type="button" data-menu="paper" aria-expanded="false" aria-controls="p-paper">Paper{CHEV}</button></li>
        </ul>
        <!-- One container for all the menus: it morphs between them rather than closing and reopening. -->
        <div class="dd" id="dd">
          <div class="dd__panel dd-sims" id="p-sims" data-panel="sims">
            <p class="dd-head">Interactive simulations <span>every one runs on the offline simulated market</span></p>
{sims}
            <a class="dd-all" href="simulations.html"{here("simulations.html")}>All simulations, and where each is explained {ARROW}</a>
          </div>
          <div class="dd__panel dd-findings" id="p-findings" data-panel="findings">
            <div class="dd-list">
{rows}
            </div>
            <div class="dd-media" aria-hidden="true">
{media}
            </div>
          </div>
          <div class="dd__panel dd-paper dd-scholar" id="p-scholar" data-panel="scholar">
{scholar}
          </div>
          <div class="dd__panel dd-paper" id="p-paper" data-panel="paper">
{links}
          </div>
        </div>
      </nav>
      <div class="topbar__actions">
        <a class="icon-button icon-button--sims" href="simulations.html" aria-label="All simulations" title="All simulations"{here("simulations.html")}><i class="ph ph-flask" aria-hidden="true"></i></a>
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
      <a class="sheet-summary" href="index.html#start"><span><strong>Start here</strong><small>Three ways in: run it, read it, or see the scholarship proposal</small></span>{ARROW}</a>
      <a class="sheet-summary" href="simulations.html"><span><strong>All simulations</strong><small>Every replay and lab, with the chapter that explains it</small></span>{ARROW}</a>
      <h3>Simulations</h3>
      <div class="sheet-sims">
{s_sims}
      </div>
      <h3>Explanations</h3>
      <div class="sheet-list">
{s_items}
      </div>
      <h3>Scholarship</h3>
      <div class="sheet-links">
{s_scholar}
      </div>
      <h3>Paper</h3>
      <div class="sheet-links">
{s_links}
        <a href="{REPO}" data-repo-link>Code on GitHub</a>
      </div>
    </div>
  </header>'''


def footer(page):
    """The Wayfinder footer: the same four groups as the menu."""
    here = lambda href: ' aria-current="page"' if href == page else ""
    chapters = [("summary.html", "Summary")] + [(h, t) for h, t, _, _ in STUDY]
    study = chr(10).join(f'          <li><a href="{h}"{here(h)}><span class="wayfinder__num">{i:02d}</span>{t}</a></li>'
                         for i, (h, t) in enumerate(chapters))
    sims = [("simulations.html", "All simulations")] + [(h, t) for h, t, *_ in SIMS]
    paper = SCHOLAR[:2] + [("report.html", "Research report"), ("report.pdf", "Report as PDF"),
                           ("conclusion.html#references", "References"), (REPO, "Code on GitHub"), ("progress.html", "Progress")]
    item = lambda h, t: (f'          <li><a href="{h}" data-repo-link>{t}</a></li>' if h == REPO
                         else f'          <li><a href="{h}"{here(h)}>{t}</a></li>')
    return f'''  <footer class="footer wayfinder">
    <div class="wayfinder__inner">
      <p class="wayfinder__name" aria-hidden="true">Detecting the Unseen</p>
      <div class="wayfinder__grid">
        <nav class="wayfinder__col" aria-label="Simulations">
          <p class="wayfinder__head">Simulations</p>
          <ul>
{chr(10).join(item(h, t) for h, t in sims)}
          </ul>
        </nav>
        <nav class="wayfinder__col" aria-label="Explanations">
          <p class="wayfinder__head">Explanations, in reading order</p>
          <ol>
{study}
          </ol>
        </nav>
        <nav class="wayfinder__col" aria-label="Scholarship and paper">
          <p class="wayfinder__head">Scholarship and paper</p>
          <ul>
{chr(10).join(item(h, t) for h, t in paper)}
          </ul>
        </nav>
      </div>
      <div class="wayfinder__base">
        <div class="wayfinder__notes">
          <p>Research use only. Every spoof on this site happened inside an offline simulation, and an alert is never evidence of intent.</p>
          <p>Charts and tables are built from the results files in <a href="{REPO}" data-repo-link>the repository</a>; figures quoted in the text were checked against them. Detector data generated <time data-generated></time>.</p>
        </div>
        <button class="wayfinder__top" type="button">Back to top <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true"><path d="M5 8.6V1.6M1.9 4.6 5 1.4l3.1 3.2"/></svg></button>
      </div>
    </div>
    <script src="assets/finish.js?v=1" defer></script>
  </footer>'''


def sims_grid():
    """The cards on simulations.html: what each simulation is, and where it is explained."""
    return "\n".join(
        f'''          <article class="sim-card">
            <div class="sim-card__top"><span class="sim-card__icon"><i class="ph ph-{ic}" aria-hidden="true"></i></span><span class="sim-kind">{kind}</span></div>
            <h3>{t}</h3>
            <p>{d}</p>
            <div class="sim-card__links">
              <a class="sim-open" href="{h}">Open the simulation {ARROW}</a>
              <a class="sim-explain" href="{eh}"><span>Explained in <b>{et}</b></span>{ARROW}</a>
            </div>
          </article>''' for h, t, d, ic, kind, (eh, et) in SIMS)


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
        if "<!-- sims:start -->" in text:
            text = replace(text, "sims", sims_grid())
        path.write_text(text, encoding="utf-8")
        print("updated", page)


if __name__ == "__main__":
    main()
