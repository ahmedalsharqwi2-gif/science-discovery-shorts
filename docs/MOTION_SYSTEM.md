# Motion design system (pro-motion)

Tokens: `brand/motion-tokens.json` - canvas (1080x1920@30, 90-180 s), safe area (top 150 / bottom 250 px, title floor 385, caption ceiling 1560), themes, motion durations and stagger, type scale, transitions, sound targets. Everything visual reads from here.

## Themes
- `paper-technical` (default): cream paper #EDE4D0, dark ink #1A1512, grid #D8CBB2. Exact values previously hardcoded in PaperEpisode.
- `blueprint-dark` (أسرار الكون primary): navy paper #0C1B2E, pale ink #DCEAF7, faint grid #1B3350, cyan #4FC3E8, gold accent #E3B23C.
PaperEpisode rebinds its palette from `props.paper.theme`; unknown names fall back to paper-technical. The original logo in brand/logo/ is used as-is, never redrawn.

## Director
`director/storyboard.mjs` turns episode scenes into `storyboard.json` before render: template per scene by information type (phenomenon -> technical-illustration, stat -> big-number, comparison, cause -> flow-diagram, journey -> map-or-timeline, quote -> quote-card), keyword emphasis list, transition plan (morph / zoom-through / mask-reveal / wipe-shape cycling), and the no-adjacent-repeat rule with an audited swap note. `validateStoryboard` gates the render.

## Motion QA
`pipeline/motion-qa.mjs` samples the rendered video at 1 fps (64x36 grayscale) and fails the episode when any scene's mean frame-diff is below threshold (static scene check, spec 2/6). Pure functions are unit-tested; `check()` writes motion-qa.json.

## Existing engine pieces this builds on
Zone-safe virtual camera (src/paper/camera.js), kinetic word-pop captions, annotation ops (circle/arrow/x/magnifier/pip), hatch fills, drawplan validation (pipeline/drawplan.mjs).

## Adding a template
Map the scene kind in TEMPLATE_BY_KIND, add a fallback to FALLBACK_CYCLE if it may repeat, and keep every visual value in motion-tokens.json, not in components.

## Render budget
Daily production starts 06:00 and must finish before 11:00; full render target <= 90 min on GitHub Actions. Current slice timings are reported honestly in the final report; no blur/shadow on large areas, assets cached.
