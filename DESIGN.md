---
name: Detecting the Unseen
description: An editorial research journal with a continuous photographic lake and inspectable simulation results.
colors:
  paper: "#f6f7f9"
  ink: "#14171f"
  mark: "#c42a68"
  dark-paper: "#0f1217"
  dark-ink: "#e8eaee"
  dark-mark: "#ee5f95"
  det-rule: "#2a78d6"
  det-pca: "#eb6834"
  det-iforest: "#1baf7a"
  analytics-rule: "#397bad"
  analytics-pca: "#b96d25"
  analytics-iforest: "#32806d"
  lake-base: "#273e4d"
  hero-ink: "#f8fafc"
  hero-mark: "#ff88b3"
typography:
  display:
    fontFamily: '"Archivo", "Segoe UI", system-ui, sans-serif'
    fontSize: "clamp(3rem, 6.4vw, 6rem)"
    fontWeight: 780
    lineHeight: 0.95
    letterSpacing: "-0.04em"
  body:
    fontFamily: '"STIX Two Text", "Cambria", Georgia, serif'
    fontSize: "1.125rem"
    lineHeight: 1.62
  mono:
    fontFamily: '"JetBrains Mono", ui-monospace, "Cascadia Mono", Consolas, monospace'
rounded:
  surface: "10px"
  pill: "999px"
  field: "6px"
spacing:
  gutter: "clamp(16px, 4vw, 48px)"
  margin-gap: "2.5rem"
components:
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    rounded: "{rounded.pill}"
    padding: "0.6rem 1.05rem"
  button-quiet:
    backgroundColor: "color-mix(in srgb, var(--paper) 70%, transparent)"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "0.6rem 1.05rem"
  filter-select:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.field}"
    padding: "0.6rem 2rem 0.6rem 0.8rem"
---

# Design System: Detecting the Unseen

## Overview

**Creative North Star: "A small disturbance has wider consequences"**

A research journal with a continuous photographic lake. The user replaced the terrain and eye concepts with a realistic falling drop, its rebound and expanding ripples. Water supplies atmosphere and a metaphor for consequences; the article, replay, charts and exact tables carry the evidence. Preserve the established editorial identity and distinction between simulated results and real-market claims.

**Key Characteristics:**
- Photographic slate-blue water, refractive motion and legible white hero type with pink emphasis.
- Quiet light and dark reading surfaces, serif prose, sturdy display type and tabular figures.
- Inspectable results with clear filters, uncertainty, exact tables and export.

## Colors

The palette combines cool paper and dark ink with restrained magenta. The normative journal tokens above come from `docs/assets/site.css`; that stylesheet also owns the complete dark-theme overrides. The hero overrides come from `docs/assets/lake.css`.

### Primary

Magenta identifies the manipulator, marked findings and title emphasis. The photographic hero uses brighter pink emphasis over water.

### Secondary

Detector families retain blue for Rule, orange for PCA, green for Isolation Forest and ink for LSTM. Analytics currently uses its own muted blue, orange and green values, recorded in the frontmatter, while preserving family meanings. Labels and filled versus outlined bars supplement colour; AUC intervals use whiskers.

### Neutral

Cool paper, ink and hairline dividers support extended reading in both themes. The slate-blue lake sits behind the hero and fades beneath reading content.

**The Evidence Rule.** Decorative water colour and geometry encode no experimental values.

## Typography

Archivo is the display and interface face, STIX Two Text the reading face, and JetBrains Mono the numerical face. Preserve the complete incumbent fallback stacks in the frontmatter. Tables use Archivo with tabular lining figures; numerical typography does not imply every number must use the mono face.

Hero titles use tight leading and balanced wrapping. Analytics uses an Archivo heading at weight 760, a responsive size from 2.5rem to 4rem and line-height 1. Body prose retains the frontmatter's reading size and line-height. Tight heading leading is intentional and must not spread to body text.

## Layout

