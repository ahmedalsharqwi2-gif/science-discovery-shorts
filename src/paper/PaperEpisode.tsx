import React from 'react';
import {AbsoluteFill, Audio, staticFile, useCurrentFrame, interpolate, Easing} from 'remotion';
import {Mascot as MascotJs} from './Mascot.jsx';
const Mascot: any = MascotJs;
import {samplePath, pointAt} from './pathFollow.js';
import {camTargetsFor, camAt} from './camera.js';
import motionTokens from '../../brand/motion-tokens.json';

// Paper-style episode renderer (طب إزاي؟ grammar, user-approved 2026-11-19):
// grid paper, question title with colored keyword + sketchy underline, ONE
// persistent hand-drawn sketch evolving per scene, paper karaoke captions,
// the channel mascot as animated presenter, and an end-card recap.
// The drawing plan comes from pipeline/drawplan.mjs (validated JSON spec).

const FPS = 30;
// Theme palette comes from brand/motion-tokens.json (pro-motion design
// system). T is module-level because the render process draws one episode
// (one theme) at a time; PaperEpisode rebinds it from props.paper.theme.
const themes = (motionTokens as any).themes as Record<string, Record<string, string>>;
let T: Record<string, string> = {...themes['paper-technical']};
const fontFamily = 'ChannelArabic, Cairo, sans-serif';

type Op = any;
type Plan = {strokes: Op[]; fills: Op[]; marks: Op[]; labels: Op[]; scenes: Op[]; endStat: string; summaryPoints: string[]};

