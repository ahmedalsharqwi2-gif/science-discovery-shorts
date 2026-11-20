// pipeline/motion-qa.mjs - motion-energy QA (owner pro-motion spec 2/6):
// no scene may be visually static for > maxStaticSeconds. Samples one frame
// per second per scene and fails when a scene's mean grayscale frame-diff is
// below threshold. Runs on the rendered review.mp4; writes motion-qa.json.
import {spawnSync} from 'node:child_process';
import {writeFileSync} from 'node:fs';

function grayFrames(video, fps = 1) {
  const r = spawnSync('ffmpeg', ['-v', 'error', '-i', video, '-vf', `fps=${fps},scale=96:54,format=gray`, '-f', 'rawvideo', '-'], {maxBuffer: 1 << 28});
  if (r.status !== 0) throw Error('MOTION_QA_FFMPEG_FAILED');
  const frameBytes = 96 * 54;
  const frames = [];
  for (let o = 0; o + frameBytes <= r.stdout.length; o += frameBytes) frames.push(r.stdout.subarray(o, o + frameBytes));
  return frames;
}

export function motionEnergy(frames) {
  const diffs = [];
  for (let i = 1; i < frames.length; i++) {
    let sum = 0;
    for (let b = 0; b < frames[i].length; b++) sum += Math.abs(frames[i][b] - frames[i - 1][b]);
    diffs.push(sum / frames[i].length);
  }
  return diffs;
}

// scenes: [{duration}] in seconds. Returns per-scene mean diff; static when
// below minMeanDiff for the whole scene.
// Threshold calibration (2026-11-20): a truly static scene measures ~0.05-0.2
// at 96x54/1fps; the gentlest legitimate scene (slow intro with drift +
// captions) measured 1.0-1.3. 0.8 rejects static scenes with ~4x margin
// without false-flagging gentle ones.
export function check(video, scenes, {minMeanDiff = 0.8, out = null} = {}) {
  const frames = grayFrames(video);
  const diffs = motionEnergy(frames);
  const report = {schema: 1, method: 'grayscale frame-diff, 1 fps, 96x54', minMeanDiff, scenes: [], passed: true};
  let cursor = 0;
  scenes.forEach((s, i) => {
    const len = Math.max(1, Math.round(s.duration));
    const slice = diffs.slice(cursor, cursor + len - 1);
    cursor += len;
    const mean = slice.length ? slice.reduce((a, b) => a + b, 0) / slice.length : 0;
    const staticScene = slice.length > 0 && mean < minMeanDiff;
    if (staticScene) report.passed = false;
    report.scenes.push({scene: i, meanDiff: +mean.toFixed(3), static: staticScene});
  });
  if (out) writeFileSync(out, JSON.stringify(report, null, 2));
  return report;
}
