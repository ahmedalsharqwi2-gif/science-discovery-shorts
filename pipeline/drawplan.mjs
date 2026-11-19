// drawplan.mjs - plans the paper-style drawing spec for one episode.
// One Gemini text call turns the episode's scenes into ONE persistent
// drawing (paper grammar: ink strokes, then color fills, marks, callout
// labels) plus per-scene ADD operations, an end-card stat and summary.
// Validation mirrors script(): strict checks with retry feedback, 3
// attempts, diagnostics on failure. No drawing ships unvalidated.

import {writeFile} from 'node:fs/promises';
import {provider} from './provider-client.mjs';

export const CANVAS = {width: 1080, height: 1920};
// Drawing area keeps the question title (top ~360px) and the caption zone
// (bottom ~420px) clear.
export const DRAW_BOX = {x0: 40, y0: 380, x1: 1040, y1: 1500};
export const PALETTE = ['ink', 'paper', 'red', 'blue', 'cyan', 'gold', 'white', 'starBlue', 'green'];

const CAPS = {strokes: 90, fills: 50, marks: 40, baseLabels: 5, sceneLabels: 3, perSceneOps: 14, annotations: 10, perSceneAnnotations: 2};

const strokeSchema = {type: 'OBJECT', required: ['d'], properties: {d: {type: 'STRING'}, width: {type: 'NUMBER'}, color: {type: 'STRING'}, delay: {type: 'NUMBER'}}};
const fillSchema = {type: 'OBJECT', required: ['color'], properties: {shape: {type: 'STRING', enum: ['circle', 'path']}, d: {type: 'STRING'}, cx: {type: 'NUMBER'}, cy: {type: 'NUMBER'}, r: {type: 'NUMBER'}, color: {type: 'STRING'}, opacity: {type: 'NUMBER'}, delay: {type: 'NUMBER'}, hatch: {type: 'BOOLEAN'}}};
const markSchema = {type: 'OBJECT', required: ['x', 'y'], properties: {x: {type: 'NUMBER'}, y: {type: 'NUMBER'}, r: {type: 'NUMBER'}, color: {type: 'STRING'}, delay: {type: 'NUMBER'}}};
const labelSchema = {type: 'OBJECT', required: ['x1', 'y1', 'x2', 'y2', 'text'], properties: {x1: {type: 'NUMBER'}, y1: {type: 'NUMBER'}, x2: {type: 'NUMBER'}, y2: {type: 'NUMBER'}, text: {type: 'STRING'}, align: {type: 'STRING', enum: ['start', 'middle', 'end']}, delay: {type: 'NUMBER'}}};
const annotationSchema = {type: 'OBJECT', required: ['type'], properties: {type: {type: 'STRING', enum: ['circle', 'arrow', 'x', 'magnifier', 'pip']}, x: {type: 'NUMBER'}, y: {type: 'NUMBER'}, r: {type: 'NUMBER'}, zoom: {type: 'NUMBER'}, x1: {type: 'NUMBER'}, y1: {type: 'NUMBER'}, x2: {type: 'NUMBER'}, y2: {type: 'NUMBER'}, size: {type: 'NUMBER'}, w: {type: 'NUMBER'}, h: {type: 'NUMBER'}, width: {type: 'NUMBER'}, color: {type: 'STRING'}, text: {type: 'STRING'}, d: {type: 'STRING'}, delay: {type: 'NUMBER'}}};
const opsSchema = {type: 'OBJECT', properties: {strokes: {type: 'ARRAY', items: strokeSchema}, fills: {type: 'ARRAY', items: fillSchema}, marks: {type: 'ARRAY', items: markSchema}, labels: {type: 'ARRAY', items: labelSchema}, annotations: {type: 'ARRAY', items: annotationSchema}}};
const planResponseSchema = {type: 'OBJECT', required: ['strokes', 'fills', 'marks', 'labels', 'scenes', 'endStat', 'summaryPoints'], properties: {
  strokes: {type: 'ARRAY', items: strokeSchema},
  fills: {type: 'ARRAY', items: fillSchema},
  marks: {type: 'ARRAY', items: markSchema},
  labels: {type: 'ARRAY', items: labelSchema},
  annotations: {type: 'ARRAY', items: annotationSchema},
  scenes: {type: 'ARRAY', items: opsSchema},
  endStat: {type: 'STRING'},
  summaryPoints: {type: 'ARRAY', items: {type: 'STRING'}},
}};

