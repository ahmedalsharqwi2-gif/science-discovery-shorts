# Hybrid review samples — science and history

This is an isolated, review-only integration. No production workflow, schedule, publication configuration, topic ledger or post ID is changed. It never calls text, voice, image or publishing providers. Owner approval is pending; the daily renderer is not switched to this branch.

## Actual engine chain

- Science: the preserved `professional_motion.proceduralDirector` builds authored Three.js geometry; `scienceCinema` supplies camera/light movement. Added explicit surfactant and micelle shapes with heads outward and tails toward oil. A separate bounded browser capture produces a muted clip; Remotion assembles it with readable Arabic captions, semantic overlays and an original science sound mix. Illustration only, not measured simulation.
- History: the preserved `photo_motion.engine.Renderer.shot` produces camera motion and image transitions from three exact public-domain archival images of Abu Simbel and the UNESCO campaign. A separate `ArchiveReview` adapter only renders review frames: it does not modify or manufacture the original production contract's human approval fields. Remotion supplies typography, measured captions and its own historical score.

The examples reuse known episodes so visual changes can be judged against the same original voice. They are review excerpts, not new daily episodes. Science source interval: 34.30–68.86 seconds (34.56 seconds). History: 0–29.02 seconds. Narration PCM samples retain their original speed and pitch; the final mix changes loudness only and ducks music beneath speech. Two separate original musical arrangements and event-timed effects replace the common score. Captions at excerpt edges were manually reconciled with retained word timing to avoid cutting a word or displaying the next sentence.

## Reproduce without generating or sending anything

Use the repository's pinned `professional_motion` and `remotion_motion` npm installations, FFmpeg, Python, Pillow (with libraqm), and NumPy. Chromium is selected explicitly; change `/usr/bin/chromium` only for your system's installed path.

Provide a retained root containing `full-delivery/science/professional_motion/delivery/` and `full-delivery/history/professional_motion/delivery/`, each with the original `story.json`, `timing.json`, `narration.wav`, and `narration.source.json`. Provide a Remotion toolchain directory containing its installed node_modules, package.json, lockfile, tsconfig.json, fonts, assets.json and the already hash-verified archival images under public/media. These are explicit input paths, never substituted with new provider requests.

```bash
python hybrid_review/prepare_review.py --retained-root /path/to/retained --repo-root . --toolchain-root /path/to/remotion-toolchain
node hybrid_review/test_geometry.mjs
python hybrid_review/render_photos.py
node hybrid_review/render_three.mjs
python hybrid_review/make_audio.py
cd hybrid_review/studio
npx tsc --noEmit
node render-review.mjs science --stills
node render-review.mjs history --stills
node render-review.mjs science
node render-review.mjs history
cd ..
python finalize_audio.py
python check_review.py science history
```

The Studio uses `npm run studio -- --port=3012`. The two compositions are `ScienceHybrid` and `HistoryHybrid`; the other production project is unchanged. The final FFmpeg mux copies the existing picture stream and binds the exact-duration 48 kHz mix, compensating limiter latency without any visual re-render. Both clips must complete before Remotion renders; an unfinished MP4 must never be consumed.

## Evidence and approval

`output/*-verification.json` retains full-decode checks, geometry, exact source voice/script hashes, PCM excerpt hashes and sample intervals, caption bounds, final movie hashes, actual encoded frame samples and audio levels. It explicitly records artist approval as pending. `output/history-assets.json` retains source/license/author evidence. Media is delivered privately through the previously authorized Google Drive review destination; no social publication calls or new publication receipts exist for these samples.

All five daily publication records and existing schedules remain on main. Generalization requires the owner's visual approval of these two distinct samples.
