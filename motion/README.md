# Shared Arabic channel renderer

One engine owns Arabic text layout, caption timing, the 9:16 canvas and MP4 export. Each channel has a separate scene module:

| Channel | Scene types |
| --- | --- |
| science | cells, signals, illustrative layers |
| history | supplied timelines, illustrative documents, explicitly schematic routes |
| horror | corridor, moving shadow, gradual reveal |

The canonical implementation lives in `science-discovery-shorts/motion`. Other repositories check it out at a reviewed commit SHA. Do not maintain three diverging copies of the engine.

## Run

Node.js 22+, FFmpeg/ffprobe, and an Arabic font are required. No browser, external rendering service, or rendering API is used.

```sh
cd motion
npm ci
node render.mjs --plan examples/science.json --frame 3 --font /path/to/NotoSansArabic-Regular.ttf --out preview.png
node render.mjs --plan /path/to/episode.json --audio /path/to/narration.wav --font /path/to/NotoSansArabic-Regular.ttf --out episode.mp4
node render.mjs --episode /path/to/checked-episode.json --timings /path/to/captions.srt --channel science --audio /path/to/narration.wav --save-plan /path/to/plan.json --font /path/to/NotoSansArabic-Regular.ttf --out episode.mp4
```

`--width 720` and `--fps 24` are supported for low-cost previews; production defaults are 1080×1920 at 30 fps.

The JSON examples are six-second **visual fixtures**, not publishable factual episodes. For a real episode, the upstream checked narration generator supplies `title` and `narration` (or `topic` and `narration_script`) and the final audio. `plan.mjs` builds a plan from real SRT sentence cues or JSON alignment entries `{text,start,end}` / `{text,offset,duration}`. Every normalized narration word must be present, in order; no guessed timings or invented text are accepted. Sentence cues keep their original boundaries; word cues are grouped into up to five words. This checks coverage and timing, not factual correctness or ASR quality, which remain upstream checks.

Science selects cells/signals/layers only for matching narration keywords, includes the user-provided octopus drawing for octopus topics, and otherwise uses concept labels drawn from the text. History uses illustrative documents and only renders timelines when `historical_events` with checked labels/dates are supplied. Horror progresses from corridor to shadows and reveal. A narration hash varies procedural parameters. These templates do not synthesize arbitrary new creatures, archaeology or photoreal footage. New visual concepts require additional reviewed scene types or supplied assets.

## Audio boundary

TTS is upstream and replaceable. Supply a complete, quality-checked narration file; the renderer never invokes TTS or guesses a voice. Plan duration must agree with the real audio within 120 ms. Scenes must cover that duration without gaps or overlaps; caption timings must be ordered and within the audio. The exporter does not stretch narration, truncate it with `-shortest`, or add words to fit a template. H.264 video and AAC audio are written to a temporary output and promoted only after export verification.

## Adoption

The manual preview workflow only creates downloadable review artifacts. It does not dispatch publishing, write receipts, or fill stock. The existing production renderer and content, duplicate, audio/ASR, and subtitle checks stay in force.

Before selecting this renderer in the production pipeline:

1. Feed the existing source-checked episode and approved narration's real word/sentence timings into the automatic planner. Supply checked historical event metadata when a timeline is needed.
2. Review the exported sample, including Egyptian pronunciation, caption placement, scene relevance and duration.
3. Add a motion-specific visual quality check. An external B-roll share check is not applicable to procedural drawings; replace it with appropriate checks rather than disabling validation.
4. Run a full unpublished episode, then connect the validated output to the existing unique-topic reservation and receipt-confirmed publisher.

Do not infer that the voice in the Manus reference has been reproduced. Its recording is not a voice model, and the reference TTS service/voice ID remains unknown.

The octopus scene is adapted from the user's supplied `octopus-colour-change-project.zip` / Canvas source. It does not call Manus or an image-generation API.