// Parses an absolute-coordinate path using only M/L/C/Z commands.
// Returns {ok, error, pointCount}.
export function parsePath(d) {
  if (typeof d !== 'string' || !d.trim()) return {ok: false, error: 'empty path'};
  const tokens = d.match(/[MLCZmlcz]|-?\d+(?:\.\d+)?|[,]/g) || [];
  if (tokens.join('').replace(/[\s,]/g, '').length !== d.replace(/[\s,]/g, '').length) return {ok: false, error: 'unsupported tokens in path: ' + d.slice(0, 60)};
  let i = 0, points = 0;
  const num = () => {
    if (i >= tokens.length || !/^-?\d/.test(tokens[i])) throw Error('expected number at token ' + i);
    const v = Number(tokens[i++]);
    if (i < tokens.length && tokens[i] === ',') i++;
    return v;
  };
  const coord = (isX) => {
    const v = num();
    const [lo, hi] = isX ? [0, CANVAS.width] : [0, CANVAS.height];
    if (v < lo || v > hi) throw Error((isX ? 'x' : 'y') + '=' + v + ' outside canvas ' + lo + '..' + hi);
    points++;
  };
  try {
    let closed = false;
    while (i < tokens.length) {
      const cmd = tokens[i++];
      if (cmd === ',' || cmd === undefined) throw Error('unexpected token ' + cmd);
      if (/[mlcz]/.test(cmd)) throw Error('relative command ' + cmd + ' not allowed; use absolute M/L/C/Z');
      if (!/^[MLCZ]$/.test(cmd)) throw Error('unsupported command ' + cmd + '; use M/L/C/Z only');
      if (cmd === 'Z') {closed = true; continue;}
      const arity = cmd === 'C' ? 6 : 2;
      if (closed) throw Error('commands after Z');
      const pairs = arity / 2;
      for (let p = 0; p < pairs; p++) {coord(true); coord(false);}
    }
    return {ok: true, pointCount: points};
  } catch (e) {
    return {ok: false, error: String(e && e.message || e)};
  }
}

const colorOk = (c) => c === undefined || PALETTE.includes(c) || /^#[0-9a-fA-F]{6}$/.test(c);
const inBox = (x, y) => x >= DRAW_BOX.x0 && x <= DRAW_BOX.x1 && y >= DRAW_BOX.y0 && y <= DRAW_BOX.y1;

