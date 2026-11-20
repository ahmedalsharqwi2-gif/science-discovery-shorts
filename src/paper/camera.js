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
    for (const l of laid.labels || []) {
      pts.push({x: l.x1, y: l.y1}); pts.push({x: l.x2, y: l.y2 - 44});
      // RTL label text is end-anchored at x2 and extends LEFT by its width.
      const tw = (String(l.text || '').length) * 22;
      pts.push({x: l.x2 - tw, y: l.y2 - 44});
    }
    for (const m of laid.marks || []) {pts.push({x: m.x, y: m.y - (m.r || 8) * 2}); pts.push({x: m.x, y: m.y + (m.r || 8) * 2});}
    for (const a of laid.annotations || []) {
      if (a.type === 'pip') {
        const w = a.w || 300, h = a.h || 220;
        pts.push({x: a.x - w / 2, y: a.y - h / 2}); pts.push({x: a.x + w / 2, y: a.y + h / 2});
      } else if (a.type === 'arrow') {
        pts.push({x: a.x1, y: a.y1}); pts.push({x: a.x2, y: a.y2});
      } else if (a.type === 'magnifier') {
        const r = a.r || 120;
        pts.push({x: a.x - r, y: a.y - r}); pts.push({x: a.x + r * 1.35, y: a.y + r * 1.35});
      } else if (typeof a.x === 'number') {
        const rr = a.r || a.size || 60;
        pts.push({x: a.x - rr, y: a.y - rr}); pts.push({x: a.x + rr, y: a.y + rr});
      }
    }
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
// Horizontal safe margins: no drawing element may cross the left/right frame
// edge (pro-motion slice review 2026-11-20: pip card + labels clipped).
export const EDGE_X = 26, FRAME_W = 1080;

