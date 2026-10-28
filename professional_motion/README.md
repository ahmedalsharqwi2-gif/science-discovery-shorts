# Professional octopus proof

An isolated science film, with eight purpose-designed scenes. This is a review candidate, not a claim that artistic quality has surpassed a reference.

The film uses a procedurally modelled octopus, physical lighting, a changing chromatophore skin shader, a microscopic pigment sac with radial muscles, travelling nerve impulses, exploded skin layers, underwater particles and a camouflage scene. Arabic typography is drawn separately at native 1080×1920. Music is an original 112 BPM arrangement of pads, arpeggios, bass, percussion and timed scene swells. No reference audio is reused.

## Generate inside GitHub Actions

The `Professional octopus proof` workflow runs on the dedicated `codex/professional-octopus-proof` branch when its workflow file changes, and can also be manually dispatched where GitHub exposes it. The workflow generates/reuses Charon narration with the repository's existing Gemini secrets, measures Arabic scene and phrase anchors with ASR, renders frames in Chromium, mixes the sound and saves review artifacts. It never publishes to social channels and does not alter `main`.

Generated narration is delivered to a separate run-specific `codex/octopus-review-run-<id>` branch so review can continue through normal Git when the cloud instance cannot reach GitHub's Actions API. That branch contains generated voice/media metadata only, never secrets. Finished films are Actions artifacts, not source commits.

## Render a measured local review

From repository root, with generated `professional_motion/delivery/narration.wav`, `narration.source.json` and `timing.json`:

```sh
cd professional_motion
npm ci
npx playwright-core install chromium
cd ..
node professional_motion/render.mjs --stills
node professional_motion/render.mjs
python -m professional_motion.finish
```

The renderer uses a system Chromium when available, otherwise Playwright's installed Chromium; `CHROMIUM_PATH` can select an executable. Rendering is deterministic, at 1080×1920 / 30fps. Any page or shader error stops encoding. An audio-free render is explicitly labelled as a visual study and cannot pass the final mixing step.

Review files: `professional_motion/output/octopus-professional-review.mp4`, `verification.json`, `visual-quality.json`, `score.json` and the eight still frames. Frame checks reject blank/frozen diagrams; audio-tail correlation detects lost speech. These are technical checks, not an independent fact check or aesthetic approval. Phrase captions use the supplied script between measured anchors; no word-perfect highlighting is claimed. The factual brief is based on Smithsonian Ocean and the diagrams simplify the mechanisms.

The current proof is specific to the octopus topic. Other channels need their own authored visual scenes; swapping titles alone is not a supported adaptation.
