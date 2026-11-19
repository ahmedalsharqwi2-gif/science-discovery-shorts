import React from 'react';
import {AbsoluteFill, Audio, staticFile, useCurrentFrame, interpolate} from 'remotion';
import {Mascot as MascotJs} from './Mascot.jsx';
const Mascot: any = MascotJs;
import {samplePath, pointAt} from './pathFollow.js';

// Paper-style episode renderer (طب إزاي؟ grammar, user-approved 2026-11-19):
// grid paper, question title with colored keyword + sketchy underline, ONE
// persistent hand-drawn sketch evolving per scene, paper karaoke captions,
// the channel mascot as animated presenter, and an end-card recap.
// The drawing plan comes from pipeline/drawplan.mjs (validated JSON spec).

const FPS = 30;
const T: Record<string, string> = {
  paper: '#EDE4D0', ink: '#1A1512', blue: '#2E6E8E', starBlue: '#3B7FB8',
  red: '#B03A2E', orange: '#E0A458', grid: '#D8CBB2', cyan: '#12bce5',
  white: '#FFFFFF', yellow: '#ffda34', gold: '#C99700', green: '#4E7E5B', shoeRed: '#E23B2E',
};
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
function layoutOps(ops: {strokes?: Op[]; fills?: Op[]; marks?: Op[]; labels?: Op[]}, startAt: number, windowFrames: number) {
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
  return {strokes, labels, fills, marks, end: strokesEnd + (labels.length ? labels.length * 26 + 24 : 8)};
}

const Stroke = ({s, frame}: {s: Op; frame: number}) => (
  <g>
    <path d={s.d} fill="none" stroke={col(s.color)} strokeWidth={s.width || 4} strokeLinecap="round" style={draw(frame, s.start, s.dur, s.len)} />
    <path d={s.d} fill="none" stroke={col(s.color)} strokeWidth={(s.width || 4) * 0.6} strokeLinecap="round" opacity={0.3} transform="translate(3,2)" style={draw(frame, s.start + 2, s.dur, s.len)} />
  </g>
);

const Fill = ({f, frame}: {f: Op; frame: number}) => (
  <g style={fade(frame, f.start, 10)}>
    {f.shape === 'path'
      ? <path d={f.d} fill={col(f.color)} opacity={f.opacity ?? 1} stroke="none" />
      : <circle cx={f.cx} cy={f.cy} r={f.r} fill={col(f.color)} opacity={f.opacity ?? 0.85} />}
  </g>
);

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
      <div style={{position: 'absolute', top: -78, right: 40, fontFamily, fontWeight: 700, fontSize: 26, color: T.ink, opacity: 0.55, direction: 'rtl'}}>{channelName}</div>
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

// Paper karaoke captions: 5-word window, 50ms lead, active word red+underlined.
const Captions = ({frame, words}: {frame: number; words: Op[]}) => {
  const t = frame / FPS + 0.05;
  let cur = -1;
  for (let i = words.length - 1; i >= 0; i--) {if (words[i].start <= t) {cur = i; break;}}
  if (cur < 0) return null;
  const start = Math.floor(cur / 5) * 5;
  const win = words.slice(start, start + 5);
  return (
    <div style={{position: 'absolute', bottom: 170, width: '100%', display: 'flex', justifyContent: 'center', padding: '0 50px'}}>
      <div style={{fontFamily, fontWeight: 800, fontSize: 54, color: T.ink, borderRadius: 24, padding: '14px 34px', direction: 'rtl', textAlign: 'center', lineHeight: 1.5, background: 'rgba(237,228,208,0.88)', boxShadow: '0 2px 0 rgba(26,21,18,0.25)'}}>
        {win.map((w: Op, i: number) => {
          const idx = start + i;
          const hot = idx === cur;
          return <span key={idx} style={hot ? {color: T.red, borderBottom: `5px solid ${T.red}`, paddingBottom: 3} : undefined}>{w.text} </span>;
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

const drift = (frame: number, dur: number) => {
  const p = interpolate(frame, [0, dur], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return `translate(${-14 * p}px, ${-22 * p}px) scale(${1 + 0.035 * p})`;
};

export const PaperEpisode = (props: any) => {
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
  const callouts: Op[] = [...plan.labels, ...plan.scenes.flatMap((s: Op) => (s.labels || []) as Op[])].slice(0, 3);
  const titleKeyword = (scenes.find((s: Op) => s.keyword && props.title.includes(s.keyword)) || {}).keyword;
  const channelName = props.channelName || 'افترض كده';

  return (
    <AbsoluteFill style={{backgroundColor: T.paper}}>
      <Grid />
      {props.audio ? <Audio src={staticFile(props.audio)} /> : null}
      <QuestionTitle frame={frame} title={props.title} keyword={titleKeyword} seriesLabel={props.seriesLabel} channelName={channelName} />
      <div style={{position: 'absolute', width: '100%', height: '100%', transform: drift(frame, total)}}>
        <svg width="1080" height="1920" style={{position: 'absolute'}}>
          {base.strokes.map((s: Op, i: number) => <Stroke key={'bs' + i} s={s} frame={frame} />)}
          {base.fills.map((f: Op, i: number) => <Fill key={'bf' + i} f={f} frame={frame} />)}
          {base.marks.map((m: Op, i: number) => <Mark key={'bm' + i} m={m} frame={frame} />)}
          {base.labels.map((l: Op, i: number) => <Callout key={'bl' + i} l={l} frame={frame} />)}
          {perScene.map((laid: Op, si: number) => laid ? (
            <g key={'sc' + si}>
              {laid.strokes.map((s: Op, i: number) => <Stroke key={'s' + i} s={s} frame={frame} />)}
              {laid.fills.map((f: Op, i: number) => <Fill key={'f' + i} f={f} frame={frame} />)}
              {laid.marks.map((m: Op, i: number) => <Mark key={'m' + i} m={m} frame={frame} />)}
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
      <EndCard frame={frame} start={endStart} title={props.title} plan={plan} callouts={callouts} />
    </AbsoluteFill>
  );
};
