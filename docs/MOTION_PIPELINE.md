# Local Canvas motion and Egyptian voice

The cinematic pipeline now has a domain-specific Canvas renderer selected by `config/cinematic_production.json` (`renderer: canvas`). It creates original animated diagrams locally in Chromium/Playwright and encodes 1080×1920, 30-fps scene clips (with a silent AAC compatibility track) using FFmpeg. The existing assembly step then adds the generated narration, timing-aligned Arabic captions, and the repository's existing audio mix. The quality gate requires at least 70% approved moving visuals; Canvas animations count as motion but are not mislabeled as source footage. Science, history, and horror share the same motion grammar but use different palettes and motifs; the art is labeled as illustrative, not documentary evidence.

## Local setup and preview

Install the repository's Python requirements (the history repository uses `scripts/requirements.txt`; science and horror use `requirements.txt`), install FFmpeg and Arabic Noto fonts, then install the matching browser:

```bash
python -m pip install -r requirements.txt  # use scripts/requirements.txt in documented-history-stories
python -m playwright install --with-deps chromium
```

Render a one-second preview without calling a visual-generation API:

```bash
python scripts/canvas_renderer.py \
  --profile science \
  --duration 1 \
  --text 'مثال على موضوع الحلقة' \
  --output /tmp/canvas-preview.mp4
```

Choose `science`, `history`, or `horror` to preview the corresponding art direction. Production inputs must still exist before running the repository's normal workflow: script generation, narration generation, then `python scripts/assemble_video.py`.

## Changing the visual style

Edit `assets/motion/canvas.html`: `drawScience`, `drawHistory`, and `drawHorror` are intentionally separate so each channel can gain its own motion and effects without changing the voice or assembly pipeline. `background()` controls shared particles, grid, and vignette; each draw function controls its subject motif, palette accents, and motion. Keep the authored stage at 1080×1920/30fps unless the canvas layout is rescaled too. The scene text and visual keywords seed small variations, so videos remain topic-aware without turning the layout into a different template each time.

## Voice profile

`assets/voices/octopus_narrator.wav` and `assets/voices/octopus_narrator.txt` are the approved reference audio and transcript. `assets/voices/voice_profiles.json` registers them as `octopus_narrator`; production defaults to `TTS_ENGINE=silma`, `SILMA_REFERENCE_PROFILE=octopus_narrator`, and `SILMA_SPEED=1.0`.

The speed is a new, adjustable baseline for these repositories—not a recovered setting from the original octopus MP4. No provider voice ID or original TTS model was recoverable. Automatic fallback to a different speaker is disabled so a failed SILMA run does not silently change the narrator; fix the SILMA issue or explicitly choose another profile if desired.

## Cost and scope

Canvas drawing, Chromium capture, FFmpeg encoding, and subtitle compositing are local steps and do not call a visual-generation API or use Manus media credits. The existing topic/script generation still uses each repository's configured LLM credentials, and voice synthesis uses its `silma-tts` dependency on the workflow runner; check that runtime's own compute/resource terms. No API keys are included in this repository change.
