// Virtual-camera math shared by PaperEpisode.tsx and the proof driver's
// zone-overlap check. One eased move per scene toward the scene's drawing
// centroid, zoom clamped so no drawing element ever enters the title zone
// (above TITLE_FLOOR) or the captions zone (below CAPTION_CEIL).
import {samplePath, pointAt} from './pathFollow.js';

export const TITLE_FLOOR = 385;
export const CAPTION_CEIL = 1560;
export const ANCHOR_Y = 1060;

export function pointsOf(laid) {
  const pts = [];
  if (laid) {
    for (const s of laid.strokes || []) {const samples = s.samples || samplePath(s.d); for (let k = 0; k <= 10; k++) pts.push(pointAt(samples, k / 10));}
    for (const f of laid.fills || []) {if (f.shape !== 'path' && typeof f.cx === 'number') {pts.push({x: f.cx, y: f.cy - (f.r || 0)}); pts.push({x: f.cx, y: f.cy + (f.r || 0)});}}
    for (const l of laid.labels || []) {pts.push({x: l.x1, y: l.y1}); pts.push({x: l.x2, y: l.y2 - 44});}
    for (const m of laid.marks || []) {pts.push({x: m.x, y: m.y - (m.r || 8) * 2}); pts.push({x: m.x, y: m.y + (m.r || 8) * 2});}
    for (const a of laid.annotations || []) {if (typeof a.x === 'number') {const rr = a.r || a.size || 60; pts.push({x: a.x, y: a.y - rr}); pts.push({x: a.x, y: a.y + rr});}}
  }
  return pts;
}

export function centroidOf(laid) {
  const pts = pointsOf(laid);
  if (!pts.length) return {x: 540, y: 1000};
  return {x: pts.reduce((a, p) => a + p.x, 0) / pts.length, y: pts.reduce((a, p) => a + p.y, 0) / pts.length};
}

export function safeZoomPts(pts, cy, want) {
  let s = want;
  for (const p of pts) {
    if (p.y < cy) s = Math.min(s, (ANCHOR_Y - TITLE_FLOOR) / Math.max(1, cy - p.y));
    if (p.y > cy) s = Math.min(s, (CAPTION_CEIL - ANCHOR_Y) / Math.max(1, p.y - cy));
  }
  return Math.max(1.02, s);
}

// Camera target per scene: zoom toward the scene centroid, with the scale
// AND the vertical anchor solved so every visible element stays between the
// title and captions zones at all times (including the 4% push-in peak).
// Falls back to a static frame (s=1) when the layout is too tall to zoom.
// Slow secondary drift (pro-motion spec: no fully static shot). Applied to
// the camera centre only; zone checks and the camera solver reserve DRIFT_Y.
export const DRIFT_X = 4, DRIFT_Y = 5;

export function camTargetsFor(windows, layers) {
  return windows.map((w, i) => {
    const c = centroidOf(layers[i]);
    const cy = Math.max(c.y, 620);
    const pts = layers.slice(0, i + 1).flatMap(pointsOf);
    const minY = Math.min(...pts.map(p => p.y), cy), maxY = Math.max(...pts.map(p => p.y), cy);
    const want = i === 0 ? 1.04 : 1.1;
    for (let s = want; s >= 1.0; s -= 0.02) {
      const sz = s * 1.045;
      const aLo = TITLE_FLOOR + DRIFT_Y + sz * (cy - minY);
      const aHi = CAPTION_CEIL - DRIFT_Y - sz * (maxY - cy);
      if (aLo <= aHi) return {x: c.x, y: cy, s, a: Math.min(Math.max(ANCHOR_Y, aLo), aHi)};
    }
    return {x: c.x, y: cy, s: 1, a: cy};
  });
}

export function camAt(fr, windows, camTargets, easing) {
  let i = windows.findIndex(w => fr < w.start + w.frames);
  if (i < 0) i = windows.length - 1;
  if (!windows.length) return {x: 540, y: ANCHOR_Y, s: 1};
  const w = windows[i];
  const to = camTargets[i], from = i > 0 ? camTargets[i - 1] : {x: 540, y: 1000, s: 1};
  const span = Math.min(30, Math.max(10, w.frames * 0.35));
  let p = Math.max(0, Math.min(1, (fr - w.start) / span));
  if (easing) p = easing(p);
  const push = Math.max(0, Math.min(1, (fr - w.start) / w.frames)) * 0.04;
  const s = (from.s + (to.s - from.s) * p) * (1 + push);
  const x = from.x + (to.x - from.x) * p, y = from.y + (to.y - from.y) * p;
  const a = (from.a !== undefined ? from.a : ANCHOR_Y) + ((to.a !== undefined ? to.a : ANCHOR_Y) - (from.a !== undefined ? from.a : ANCHOR_Y)) * p;
  return {x: x + Math.sin(fr / 45) * DRIFT_X, y: y + Math.cos(fr / 60) * DRIFT_Y, s, a};
}

// Zone check: every point of every visible layer, under every scene's
// settled camera (and its push-in peak), must stay between the title and
// captions zones. Returns a list of violations.
export function zoneViolations(windows, layers, camTargets) {
  const violations = [];
  camTargets.forEach((t, si) => {
    for (const mult of [1, 1.04]) {
      const s = t.s * mult;
      const anchor = t.a !== undefined ? t.a : ANCHOR_Y;
      layers.slice(0, si + 1).forEach((laid, li) => {
        for (const p of pointsOf(laid)) {
          const sy = anchor - s * (t.y - p.y);
          if (sy - DRIFT_Y < TITLE_FLOOR) violations.push(`scene ${si} camera puts layer ${li} point at y=${Math.round(sy)} - drift < ${TITLE_FLOOR}`);
          if (sy + DRIFT_Y > CAPTION_CEIL) violations.push(`scene ${si} camera puts layer ${li} point at y=${Math.round(sy)} + drift > ${CAPTION_CEIL}`);
        }
      });
    }
  });
  return violations;
}
