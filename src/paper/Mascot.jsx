import React from 'react';
import {interpolate} from 'remotion';

// Paper-presenter mascot v2: restyled to match the channel's original
// character (owner references 2026-11-19: logo + episode frame):
// huge white oval eyes WITH dark pupils (directional gaze), big toothy open
// grin, thick dark outlines, yellow jagged-hem shirt with white collar,
// black pants, red sneakers with a white stripe, single hair curl.
// Same parametric actions/expressions contract as v1.

export const CHARACTER_COLORS = {skin: '#12bce5', shirt: '#ffda34', line: '#101719', pants: '#101719', shoe: '#E23B2E'};
export const EXPRESSIONS = ['smile', 'shock', 'tired', 'angry', 'curious', 'sad', 'proud', 'scared', 'laugh', 'wink', 'confused', 'determined'];
export const ACTIONS = ['walk', 'run', 'jump', 'fall', 'point', 'turn', 'hang', 'sleep'];

// Rig geometry: origin between the feet; head center at (0, -150), r=116.
// Total height ~620 units before scale.

// Toothy grin: white band with dark outline and teeth lines. open=0 closed grin,
// 1 fully open oval (shock), 2 gritted (angry), 3 small smile.
const Mouth = ({kind, frame}) => {
  if (kind === 1) return <ellipse cx="0" cy="-88" rx="30" ry="38" fill={CHARACTER_COLORS.line} />;
  if (kind === 2) return (
    <g>
      <path d="M-58 -100 L58 -100 L52 -62 L-52 -62 Z" fill="white" stroke={CHARACTER_COLORS.line} strokeWidth="8" strokeLinejoin="round" />
      <path d="M-20 -100 L-20 -62 M20 -100 L20 -62" stroke={CHARACTER_COLORS.line} strokeWidth="6" fill="none" />
    </g>
  );
  if (kind === 3) return <path d="M-38 -88 Q0 -60 38 -88" fill="none" stroke={CHARACTER_COLORS.line} strokeWidth="9" strokeLinecap="round" />;
  // default: big toothy open grin (white oval, teeth lines, lower-lip arc)
  return (
    <g>
      <ellipse cx="0" cy="-82" rx="72" ry="34" fill="white" stroke={CHARACTER_COLORS.line} strokeWidth="9" />
      <path d="M-40 -114 L-38 -56 M0 -116 L0 -50 M40 -114 L38 -56" stroke={CHARACTER_COLORS.line} strokeWidth="6" fill="none" />
      <path d="M-72 -82 L72 -82" stroke={CHARACTER_COLORS.line} strokeWidth="6" fill="none" />
    </g>
  );
};

// expression -> [mouthKind, browDy, browTilt, pupilScale]
const EXPR = [
  [0, 0, 0, 1],      // smile (grin)
  [1, 6, 0, 1.1],    // shock (open mouth)
  [3, 4, 0, 0.4],    // tired (small smile, heavy eyes)
  [2, 10, 26, 1],    // angry (gritted, brows slammed down+tilted)
  [0, -6, -8, 1.15], // curious (grin, raised brows, bigger pupils)
  [3, 8, 14, 0.9],   // sad
  [0, -4, 0, 1],     // proud grin
  [1, 10, 12, 1.2],  // scared
  [0, -8, 0, 0.6],   // laugh (grin, eyes squeezed)
  [0, 0, 0, 1],      // wink (handled per-eye)
  [3, 2, -14, 1],    // confused
  [2, 6, 18, 1],     // determined (gritted, tilted brows)
];

