# Visual FX pipeline

The renderer now adds a deterministic, offline-safe finishing layer after the authored Three.js scene and text overlay. It uses camera-time easing hooks, parallax/depth treatment, sparse particles, vignette, color grading, a light sweep, and bounded film grain. It does not add branding, external assets, or network calls. The effect layer is intentionally subtle so Arabic captions, source evidence, and factual diagrams remain readable.

`window.visualFXStatus` records the active engines in `render.json`; if the layer is unavailable, the authored renderer remains usable as a safe fallback.