// Validates a planned spec against the paper grammar and canvas rules.
// Returns an array of human-readable problems; empty array means valid.
export function validatePlan(plan, sceneCount) {
  const problems = [];
  if (!plan || typeof plan !== 'object') return ['plan is not an object'];
  const ops = ['strokes', 'fills', 'marks', 'labels', 'annotations'];
  for (const k of ops.slice(0, 4)) if (!Array.isArray(plan[k])) problems.push(k + ' must be an array');
  if (plan.annotations === undefined) plan.annotations = [];
  if (!Array.isArray(plan.annotations)) problems.push('annotations must be an array');
  for (const sc of Array.isArray(plan.scenes) ? plan.scenes : []) if (sc && sc.annotations === undefined) sc.annotations = [];
  if (problems.length) return problems;
  if (!Array.isArray(plan.scenes)) return ['scenes must be an array'];
  if (plan.scenes.length !== sceneCount) problems.push('scenes has ' + plan.scenes.length + ' entries, must equal episode scene count ' + sceneCount);

  const totals = {strokes: plan.strokes.length, fills: plan.fills.length, marks: plan.marks.length, labels: plan.labels.length, annotations: plan.annotations.length};
  for (const s of plan.scenes) for (const k of ops) if (Array.isArray(s[k])) totals[k] += s[k].length;
  if (totals.strokes > CAPS.strokes) problems.push('total strokes ' + totals.strokes + ' exceeds cap ' + CAPS.strokes + '; simplify the drawing');
  if (totals.fills > CAPS.fills) problems.push('total fills ' + totals.fills + ' exceeds cap ' + CAPS.fills);
  if (totals.marks > CAPS.marks) problems.push('total marks ' + totals.marks + ' exceeds cap ' + CAPS.marks);
  if (plan.labels.length > CAPS.baseLabels) problems.push('base labels ' + plan.labels.length + ' exceeds cap ' + CAPS.baseLabels);
  if (totals.annotations > CAPS.annotations) problems.push('total annotations ' + totals.annotations + ' exceeds cap ' + CAPS.annotations);

  const checkOps = (ops2, where) => {
    for (const [idx, st] of (ops2.strokes || []).entries()) {
      const p = parsePath(st.d);
      if (!p.ok) problems.push(where + ' stroke ' + idx + ': ' + p.error);
      if (!colorOk(st.color)) problems.push(where + ' stroke ' + idx + ': unknown color ' + st.color);
    }
    for (const [idx, f] of (ops2.fills || []).entries()) {
      if (!colorOk(f.color)) problems.push(where + ' fill ' + idx + ': unknown color ' + f.color);
      if (f.shape === 'path') {
        const p = parsePath(f.d);
        if (!p.ok) problems.push(where + ' fill ' + idx + ': ' + p.error);
      } else {
        if (!Number.isFinite(f.cx) || !Number.isFinite(f.cy) || !Number.isFinite(f.r)) problems.push(where + ' fill ' + idx + ': circle needs cx, cy, r');
        else if (!inBox(f.cx, f.cy)) problems.push(where + ' fill ' + idx + ': circle center (' + f.cx + ',' + f.cy + ') outside drawing box ' + JSON.stringify(DRAW_BOX));
      }
    }
    for (const [idx, m] of (ops2.marks || []).entries()) {
      if (!Number.isFinite(m.x) || !Number.isFinite(m.y)) problems.push(where + ' mark ' + idx + ': needs numeric x, y');
      else if (!inBox(m.x, m.y)) problems.push(where + ' mark ' + idx + ': (' + m.x + ',' + m.y + ') outside drawing box');
      if (!colorOk(m.color)) problems.push(where + ' mark ' + idx + ': unknown color ' + m.color);
    }
    for (const [idx, a] of (ops2.annotations || []).entries()) {
      if (!['circle', 'arrow', 'x', 'magnifier', 'pip'].includes(a.type)) {problems.push(where + ' annotation ' + idx + ': unknown type ' + a.type); continue;}
      if (!colorOk(a.color)) problems.push(where + ' annotation ' + idx + ': unknown color ' + a.color);
      if (a.type === 'arrow') {
        if (![a.x1, a.y1, a.x2, a.y2].every(Number.isFinite)) problems.push(where + ' annotation ' + idx + ': arrow needs numeric x1,y1,x2,y2');
        else if (!inBox(a.x2, a.y2)) problems.push(where + ' annotation ' + idx + ': arrow head outside drawing box');
      } else {
        if (!Number.isFinite(a.x) || !Number.isFinite(a.y)) problems.push(where + ' annotation ' + idx + ': needs numeric x, y');
        else if (!inBox(a.x, a.y)) problems.push(where + ' annotation ' + idx + ': (' + a.x + ',' + a.y + ') outside drawing box');
      }
      if (a.type === 'pip' && a.text !== undefined) { if (typeof a.text !== 'string' || a.text.length > 24) problems.push(where + ' annotation ' + idx + ': pip text 1-24 chars'); else { if (/\d/.test(a.text)) problems.push(where + ' annotation ' + idx + ': pip text no digits'); if (/[A-Za-z]/.test(a.text)) problems.push(where + ' annotation ' + idx + ': pip text Arabic only'); } }
      if (a.type === 'pip' && a.d !== undefined) { const pp = parsePath(a.d); if (!pp.ok) problems.push(where + ' annotation ' + idx + ': pip icon path: ' + pp.error); }
      if (a.type === 'magnifier' && a.zoom !== undefined && !(a.zoom >= 1.2 && a.zoom <= 4)) problems.push(where + ' annotation ' + idx + ': magnifier zoom 1.2-4');
    }
    for (const [idx, l] of (ops2.labels || []).entries()) {
      if (![l.x1, l.y1, l.x2, l.y2].every(Number.isFinite)) {problems.push(where + ' label ' + idx + ': needs numeric x1,y1,x2,y2'); continue;}
      if (!inBox(l.x1, l.y1)) problems.push(where + ' label ' + idx + ': anchor (' + l.x1 + ',' + l.y1 + ') outside drawing box');
      if (typeof l.text !== 'string' || !l.text.trim() || l.text.length > 24) problems.push(where + ' label ' + idx + ': text must be 1-24 chars, got ' + String(l.text || '').length);
      else { if (/\d/.test(l.text)) problems.push(where + ' label ' + idx + ': write numbers as Arabic words, no digits'); if (/[A-Za-z]/.test(l.text)) problems.push(where + ' label ' + idx + ': Arabic only, no Latin letters'); }
      if (l.x2 < 0 || l.x2 > CANVAS.width || l.y2 < 0 || l.y2 > CANVAS.height) problems.push(where + ' label ' + idx + ': text position outside canvas');
    }
  };
  checkOps(plan, 'base');
  plan.scenes.forEach((s, i) => {
    const count = ops.reduce((n, k) => n + (Array.isArray(s[k]) ? s[k].length : 0), 0);
    if (count < 1) problems.push('scene ' + i + ' adds no visible ops; every scene must add at least one stroke, fill, mark or label so the drawing evolves');
    if (count > CAPS.perSceneOps) problems.push('scene ' + i + ' adds ' + count + ' ops, exceeds per-scene cap ' + CAPS.perSceneOps);
    if (Array.isArray(s.labels) && s.labels.length > CAPS.sceneLabels) problems.push('scene ' + i + ' labels ' + s.labels.length + ' exceeds per-scene cap ' + CAPS.sceneLabels);
    if (Array.isArray(s.annotations) && s.annotations.length > CAPS.perSceneAnnotations) problems.push('scene ' + i + ' annotations ' + s.annotations.length + ' exceeds per-scene cap ' + CAPS.perSceneAnnotations);
    checkOps(s, 'scene ' + i);
  });

  if (typeof plan.endStat !== 'string' || !plan.endStat.trim() || plan.endStat.length > 24) problems.push('endStat must be 1-24 chars');
  else { if (/\d/.test(plan.endStat)) problems.push('endStat must write numbers as Arabic words, no digits'); if (/[A-Za-z]/.test(plan.endStat)) problems.push('endStat must be Arabic only, no Latin letters'); }
  if (!Array.isArray(plan.summaryPoints) || plan.summaryPoints.length < 2 || plan.summaryPoints.length > 4) problems.push('summaryPoints must have 2-4 entries');
  else plan.summaryPoints.forEach((pt, i) => { if (typeof pt !== 'string' || pt.length > 60) problems.push('summaryPoints ' + i + ' must be 1-60 chars'); else { if (/\d/.test(pt)) problems.push('summaryPoints ' + i + ': write numbers as Arabic words, no digits'); if (/[A-Za-z]/.test(pt)) problems.push('summaryPoints ' + i + ': Arabic only, no Latin letters'); } });
  return problems;
}