export const MascotRig = ({frame, expression = 0, action = 'point', gazeX = 16}) => {
  const t = frame / 30, speed = action === 'run' ? 14 : 6, walk = ['walk', 'run'].includes(action) ? Math.sin(t * speed) * 20 : 0;
  const y = action === 'jump' ? -Math.abs(Math.sin(t * 4)) * 95 : action === 'hang' ? Math.sin(t * 3) * 12 : 0;
  const rotation = action === 'fall' ? Math.min(85, t * 90) : action === 'sleep' ? 85 : action === 'turn' ? Math.sin(t * 2) * 9 : 0;
  const e = EXPR[expression] || EXPR[0];
  const [mouthKind, browDy, browTilt, pupilScale] = e;
  const sleeping = action === 'sleep' || expression === 2;
  const eyeRy = sleeping ? 8 : 52;
  const pupilRy = sleeping ? 2 : Math.max(3, Math.round(17 * pupilScale * (expression === 8 ? 0.4 : 1)));
  const gx = sleeping ? 0 : gazeX, gy = 4;
  const legs = `M-42 130 L${-50 + walk} 268 M42 130 L${50 - walk} 268`;
  const arms = `M-78 10 Q-172 ${action === 'hang' ? -220 : 36 + walk} -182 ${action === 'hang' ? -280 : -44} M78 10 Q152 ${action === 'hang' ? -220 : action === 'point' ? -64 : 88} 192 ${action === 'hang' ? -280 : action === 'point' ? -112 : 28}`;
  return (
    <g transform={`translate(0 ${y}) rotate(${rotation})`} strokeLinecap="round" strokeLinejoin="round">
      {/* legs: black pants */}
      <path d={legs} fill="none" stroke={CHARACTER_COLORS.line} strokeWidth="52" />
      <path d={legs} fill="none" stroke={CHARACTER_COLORS.pants} strokeWidth="36" />
      {/* red sneakers with white stripe */}
      <g transform={`translate(${-72 + walk} 288) rotate(-4)`}>
        <ellipse rx="46" ry="22" fill={CHARACTER_COLORS.shoe} stroke={CHARACTER_COLORS.line} strokeWidth="8" />
        <path d="M-30 2 L28 2" stroke="white" strokeWidth="7" />
      </g>
      <g transform={`translate(${72 - walk} 288) rotate(4)`}>
        <ellipse rx="46" ry="22" fill={CHARACTER_COLORS.shoe} stroke={CHARACTER_COLORS.line} strokeWidth="8" />
        <path d="M-28 2 L30 2" stroke="white" strokeWidth="7" />
      </g>
      {/* shirt: yellow, jagged hem, white collar */}
      <path d="M-68 -34 L-110 118 L-64 96 L-32 128 L0 102 L32 128 L64 96 L110 118 L68 -34 Z"
        fill={CHARACTER_COLORS.shirt} stroke={CHARACTER_COLORS.line} strokeWidth="10" />
      <path d="M-34 -28 L0 14 L34 -28 L20 -34 L0 -6 L-20 -34 Z" fill="white" stroke={CHARACTER_COLORS.line} strokeWidth="7" />
      {/* arms */}
      <path d={arms} fill="none" stroke={CHARACTER_COLORS.line} strokeWidth="54" />
      <path d={arms} fill="none" stroke={CHARACTER_COLORS.skin} strokeWidth="38" />
      {/* head */}
      <circle cx="0" cy="-150" r="116" fill={CHARACTER_COLORS.skin} stroke={CHARACTER_COLORS.line} strokeWidth="11" />
      {/* hair curl */}
      <path d="M-24 -258 C -30 -286, 18 -288, 12 -258" fill="none" stroke={CHARACTER_COLORS.line} strokeWidth="10" />
      {/* eyes: huge white ovals with pupils */}
      <ellipse cx="-44" cy="-168" rx="36" ry={eyeRy} fill="white" stroke={CHARACTER_COLORS.line} strokeWidth="8" />
      <ellipse cx="46" cy="-168" rx="36" ry={eyeRy} fill="white" stroke={CHARACTER_COLORS.line} strokeWidth="8" />
      <ellipse cx={-44 + gx} cy={-162 + gy} rx="14" ry={pupilRy} fill={CHARACTER_COLORS.line} stroke="none" />
      <ellipse cx={46 + gx} cy={-162 + gy} rx="14" ry={expression === 9 ? 2 : pupilRy} fill={CHARACTER_COLORS.line} stroke="none" />
      {/* brows */}
      <g stroke={CHARACTER_COLORS.line} strokeWidth="12" fill="none">
        <path d={`M-84 ${-226 + browDy + browTilt} L-16 ${-226 + browDy - browTilt}`} />
        <path d={`M16 ${-226 + browDy - browTilt} L86 ${-226 + browDy + browTilt}`} />
      </g>
      <Mouth kind={mouthKind} frame={frame} />
    </g>
  );
};

// Choreographed presenter: walks in from offscreen to (x, y), then performs
// the beats list: [{frame, action, expression, duration}] in absolute frames;
// outside beats he idles with a subtle bob.
export const Mascot = ({frame, x, y, scale = 0.55, enterFrame = 0, beats = [], idleExpression = 0}) => {
  const enterDur = 45;
  const enter = interpolate(frame, [enterFrame, enterFrame + enterDur], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  if (enter <= 0) return null;
  const entering = enter < 1;
  const current = beats.filter(b => frame >= b.frame).pop();
  const action = entering ? 'walk' : (current?.action || 'idle');
  const expression = entering ? 0 : (current?.expression ?? idleExpression);
  const bob = entering || action !== 'idle' ? 0 : Math.sin(frame / 30 * 1.6) * 6;
  const px = interpolate(enter, [0, 1], [1080 + 260, x]);
  return (
    <g transform={`translate(${px} ${y + bob}) scale(${scale})`}>
      <MascotRig frame={frame} action={action === 'idle' ? 'point' : action} expression={expression} />
    </g>
  );
};