const draw = (frame: number, start: number, dur: number, len: number) => {
  const p = interpolate(frame, [start, start + dur], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return {strokeDasharray: String(len), strokeDashoffset: String(len * (1 - p))} as any;
};
const fade = (frame: number, start: number, dur = 10) => ({
  opacity: interpolate(frame, [start, start + dur], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
});
const col = (c?: string) => (c && T[c]) || c || T.ink;

// Sequences one op group into a frame window: strokes chain with travel
// gaps, labels follow with leader lines, fills/marks bloom after strokes.
function layoutOps(ops: {strokes?: Op[]; fills?: Op[]; marks?: Op[]; labels?: Op[]; annotations?: Op[]}, startAt: number, windowFrames: number) {
  const strokes = (ops.strokes || []).map((s: Op) => ({...s, samples: samplePath(s.d)}));
  const n = Math.max(1, strokes.length);
  const strokeDur = Math.max(12, Math.min(38, Math.floor((windowFrames * 0.55) / n)));
  let t = startAt;
  strokes.forEach((s, i) => {
    if (i > 0) {
      const prevEnd = pointAt(strokes[i - 1].samples, 1);
      const nextStart = pointAt(s.samples, 0);
      const dist = Math.hypot(nextStart.x - prevEnd.x, nextStart.y - prevEnd.y);
      t += Math.min(40, Math.round(dist / 30) + 6);
    }
    s.start = t;
    s.len = Math.ceil(s.samples.total * 1.02);
    s.dur = strokeDur;
    t += strokeDur;
  });
  const strokesEnd = t;
  const labels = (ops.labels || []).map((l: Op, i: number) => ({...l, start: strokesEnd + 6 + i * 26, dur: 18}));
  const fills = (ops.fills || []).map((f: Op, i: number) => ({...f, start: strokesEnd + (f.delay ?? 0) + i * 3}));
  const marks = (ops.marks || []).map((m: Op, i: number) => ({...m, start: strokesEnd + (m.delay ?? 0) + i * 2}));
  const annotations = (ops.annotations || []).map((a: Op, i: number) => ({...a, start: strokesEnd + (a.delay ?? 0) + i * 16}));
  return {strokes, labels, fills, marks, annotations, end: strokesEnd + (labels.length ? labels.length * 26 + 24 : 8)};
}

const Stroke = ({s, frame}: {s: Op; frame: number}) => (
  <g>
    <path d={s.d} fill="none" stroke={col(s.color)} strokeWidth={s.width || 4} strokeLinecap="round" style={draw(frame, s.start, s.dur, s.len)} />
    <path d={s.d} fill="none" stroke={col(s.color)} strokeWidth={(s.width || 4) * 0.6} strokeLinecap="round" opacity={0.3} transform="translate(3,2)" style={draw(frame, s.start + 2, s.dur, s.len)} />
  </g>
);

const Fill = ({f, frame, fid}: {f: Op; frame: number; fid?: string}) => (
  <g style={fade(frame, f.start, 10)}>
    {f.hatch && f.shape === 'path' ? (
      <>
        <pattern id={fid || 'hatch'} patternUnits="userSpaceOnUse" width="9" height="9" patternTransform="rotate(-32)">
          <rect width="9" height="9" fill={col(f.color)} opacity={(f.opacity ?? 1) * 0.35} />
          <line x1="0" y1="0" x2="0" y2="9" stroke={col(f.color)} strokeWidth="1.6" opacity="0.9" />
        </pattern>
        <path d={f.d} fill={`url(#${fid || 'hatch'})`} stroke="none" />
      </>
    ) : f.shape === 'path'
      ? <path d={f.d} fill={col(f.color)} opacity={f.opacity ?? 1} stroke="none" />
      : <circle cx={f.cx} cy={f.cy} r={f.r} fill={col(f.color)} opacity={f.opacity ?? 0.85} />}
  </g>
);

// Annotation ops (user-approved direction 2026-11-20): spotlight circle,
// arrow, X mark, magnifier bubble, and dark picture-in-picture box. Each
// draws in with the same hand-drawn grammar as strokes.
const Annotation = ({a, frame, art}: {a: Op; frame: number; art?: Op}) => {
  const c = col(a.color || 'red');
  if (a.type === 'circle') {
    const len = 2 * Math.PI * (a.r || 60);
    return (
      <g>
        <circle cx={a.x} cy={a.y} r={(a.r || 60)} fill="none" stroke={c} strokeWidth={a.width || 5} strokeLinecap="round" pathLength={len} style={draw(frame, a.start, a.dur || 22, len)} transform={`rotate(-90 ${a.x} ${a.y})`} />
      </g>
    );
  }
  if (a.type === 'arrow') {
    const len = Math.hypot(a.x2 - a.x1, a.y2 - a.y1);
    const ang = Math.atan2(a.y2 - a.y1, a.x2 - a.x1);
    const h = 22;
    const head = `M ${a.x2} ${a.y2} L ${a.x2 - h * Math.cos(ang - 0.42)} ${a.y2 - h * Math.sin(ang - 0.42)} M ${a.x2} ${a.y2} L ${a.x2 - h * Math.cos(ang + 0.42)} ${a.y2 - h * Math.sin(ang + 0.42)}`;
    return (
      <g>
        <path d={`M ${a.x1} ${a.y1} L ${a.x2} ${a.y2}`} fill="none" stroke={c} strokeWidth={a.width || 5} strokeLinecap="round" style={draw(frame, a.start, a.dur || 20, len)} />
        <path d={head} fill="none" stroke={c} strokeWidth={a.width || 5} strokeLinecap="round" style={draw(frame, a.start + (a.dur || 20) - 4, 8, 2 * h)} />
      </g>
    );
  }
  if (a.type === 'x') {
    const s = a.size || 34;
    const d1 = `M ${a.x - s} ${a.y - s} L ${a.x + s} ${a.y + s}`, d2 = `M ${a.x + s} ${a.y - s} L ${a.x - s} ${a.y + s}`;
    const len = 2 * s * Math.SQRT2;
    return (
      <g>
        <path d={d1} fill="none" stroke={c} strokeWidth={a.width || 7} strokeLinecap="round" style={draw(frame, a.start, 10, len)} />
        <path d={d2} fill="none" stroke={c} strokeWidth={a.width || 7} strokeLinecap="round" style={draw(frame, a.start + 6, 10, len)} />
      </g>
    );
  }
  if (a.type === 'magnifier' && art) {
    const r = a.r || 120, z = a.zoom || 2;
    const p = interpolate(frame, [a.start, a.start + 14], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
    if (p <= 0) return null;
    const id = `mag-${Math.round(a.x)}-${Math.round(a.y)}`;
    return (
      <g opacity={p}>
        <clipPath id={id}><circle cx={a.x} cy={a.y} r={r} /></clipPath>
        <circle cx={a.x} cy={a.y} r={r} fill={T.paper} />
        <g clipPath={`url(#${id})`}>
          <g transform={`translate(${a.x} ${a.y}) scale(${z}) translate(${-a.x} ${-a.y})`}>
            {(art.strokes || []).map((s: Op, i: number) => <path key={'ms' + i} d={s.d} fill="none" stroke={col(s.color)} strokeWidth={(s.width || 4) * 0.9} strokeLinecap="round" />)}
            {(art.fills || []).map((f: Op, i: number) => (f.shape === 'path'
              ? <path key={'mf' + i} d={f.d} fill={col(f.color)} opacity={f.opacity ?? 1} stroke="none" />
              : <circle key={'mf' + i} cx={f.cx} cy={f.cy} r={f.r} fill={col(f.color)} opacity={f.opacity ?? 0.85} />))}
          </g>
        </g>
        <circle cx={a.x} cy={a.y} r={r} fill="none" stroke={T.ink} strokeWidth={5} />
        <line x1={a.x + r * 0.72} y1={a.y + r * 0.72} x2={a.x + r * 1.25} y2={a.y + r * 1.25} stroke={T.ink} strokeWidth={10} strokeLinecap="round" />
      </g>
    );
  }
  if (a.type === 'pip') {
    const w = a.w || 300, h = a.h || 220;
    // Fit the label inside the card: shrink the font when the text is wide
    // (slice review 2026-11-20: 30px text overflowed a 220px card).
    const fs = a.text ? Math.min(30, Math.floor((w - 28) / (String(a.text).length * 0.62))) : 30;
    return (
      <g style={fade(frame, a.start, 10)}>
        <rect x={a.x - w / 2} y={a.y - h / 2} width={w} height={h} rx={18} fill={T.ink} stroke={col(a.color || 'red')} strokeWidth={4} />
        {a.d ? <path d={a.d} fill="none" stroke={T.paper} strokeWidth={3} strokeLinecap="round" style={draw(frame, a.start + 6, 20, a.len || 300)} /> : null}
        {a.text ? <text x={a.x} y={a.y + h / 2 - 24} textAnchor="middle" fontFamily={fontFamily} fontWeight={700} fontSize={fs} fill={T.paper}>{a.text}</text> : null}
      </g>
    );
  }
  return null;
};

const Mark = ({m, frame}: {m: Op; frame: number}) => {
  const p = interpolate(frame, [m.start, m.start + 7], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  if (p <= 0) return null;
  const c = col(m.color || 'gold');
  return (
    <g opacity={p}>
      <circle cx={m.x} cy={m.y} r={(m.r || 8) * p} fill={c} />
      <line x1={m.x - (m.r || 8) * 2.2 * p} y1={m.y} x2={m.x + (m.r || 8) * 2.2 * p} y2={m.y} stroke={c} strokeWidth={2} />
      <line x1={m.x} y1={m.y - (m.r || 8) * 2.2 * p} x2={m.x} y2={m.y + (m.r || 8) * 2.2 * p} stroke={c} strokeWidth={2} />
    </g>
  );
};

const Callout = ({l, frame}: {l: Op; frame: number}) => (
  <g style={fade(frame, l.start, 8)}>
    <path d={`M ${l.x1} ${l.y1} L ${l.x2} ${l.y2}`} stroke={T.ink} strokeWidth={2.5} fill="none"
      style={draw(frame, l.start, l.dur || 18, Math.hypot(l.x2 - l.x1, l.y2 - l.y1))} />
    <circle cx={l.x1} cy={l.y1} r={6} fill={T.red} />
    <text x={l.x2} y={l.y2 - 14} textAnchor="end" fontFamily={fontFamily} fontWeight={700} fontSize={38} fill={T.ink}>{l.text}</text>
  </g>
);

const Grid = () => (
  <AbsoluteFill style={{backgroundColor: T.paper}}>
    <svg width="1080" height="1920" style={{position: 'absolute'}}>
      {Array.from({length: 27}, (_, i) => (<line key={'v' + i} x1={i * 42} y1={0} x2={i * 42} y2={1920} stroke={T.grid} strokeWidth={1} />))}
      {Array.from({length: 46}, (_, i) => (<line key={'h' + i} x1={0} y1={i * 42} x2={1080} y2={i * 42} stroke={T.grid} strokeWidth={1} />))}
    </svg>
  </AbsoluteFill>
);

const QuestionTitle = ({frame, title, keyword, seriesLabel, channelName}: {frame: number; title: string; keyword?: string; seriesLabel?: string; channelName: string}) => {
  const kw = keyword || '';
  const i = kw ? title.indexOf(kw) : -1;
  const accent = T.gold;
  return (
    <div style={{position: 'absolute', top: 110, width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', ...fade(frame, 2, 12)}}>
      <div style={{position: 'absolute', top: -78, right: 40, fontFamily, fontWeight: 700, fontSize: 26, color: T.ink, opacity: 0.55, direction: 'rtl'}}>{channelName || ''}</div>
      {seriesLabel ? <div style={{fontFamily, fontWeight: 700, fontSize: 26, color: T.ink, opacity: 0.6, marginBottom: 14, direction: 'rtl'}}>{seriesLabel}</div> : null}
      <div style={{fontFamily, fontWeight: 800, fontSize: 66, color: T.ink, direction: 'rtl', textAlign: 'center', lineHeight: 1.4, padding: '0 70px'}}>
        {i >= 0 ? title.slice(0, i) : title}
        {i >= 0 ? (
          <span style={{position: 'relative', color: accent, display: 'inline-block'}}>
            {kw}
            <svg style={{position: 'absolute', right: 0, left: 0, bottom: -16, width: '100%'}} height="18" viewBox="0 0 100 18" preserveAspectRatio="none">
              <path d="M3 11 C 25 4, 55 17, 97 8" fill="none" stroke={accent} strokeWidth={4.5} strokeLinecap="round" vectorEffect="non-scaling-stroke" style={draw(frame, 8, 16, 110)} />
            </svg>
          </span>
        ) : null}
        {i >= 0 ? title.slice(i + kw.length) : ''}
      </div>
    </div>
  );
};

// On-screen citation chip (per-channel spec: history/horror/ai-news show the
// source at key shots). Rendered only when props.paper.citations is true and
// the current scene carries a sourceLabel (set by the assets stage).
const KIND_STYLE = {fact: {label: 'موثق', color: 'green'}, legend: {label: 'حكاية', color: 'gold'}, illustration: {label: 'توضيح', color: 'blue'}};
const SourceChip = ({label, kind}: {label: string; kind?: string}) => {
  const k = kind && (KIND_STYLE as any)[kind];
  const border = k ? col(k.color) : T.grid;
  return (
    <div style={{position: 'absolute', bottom: 296, left: 44, fontFamily, fontWeight: 700, fontSize: 24, color: T.ink, background: T.paper, opacity: 0.92, border: `2px solid ${border}`, borderRadius: 14, padding: '8px 20px', direction: 'rtl'}}>
      {k ? <span style={{color: col(k.color), marginInlineEnd: 10}}>{k.label} ·</span> : null}{label}
    </div>
  );
};

// Top bar (per-channel spec: نفهمها gold standard): channel logo + name on the
// right, live scene counter on the left. Replaces the floating channel label
// in QuestionTitle when enabled (props.paper.topBar + paper.logoPath).
const TopBar = ({frame, channelName, logoPath, sceneIndex, sceneCount, chapterLabel}: {frame: number; channelName: string; logoPath: string; sceneIndex: number; sceneCount: number; chapterLabel?: string}) => (
  <div style={{position: 'absolute', top: 26, left: 0, right: 0, display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0 44px', direction: 'rtl', ...fade(frame, 2, 12)}}>
    <div style={{display: 'flex', alignItems: 'center', gap: 14}}>
      <img src={staticFile(logoPath)} style={{width: 54, height: 54, borderRadius: 12, objectFit: 'cover', border: `2px solid ${T.grid}`}} />
      <span style={{fontFamily, fontWeight: 800, fontSize: 28, color: T.ink}}>{channelName}</span>
    </div>
    <span style={{fontFamily, fontWeight: 700, fontSize: 26, color: T.ink, opacity: 0.65}}>{chapterLabel ? `${chapterLabel} · ` : ''}{sceneIndex + 1}/{sceneCount}</span>
  </div>
);

// Paper karaoke captions: 5-word window, 50ms lead, active word red+underlined.
// Kinetic reveal (user-approved direction 2026-11-20): each word pops in as it
// is spoken (scale+rise with a light overshoot), unspoken words stay hidden.
const Captions = ({frame, words}: {frame: number; words: Op[]}) => {
  const t = frame / FPS + 0.05;
  let cur = -1;
  for (let i = words.length - 1; i >= 0; i--) {if (words[i].start <= t) {cur = i; break;}}
  if (cur < 0) return null;
  const start = Math.floor(cur / 5) * 5;
  const win = words.slice(start, start + 5);
  return (
    <div style={{position: 'absolute', bottom: 170, width: '100%', display: 'flex', justifyContent: 'center', padding: '0 50px'}}>
      <div style={{fontFamily, fontWeight: 800, fontSize: 54, color: T.ink, borderRadius: 24, padding: '20px 38px', direction: 'rtl', textAlign: 'center', lineHeight: 1.5, maxWidth: 940, background: `color-mix(in srgb, ${T.paper} 88%, transparent)`, border: `2px solid ${T.grid}`, boxShadow: '0 2px 0 rgba(26,21,18,0.25)'}}>
        {win.map((w: Op, i: number) => {
          const idx = start + i;
          const hot = idx === cur;
          const age = t - w.start;
          if (age < -0.05) return <span key={idx} style={{display: 'inline-block', opacity: 0, marginInlineStart: idx > start ? '0.28em' : 0}}>{w.text}</span>;
          const pop = interpolate(age, [0, 0.09, 0.16], [0.55, 1.06, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
          const rise = interpolate(age, [0, 0.16], [4, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
          return <span key={idx} style={{display: 'inline-block', marginInlineStart: idx > start ? '0.28em' : 0, transform: `scale(${pop}) translateY(${rise}px)`, opacity: interpolate(age, [0, 0.06], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}), ...(hot ? {color: T.red, borderBottom: `5px solid ${T.red}`, paddingBottom: 3} : {})}}>{w.text}</span>;
        })}
      </div>
    </div>
  );
};

// End-card recap: the finished drawing with numbered callouts, giant stat, summary.
const EndCard = ({frame, start, title, plan, callouts}: {frame: number; start: number; title: string; plan: Plan; callouts: Op[]}) => {
  const p = interpolate(frame, [start, start + 18], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  if (p <= 0) return null;
  const pop = (i: number) => ({opacity: interpolate(frame, [start + 14 + i * 8, start + 22 + i * 8], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})});
  const allStrokes = [...plan.strokes, ...plan.scenes.flatMap((s: Op) => s.strokes || [])];
  const allFills = [...plan.fills, ...plan.scenes.flatMap((s: Op) => s.fills || [])];
  return (
    <AbsoluteFill style={{backgroundColor: T.paper, opacity: p}}>
      <Grid />
      <div style={{position: 'absolute', top: 90, width: '100%', textAlign: 'center', fontFamily, fontWeight: 800, fontSize: 44, color: T.ink, direction: 'rtl', padding: '0 60px'}}>{title}</div>
      <svg width="1080" height="560" viewBox="140 500 800 800" style={{position: 'absolute', top: 200}}>
        {allStrokes.map((st: Op, i: number) => (<path key={i} d={st.d} fill="none" stroke={col(st.color)} strokeWidth={(st.width || 4) * 0.9} strokeLinecap="round" />))}
        {allFills.map((f: Op, i: number) => (f.shape === 'path'
          ? <path key={'f' + i} d={f.d} fill={col(f.color)} opacity={f.opacity ?? 1} stroke="none" />
          : <circle key={'f' + i} cx={f.cx} cy={f.cy} r={f.r} fill={col(f.color)} opacity={f.opacity ?? 0.85} />))}
        {callouts.map((l: Op, i: number) => (
          <g key={'c' + i}>
            <circle cx={l.x1} cy={l.y1} r={22} fill={T.paper} stroke={T.ink} strokeWidth={3} />
            <text x={l.x1} y={l.y1 + 12} textAnchor="middle" fontFamily={fontFamily} fontWeight={800} fontSize={30} fill={T.ink}>{i + 1}</text>
          </g>
        ))}
      </svg>
      <div style={{position: 'absolute', top: 800, width: '100%', display: 'flex', justifyContent: 'center', gap: 60, direction: 'rtl'}}>
        {callouts.map((l: Op, i: number) => (
          <div key={i} style={{...pop(i), display: 'flex', alignItems: 'center', gap: 10}}>
            <span style={{width: 40, height: 40, borderRadius: 20, border: `3px solid ${T.ink}`, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontFamily, fontWeight: 800, fontSize: 24, color: T.ink, background: T.paper}}>{i + 1}</span>
            <span style={{fontFamily, fontWeight: 700, fontSize: 30, color: T.ink}}>{l.text}</span>
          </div>
        ))}
      </div>
      <div style={{position: 'absolute', top: 920, width: '100%', textAlign: 'center', ...pop(3)}}>
        <span style={{fontFamily, fontWeight: 800, fontSize: 110, color: T.red}}>{plan.endStat}</span>
      </div>
      <div style={{position: 'absolute', top: 1120, width: '100%', padding: '0 90px', direction: 'rtl'}}>
        {(plan.summaryPoints || []).map((pt: string, i: number) => (
          <div key={i} style={{...pop(4 + i), fontFamily, fontWeight: 700, fontSize: 34, color: T.ink, marginBottom: 22, display: 'flex', gap: 14}}>
            <span style={{color: T.red, fontWeight: 800}}>{i + 1}.</span>
            <span>{pt}</span>
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};

export const PaperEpisode = (props: any) => {
  T = {...themes['paper-technical'], ...(themes[props.paper?.theme] || {})};
  const frame = useCurrentFrame();
  const plan: Plan = props.paper.plan;
  const scenes = props.scenes || [];
  // scene windows in frames from cumulative durations (seconds)
  const windows: {start: number; frames: number}[] = [];
  let acc = 0;
  for (const s of scenes) {const frames = Math.max(30, Math.round((s.duration || 8) * FPS)); windows.push({start: acc, frames}); acc += frames;}
  const total = props.durationInFrames || acc;
  const endStart = total - 170;

  const base = layoutOps(plan, 40, Math.max(120, (windows[0]?.start ?? 240) + (windows[0]?.frames ?? 200) - 60));
  const perScene = plan.scenes.map((ops: Op, i: number) => windows[i] ? layoutOps(ops, windows[i].start + 8, windows[i].frames - 16) : null);

  // captions: absolute-time word list
  const words: Op[] = [];
  scenes.forEach((s: Op, i: number) => {const off = windows[i].start / FPS; (s.words || []).forEach((w: Op) => words.push({text: w.text, start: w.start + off, end: w.end + off}));});

  // presenter beats: per scene action/expression; point when that scene's callouts land
  const beats: Op[] = [];
  scenes.forEach((s: Op, i: number) => {
    const laid = perScene[i];
    if (laid && laid.labels.length) beats.push({frame: windows[i].start + 8, action: 'point', expression: s.expression ?? 4});
    if (laid) beats.push({frame: laid.end, action: s.action || 'idle', expression: s.expression ?? 0});
  });
  // camera target per scene: eased move toward the scene's drawing centroid,
  // zoom clamped so no element ever enters the title or captions zones.
  const camLayers = [{strokes: base.strokes, fills: base.fills, marks: base.marks, labels: base.labels, annotations: base.annotations}, ...perScene.map((l: Op) => l || {})];
  const camTargets = camTargetsFor(windows, camLayers);
  const ease = Easing.inOut(Easing.cubic);
  const cam = (fr: number) => {
    const t = camAt(fr, windows, camTargets, ease);
    return `translate(${540 - t.s * t.x}px, ${(t.a ?? 1060) - t.s * t.y}px) scale(${t.s})`;
  };
  const callouts: Op[] = [...plan.labels, ...plan.scenes.flatMap((s: Op) => (s.labels || []) as Op[])].slice(0, 3);
  const titleKeyword = (scenes.find((s: Op) => s.keyword && props.title.includes(s.keyword)) || {}).keyword;
  const channelName = props.channelName || 'افترض كده';

  const topBar = props.paper?.topBar === true && props.paper?.logoPath;
  const sceneIdx = (() => {const i = windows.findIndex(w => frame < w.start + w.frames); return i < 0 ? scenes.length - 1 : i;})();

  return (
    <AbsoluteFill style={{backgroundColor: T.paper}}>
      <Grid />
      {props.audio ? <Audio src={staticFile(props.audio)} /> : null}
      {topBar ? <TopBar frame={frame} channelName={channelName} logoPath={props.paper.logoPath} sceneIndex={sceneIdx} sceneCount={scenes.length} chapterLabel={props.paper.chapterLabel} /> : null}
      <QuestionTitle frame={frame} title={props.title} keyword={titleKeyword} seriesLabel={props.seriesLabel} channelName={topBar ? '' : channelName} />
      <div style={{position: 'absolute', width: '100%', height: '100%', transformOrigin: '0 0', transform: cam(frame)}}>
        <svg width="1080" height="1920" style={{position: 'absolute'}}>
          {base.strokes.map((s: Op, i: number) => <Stroke key={'bs' + i} s={s} frame={frame} />)}
          {base.fills.map((f: Op, i: number) => <Fill key={'bf' + i} f={f} frame={frame} fid={'hb' + i} />)}
          {base.marks.map((m: Op, i: number) => <Mark key={'bm' + i} m={m} frame={frame} />)}
          {base.annotations.map((a: Op, i: number) => <Annotation key={'ba' + i} a={a} frame={frame} art={plan} />)}
          {base.labels.map((l: Op, i: number) => <Callout key={'bl' + i} l={l} frame={frame} />)}
          {perScene.map((laid: Op, si: number) => laid ? (
            <g key={'sc' + si}>
              {laid.strokes.map((s: Op, i: number) => <Stroke key={'s' + i} s={s} frame={frame} />)}
              {laid.fills.map((f: Op, i: number) => <Fill key={'f' + i} f={f} frame={frame} fid={'hs' + si + '-' + i} />)}
              {laid.marks.map((m: Op, i: number) => <Mark key={'m' + i} m={m} frame={frame} />)}
              {laid.annotations.map((a: Op, i: number) => <Annotation key={'a' + i} a={a} frame={frame} art={plan} />)}
              {laid.labels.map((l: Op, i: number) => <Callout key={'l' + i} l={l} frame={frame} />)}
            </g>
          ) : null)}
          {props.mascot !== false && <Mascot frame={frame} x={280} y={1290} scale={0.6} enterFrame={55} beats={beats} />}
        </svg>
      </div>
      <svg width="1080" height="1920" style={{position: 'absolute', pointerEvents: 'none', opacity: 0.05}}>
        <filter id="grain"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" stitchTiles="stitch" /></filter>
        <rect width="1080" height="1920" filter="url(#grain)" />
      </svg>
      {words.length ? <Captions frame={frame} words={words} /> : null}
      {props.paper?.citations === true && (() => {const sc = scenes[sceneIdx]; return sc?.sourceLabel ? <SourceChip label={sc.sourceLabel} kind={sc.kind} /> : null;})()}
      <EndCard frame={frame} start={endStart} title={props.title} plan={plan} callouts={callouts} />
    </AbsoluteFill>
  );
};
