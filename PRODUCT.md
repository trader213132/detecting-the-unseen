# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Static HTML/CSS/JS served from `docs/` by GitHub Pages (the user asked for "a good html" website on GitHub). There is no framework or build step. Page data (`docs/data/*.js`) is generated from the experiment outputs by `build_site.py`.

## Users

Primary: the Habs Research Scholarship assessors and teachers reviewing Ebrahim's application (Year 11, internal deadline Friday 6 November 2026). They read on school or home laptops and need to understand the question, the method, the honest result and the plan within minutes, and may come back to see progress. Secondary: anyone following the project from the GitHub repository.

## Product Purpose

A public research page for the project "Detecting the Unseen". It asks: can AI detect hidden market manipulation (spoofing) without being taught what manipulation looks like? The page explains the question, shows how the experiment works, presents the real preliminary results, and tracks progress towards the submission and the Sixth Form plan. Success means a reader leaves knowing what was tested, what was found (including where the hypothesis failed), and what happens next.

## Positioning

This is a real, reproducible experiment, not a pitch. Every number on the page comes from `results/metrics.csv` and `results/impact.csv`, which are produced by `run_experiments.py`. The distinctive mechanism is testing the "without being taught" claim itself: generic versus spoof-informed features, a variant the rule was not written for (layering), genuine large orders of the same size as controls, and honest-twin simulations showing the spoofs actually work.

## Operating Context

- Readers arrive from the application or the GitHub repository link.
- Ebrahim updates progress by editing `docs/progress.js` and regenerating data after experiment runs.
- The research code lives in the same repository (`src/`, `run_experiments.py`).

## Capabilities and Constraints

- Results are preliminary and come from simulation only, so the page must say so and never present them as real-world surveillance performance.
- An anomaly score is never described as proof of manipulation or intent.
- All spoofing happens inside an offline simulation, which the page must state.
- The AI-drafted proposal (`proposal/`) stays private and is not published.
- The byline is "Ebrahim" only (the user's choice). No surname, photo or other personal details.

## Brand Commitments

- Name: "Detecting the Unseen".
- Style direction chosen by the user: "Research journal": clean, editorial, light and dark, figure-led, reads like a serious preprint with an interactive results section.
- The detector colours in the existing figures are Rule = blue `#2a78d6`, PCA = orange `#eb6834`, Isolation Forest = aqua `#1baf7a`. They were validated for colour-blind safety and keep their meaning across the site.

## Evidence on Hand

- `results/metrics.csv`, `results/impact.csv`, `results/summary.md` and `results/figures/*.png`, all real outputs.
- The simulator (`src/market.py`), which can replay real spoof episodes step by step.
- Verified references are listed in `README.md`.
- There are no testimonials, no institutional endorsement and no real-market validation. These must not be invented.

## Product Principles

1. Show the mechanism instead of describing it.
2. Report failures as clearly as successes.
3. Every number traces back to a file in the repository.
4. Unusual is not the same as manipulative. The language must keep that distinction.

## Accessibility & Inclusion

WCAG AA contrast, full keyboard access, respect for reduced-motion preferences, and data tables available for every interactive chart.