The desktop article has a 42rem reading column, 15rem note margin and 2.5rem gap. At 1080px notes become tap-to-open disclosures. The replay stacks below 900px; navigation collapses at 820px. At 640px the schedule becomes a list with explicit completion dates and statuses. Tables scroll within their own containers.

The fixed lake fills the viewport across the journal and Analytics. Hero copy sits left and the drop right; below 900px the copy leaves a lower area for water. The journal's Analytics action stays visible when central navigation collapses. The Analytics shell has a maximum width of 1320px with two chart columns and a 2.6rem gap, becoming one column at 1000px. Filters wrap with explicit labels.

## Elevation & Depth

The lake photograph and refraction supply depth; chart panels remain flat with editorial rules. A dark directional wash protects hero copy. The replay retains the soft shadow from `site.css`. The top bar switches from a dark transparent hero treatment to paper after 48px of scrolling; a thin magenta line tracks reading progress.

The lake fades with scroll to 9% opacity beneath reading content and stays at 9% throughout Analytics. This is decorative continuity beneath the journal.

## Shapes

Pill silhouettes belong to controls and navigation. Selects have gently rounded corners; results panels and booktabs tables use horizontal rules. Elliptical waves are decorative perspective geometry, independent of the order-book replay and experiment values.

## Components

### Controls and navigation

Primary pills reverse ink and paper; quiet pills use translucent paper and a visible border. Hover changes the surface, active presses scale gently, and keyboard focus uses a visible two-pixel outline with a three-pixel offset. The lake hero overrides pill colours for contrast. Analytics uses native selects with a minimum height of 44px; Reset filters restores the initial selection.

### Lake scene

`docs/assets/lake.png` is the photographic source with embedded provenance. Preserve that metadata during asset processing. `lake.js` adds an accelerating drop, a smaller rebound, refraction, highlights and expanding elliptical waves in a nine-second cycle. It is decorative, not a fluid simulation or a chart, and is hidden from assistive technology.

Rendering targets approximately 30 frames per second with a 1.1-million-pixel budget and a device-pixel-ratio ceiling of 1.35. The fixed Pause motion control coordinates motion state. Reduced motion displays a still frame; hidden tabs suspend animation. Resize redraws the current frame. WebGL failure, shader failure or context loss leaves the photographic CSS fallback; texture-load failure also retains that background. The fixed scene continues beneath the article, so scrolling past the hero does not suspend it.

### Research figures and tables

The journal keeps six SVG charts backed by eight generated tables, with arrow-key chart tabs. Margin-note buttons retain a minimum 24px target and desktop notes remain in the margin. Progress distinguishes planned dates from actual completion dates and never infers completion from elapsed time.

### Analytics

Three filters select training market, spoof pattern and order size, making 20 combinations. Three SVG charts show detection versus honest-order flags, AUC with confidence intervals, and ordinary-market false alarms. A fourth panel reports the paired intervention's fill impact. False alarms depend only on training; impact depends only on pattern and size. State those dependencies beside the panels.

Exact values use semantic booktabs tables, scoped headers and local horizontal scrolling. Confidence intervals and sample counts remain inspectable. CSV export includes the selected detector results, intervals and sample counts at website-export precision. Fixed robustness, individual-order and time-resolution tables remain separate from the filtered comparison. Data comes from the generated `RESULTS` and `EXTENSIONS` objects, with repository sources stated beside outputs. Filter changes update a polite live interpretation. Claims remain preliminary and simulation-only.

## Do's and Don'ts

### Do:
- **Do** preserve the incumbent font stacks, light and dark themes, byline and detector meanings.
- **Do** keep water decorative and research numbers traceable to generated data.
- **Do** preserve pause, reduced motion, hidden-tab suspension, static fallback and table access.
- **Do** keep uncertainty, populations and filter dependencies visible beside results.

### Don't:
- **Don't** describe the lake as data-derived terrain or resurrect the superseded eye motif.
- **Don't** treat catch rate or anomaly scores as proof of manipulation or intent.
- **Don't** invent a repository URL, publication status or real-market validation.
- **Don't** remove embedded raster provenance during asset processing.
