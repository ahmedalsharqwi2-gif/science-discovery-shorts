# Science production v2 — opt-in review renderer

The new renderer is selected explicitly with `--pipeline v2`. Omitting it retains the legacy renderer and daily workflow. No topic registry, video fingerprint, publication receipt, or approved channel destination is rewritten by this change.

Science v2 adds deterministic eased truck, crane and dolly paths for eight authored shots, a cool rim and neutral key light, restrained exposure and a sparse depth backdrop. The sourced earth-magnetosphere episode additionally gets a dedicated qualitative scientific stage: analytic dipole loops and deflected solar-wind particles, an Earth/Mars comparison, a reconnection illustration, and exactly four schematic MMS spacecraft in a tetrahedral formation. These diagrams are not quantitative field models or to-scale orbits. Other topics retain their authored subject meshes and geometric contracts. Scene timing, captions, source labels and safe branding remain authoritative. No stock imagery or substitute logo is invented.

## Isolated technical validation

From this repository root:

```sh
node professional_motion/render.mjs --pipeline v2 --style reference --review \
  --delivery-dir /workspace/setup/science-v2/delivery \
  --output-dir /workspace/setup/science-v2/full
python -m professional_motion.finish --pipeline v2 --validation-kind archived-topic \
  --delivery-dir /workspace/setup/science-v2/delivery \
  --output-dir /workspace/setup/science-v2/full
```

The isolated delivery contains the archived 162.36-second `earth-magnetosphere` episode, original narration and measured timing from `codex/professional-review-run-41055103244`. The downloaded story and narration match the hashes in the measured timing. This is a technical rerender of an already published topic, marked as review-only; it must never be submitted as today's fresh film or counted as fresh-topic cutover acceptance. It does not replace any published media.

The one-second 1080×1920, 30fps H.264 benchmark rendered successfully with the new pipeline. Its frame was inspected: the reference overlay and Arabic caption stay separated from the globe/field illustration; missing original science logo remains explicitly missing. Five representative stills spanning beginning, middle and end were inspected: scene-specific Earth/Mars, reconnection and four-spacecraft illustrations are visible; Arabic captions remain in their separate safe panel. Full-film validation is recorded separately only when completed.

## Checks

- `python -m pytest -q tests/test_science_v2.py tests/test_professional_motion.py tests/test_visual_subjects.py`: 12 passed.
- `node --test professional_motion/science_field.test.mjs professional_motion/science_shots.test.mjs`: passed (four scene/shot checks, reported as two files by the environment's Node runner).
- JavaScript syntax checks and Python finalizer compilation: passed.
- Existing `tests/test_reference_style.py` has an unrelated failure: it calls `json.loads()` on the YAML daily workflow. The workflow is intentionally not changed by this renderer opt-in.

The original PNG/JPG science logo was not attached; no replacement was drawn. New topic generation still needs configured Gemini credentials. Legacy scheduling defects reported during onboarding are not silently patched or activated by this visual branch; the migration controller must gate activation and prevent simultaneous scheduling.