function instructionFor(episode, config) {
  const sceneList = episode.scenes.map((s, i) => i + '. title=' + s.title + ' | summary=' + s.summary + ' | keyword=' + s.keyword + ' | template=' + s.template + ' | labels=' + JSON.stringify(s.labels) + (s.brollQuery ? ' | brollQuery=' + s.brollQuery : '')).join('\n');
  return `You are the art director for ${config.name}, an Egyptian Arabic paper-animation channel. Plan ONE persistent hand-drawn sketch that evolves across the episode, in this grammar: ink outlines (strokes) draw first, color fills bloom after, sparkle marks accent, and a few numbered-style callout labels point at parts. Return JSON only.

Canvas ${CANVAS.width}x${CANVAS.height}; keep ALL drawing inside the box x ${DRAW_BOX.x0}..${DRAW_BOX.x1}, y ${DRAW_BOX.y0}..${DRAW_BOX.y1} (title sits above, captions below). Path data uses ONLY absolute M, L, C, Z commands with numbers in canvas coordinates - no relative commands, no arcs, no transforms. Colors: named ${PALETTE.join('/')} or #RRGGBB.

Rules:
- The base drawing (strokes/fills/marks/labels) is the episode's ONE iconic image, matching the title question. It must read clearly as a sketch on grid paper: 8-25 strokes, simple shapes, no shading.
- scenes[] must have EXACTLY ${episode.scenes.length} entries; entry i lists only the NEW ops added during scene i (every scene MUST add at least one new visible op: a small detail, a fill, a mark, or at most ${CAPS.sceneLabels} labels). Total across base + scenes: max ${CAPS.strokes} strokes, ${CAPS.fills} fills, ${CAPS.marks} marks.
- Labels are short Arabic callouts (1-3 words, max 24 chars) in Egyptian white dialect - Arabic only, no Latin letters, numbers as Arabic words. Each has anchor point (x1,y1) ON the part and text position (x2,y2) beside it.
- You MAY add up to 2 annotations per scene (max 10 total) from: {"type":"circle","x,"y","r"} a red spotlight ring ON a part; {"type":"arrow","x1","y1","x2","y2"} pointing at a part; {"type":"x","x","y","size"} a red X over something forbidden/wrong; {"type":"magnifier","x","y","r","zoom"} a magnifier bubble that enlarges the drawing under it; {"type":"pip","x","y","w","h","text"} a dark picture-in-picture box with a short Arabic caption (optional "d" icon path). Use them where the narration points at, forbids, or zooms into something - they are the episode's emphasis layer.
- Fills of shape "path" may set "hatch": true for hand-shaded parallel-line hatching instead of flat color (good for cross-sections and shaded parts).
- Use each scene's template hint: phenomenon -> central object with motion marks; comparison -> two sides; steps -> numbered mini items in a row; journey -> path with stops; map -> simple outline map; chart -> bars with values; cause -> arrow chain.
- endStat: the episode's single most surprising number as a short Arabic string (write the number as Arabic words - no digits, no Latin letters; max 24 chars), for the giant red end-card stat.
- summaryPoints: 3 short Arabic takeaways (each max 60 chars), Egyptian white dialect, factual and matching the script.
- Never draw text besides labels; never draw realistic gore, real people, or logos.

Episode title: ${episode.title}
Hook: ${episode.hook}
Scenes:
${sceneList}`;
}