export function camTargetsFor(windows, layers) {
  return windows.map((w, i) => {
    const c = centroidOf(layers[i]);
    const cy = Math.max(c.y, 620);
    const pts = layers.slice(0, i + 1).flatMap(pointsOf);
    const minY = Math.min(...pts.map(p => p.y), cy), maxY = Math.max(...pts.map(p => p.y), cy);
    const minX = Math.min(...pts.map(p => p.x), c.x), maxX = Math.max(...pts.map(p => p.x), c.x);
    const want = i === 0 ? 1.04 : 1.1;
    for (let s = want; s >= 1.0; s -= 0.02) {
      const sz = s * 1.045;
      const aLo = TITLE_FLOOR + DRIFT_Y + sz * (cy - minY);
      const aHi = CAPTION_CEIL - DRIFT_Y - sz * (maxY - cy);
      if (aLo > aHi) continue;
      // Clamp camera x so every element stays inside the side edges at this
      // scale (including push-in peak and drift). Screen x = 540 + sz*(px - tx).
      const half = (FRAME_W / 2 - EDGE_X - DRIFT_X) / sz;
      const xLo = maxX - half, xHi = minX + half;
      const tx = xLo <= xHi ? Math.min(Math.max(c.x, xLo), xHi) : c.x;
      return {x: tx, y: cy, s, a: Math.min(Math.max(ANCHOR_Y, aLo), aHi)};
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
// Label text box in drawing coords: RTL text is end-anchored at (x2, y2),
// extends LEFT by width and sits in the 44px band above the anchor point.
// Width factor 24/char + 8px margin: calibrated against rendered labels
// (slice review 2026-11-20: adjacent labels overlapped on screen).
export function labelBoxesOf(laid) {
  return (laid && laid.labels || []).map(l => {
    const tw = String(l.text || '').length * 24 + 8;
    return {text: String(l.text || ''), x0: l.x2 - tw, x1: l.x2, y0: l.y2 - 56, y1: l.y2 + 4};
  });
}

// End card: the endStat headline must fit one line at the readability floor.
// Matches the EndCard auto-shrink in PaperEpisode (0.60em per Arabic glyph,
// 880px usable width, 110px cap). Flag when the required size drops under 64.
export function endCardProblems(plan) {
  const stat = String(plan && plan.endStat || '');
  if (!stat) return [];
  const fs = Math.min(110, Math.floor(880 / (stat.length * 0.6)));
  return fs < 64 ? [`end card headline "${stat}" needs fontSize ${fs} (< 64 floor); shorten it`] : [];
}

// Stroke/ring samples in drawing coords (for the label-clearance gate and
// auto-layout). Annotation circles become ring samples; arrows, pips, marks
// and fills are excluded by design (labels may anchor near marks, and fills
// like the hatch region are intended label backgrounds).
export function strokeSamplesOf(laid) {
  const pts = [];
  if (!laid) return pts;
  for (const st of laid.strokes || []) {
    const samples = st.samples || samplePath(st.d);
    const r = (st.width || 4) / 2 + 10; // half stroke + clearance
    for (let k = 0; k <= 20; k++) {const p = pointAt(samples, k / 20); pts.push({x: p.x, y: p.y, r});}
  }
  for (const a of laid.annotations || []) {
    if (a.type === 'circle') {
      const rr = a.r || 110, r = 4 / 2 + 10;
      for (let k = 0; k < 24; k++) {const th = k / 24 * Math.PI * 2; pts.push({x: a.x + Math.cos(th) * rr, y: a.y + Math.sin(th) * rr, r});}
    }
  }
  return pts;
}

// Label boxes include the backing-pill padding (slice review 2026-11-20 3:07:
// labels get halo pills; text-on-stroke counts as overlap).
export function labelStrokeViolations(layers) {
  const boxes = layers.flatMap((laid, li) => labelBoxesOf(laid).map(b => ({...b, li, x0: b.x0 - 14, x1: b.x1 + 14, y0: b.y0 - 12, y1: b.y1 + 12})));
  const out = [], seen = new Set();
  layers.forEach((laid, li) => {
    for (const p of strokeSamplesOf(laid)) {
      for (const b of boxes) {
        if (p.x > b.x0 - p.r && p.x < b.x1 + p.r && p.y > b.y0 - p.r && p.y < b.y1 + p.r) {
          const key = b.text + '|' + li;
          if (!seen.has(key)) {seen.add(key); out.push(`label "${b.text}" (layer ${b.li}) sits on a stroke/ring of layer ${li} near (${Math.round(p.x)},${Math.round(p.y)})`);}
        }
      }
    }
  });
  return out;
}

// Deterministic label auto-layout: grid-search a collision-free home for
// each label (label-label with min gap, label-stroke clearance, canvas edges,
// leader length cap), preferring spots near the anchor point. Similarity
// cameras preserve overlap, so all checks run in drawing coords.
export function autoLayoutLabels(plan, opts = {}) {
  const layers = [{strokes: plan.strokes, fills: plan.fills, marks: plan.marks, labels: plan.labels, annotations: plan.annotations}, ...(plan.scenes || [])];
  const placed = []; // accepted boxes
  const moved = [];
  const allLabels = [];
  layers.forEach((laid, li) => (laid.labels || []).forEach(l => allLabels.push({l, li})));
  // Most-constrained-first: the widest labels get first pick of free space.
  allLabels.sort((a, b) => String(b.l.text || '').length - String(a.l.text || '').length);
  const strokePts = layers.flatMap(l => strokeSamplesOf(l));
  const hitStrokes = b => strokePts.some(p => p.x > b.x0 - p.r && p.x < b.x1 + p.r && p.y > b.y0 - p.r && p.y < b.y1 + p.r);
  const hitLabels = b => placed.some(A => A.x0 - 8 < b.x1 && b.x0 - 8 < A.x1 && A.y0 - 8 < b.y1 && b.y0 - 8 < A.y1);
  for (const {l} of allLabels) {
    const text = String(l.text || '');
    const tw = text.length * 24 + 8;
    // Gate-identical box (labelBoxesOf + pill/stroke inflation).
    const boxAt = (x2, y2) => ({x0: x2 - tw - 14, x1: x2 + 14, y0: y2 - 68, y1: y2 + 16});
    // Camera-safe band: scene cameras shift x around the centroid, so labels
    // must sit well inside the frame in drawing coords.
    const ok = b => b.x0 >= 120 && b.x1 <= 960 && b.y0 >= TITLE_FLOOR + 10 && b.y1 <= CAPTION_CEIL - 10 && !hitStrokes(b) && !hitLabels(b);
    let chosen = null;
    const cur = boxAt(l.x2, l.y2);
    if (ok(cur)) chosen = {x2: l.x2, y2: l.y2, cost: 0};
    else {
      let best = null;
      for (let y2 = TITLE_FLOOR + 70; y2 <= CAPTION_CEIL - 30 && !chosen; y2 += 16) {
        for (let x2 = 120 + tw + 14; x2 <= 960 - 14; x2 += 16) {
          const lead = Math.abs(x2 - l.x1) + Math.abs(y2 - l.y1);
          if (lead > 920) continue;
          const b = boxAt(x2, y2);
          if (!ok(b)) continue;
          const cost = lead + Math.abs(x2 - l.x2) * 0.5 + Math.abs(y2 - l.y2) * 0.5;
          if (!best || cost < best.cost) best = {x2, y2, cost};
        }
      }
      chosen = best;
    }
    if (!chosen) {moved.push(`NO_HOME: ${text}`); continue;}
    if (chosen.x2 !== l.x2 || chosen.y2 !== l.y2) {moved.push(`${text}: (${l.x2},${l.y2}) -> (${chosen.x2},${chosen.y2})`); l.x2 = chosen.x2; l.y2 = chosen.y2;}
    placed.push(boxAt(l.x2, l.y2));
  }
  return moved;
}

export function zoneViolations(windows, layers, camTargets) {
  const violations = [];
  violations.push(...labelStrokeViolations(layers));
  camTargets.forEach((t, si) => {
    // Label-to-label collision gate: every pair of label boxes visible during
    // this scene (layers accumulate) must not overlap on screen, using the
    // settled camera at its push-in peak, with drift margin.
    {
      const s = t.s * 1.04, anchor = t.a !== undefined ? t.a : ANCHOR_Y;
      const M = 8; // min-gap enforcement: boxes inflated so <16px gaps flag
      const toScreen = b => ({
        x0: FRAME_W / 2 + s * (b.x0 - M - t.x) - DRIFT_X, x1: FRAME_W / 2 + s * (b.x1 + M - t.x) + DRIFT_X,
        y0: anchor - s * (t.y - b.y0 - M) - DRIFT_Y, y1: anchor - s * (t.y - b.y1 + M) + DRIFT_Y,
      });
      const boxes = layers.slice(0, si + 1).flatMap((laid, li) => labelBoxesOf(laid).map(b => ({...b, li})));
      for (let i = 0; i < boxes.length; i++) for (let j = i + 1; j < boxes.length; j++) {
        const A = toScreen(boxes[i]), B = toScreen(boxes[j]);
        if (A.x0 < B.x1 && B.x0 < A.x1 && A.y0 < B.y1 && B.y0 < A.y1) violations.push(`scene ${si} labels collide: "${boxes[i].text}" (layer ${boxes[i].li}) x "${boxes[j].text}" (layer ${boxes[j].li})`);
      }
    }
    for (const mult of [1, 1.04]) {
      const s = t.s * mult;
      const anchor = t.a !== undefined ? t.a : ANCHOR_Y;
      layers.slice(0, si + 1).forEach((laid, li) => {
        for (const p of pointsOf(laid)) {
          const sy = anchor - s * (t.y - p.y);
          if (sy - DRIFT_Y < TITLE_FLOOR) violations.push(`scene ${si} camera puts layer ${li} point at y=${Math.round(sy)} - drift < ${TITLE_FLOOR} (draw ${Math.round(p.x)},${Math.round(p.y)})`);
          if (sy + DRIFT_Y > CAPTION_CEIL) violations.push(`scene ${si} camera puts layer ${li} point at y=${Math.round(sy)} + drift > ${CAPTION_CEIL} (draw ${Math.round(p.x)},${Math.round(p.y)})`);
          const sx = FRAME_W / 2 + s * (p.x - t.x);
          if (sx - DRIFT_X < EDGE_X) violations.push(`scene ${si} camera puts layer ${li} point at x=${Math.round(sx)} - drift < left edge ${EDGE_X}`);
          if (sx + DRIFT_X > FRAME_W - EDGE_X) violations.push(`scene ${si} camera puts layer ${li} point at x=${Math.round(sx)} + drift > right edge ${FRAME_W - EDGE_X}`);
        }
      });
    }
  });
  return violations;
}
