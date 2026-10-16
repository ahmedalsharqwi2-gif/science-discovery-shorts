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
```

`--width 720` and `--fps 24` are supported for low-cost previews; production defaults are 1080×1920 at 30 fps.

The JSON examples are six-second **visual fixtures**, not publishable factual episodes. For a real episode, the checked narration generator must supply the plan, source-grounded labels, scene data and captions timed against the final narration. The example drawings do not synthesize arbitrary new subjects automatically. New visual concepts require additional reviewed scene types or supplied assets.

## Audio boundary

TTS is upstream and replaceable. Supply a complete, quality-checked narration file; the renderer never invokes TTS or guesses a voice. Plan duration must agree with the real audio within 120 ms. Scenes must cover that duration without gaps or overlaps; caption timings must be ordered and within the audio. The exporter does not stretch narration, truncate it with `-shortest`, or add words to fit a template. H.264 video and AAC audio are written to a temporary output and promoted only after export verification.

## Adoption

The manual preview workflow only creates downloadable review artifacts. It does not dispatch publishing, write receipts, or fill stock. The existing production renderer and content, duplicate, audio/ASR, and subtitle checks stay in force.

Before selecting this renderer in the production pipeline:

1. Generate a complete source-checked plan for a new topic, with its approved narration and real word/sentence timings.
2. Review the exported sample, including Egyptian pronunciation, caption placement, scene relevance and duration.
3. Add a motion-specific visual quality check. An external B-roll share check is not applicable to procedural drawings; replace it with appropriate checks rather than disabling validation.
4. Run a full unpublished episode, then connect the validated output to the existing unique-topic reservation and receipt-confirmed publisher.

Do not infer that the voice in the Manus reference has been reproduced. Its recording is not a voice model, and the reference TTS service/voice ID remains unknown.