// Plans the drawing spec for one episode. Throws DRAWPLAN_VALIDATION_EXHAUSTED
// (or a specific DRAWPLAN_* code) after 3 failed attempts.
export async function drawplan(episode, config, opts = {}) {
  const client = opts.client || await provider();
  const instruction = instructionFor(episode, config);
  let feedback = '';
  for (let attempt = 0; attempt < 3; attempt++) {
    const response = await client.generate('text', {contents: [{parts: [{text: instruction + feedback}]}], generationConfig: {responseMimeType: 'application/json', responseSchema: planResponseSchema, temperature: 0.4}}, {settings: {task: 'paper_drawplan', schema: 1}, useCache: attempt === 0});
    let plan = null;
    try {
      const text = response.candidates[0].content.parts.filter(p => p.text).map(p => p.text).join('');
      plan = JSON.parse(text);
      const problems = validatePlan(plan, episode.scenes.length);
      if (problems.length) throw Error('DRAWPLAN_SCHEMA_INVALID: ' + problems.join(' | '));
      return {plan, drawModel: response._pipeline.model};
    } catch (e) {
      const msg = String(e && e.message || e);
      const code = msg.startsWith('DRAWPLAN_SCHEMA_INVALID') ? 'DRAWPLAN_SCHEMA_INVALID' : 'DRAWPLAN_RESPONSE_UNPARSEABLE';
      const detail = msg.slice(0, 1200);
      console.error('DRAWPLAN_VALIDATION_DETAIL ' + code + ' :: ' + detail);
      if (opts.diagnosticsPath) await writeFile(opts.diagnosticsPath, JSON.stringify({code, attempt: attempt + 1, detail}, null, 2)).catch(() => {});
      if (attempt === 2) throw Error(code);
      feedback = ' The previous plan failed validation with these exact problems: ' + detail.slice(0, 900) + '. Fix exactly those: only absolute M/L/C/Z path commands, all drawing inside the box ' + JSON.stringify(DRAW_BOX) + ', scenes[] must have exactly ' + episode.scenes.length + ' entries, respect the op caps. Keep the same overall idea.';
    }
  }
  throw Error('DRAWPLAN_VALIDATION_EXHAUSTED');
}
