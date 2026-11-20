// Local proof render C: new science direction (strange/unsettling real
// discovery) - the 1997 NOAA "Bloop" mystery. Silent preview (no local TTS
// keys): synthetic even word timings drive the kinetic captions. Hand-built
// plan exercising annotations (arrow, magnifier, circle, pip) + hatch fill.
import {readFile, writeFile} from 'node:fs/promises';
import {renderEpisode} from './pipeline/render.mjs';
import {validatePlan} from './pipeline/drawplan.mjs';
import {camTargetsFor, zoneViolations} from './src/paper/camera.js';

const sceneTexts = [
  'في صوت اتحفظ في أعماق المحيط أعلى من أي كائن حي ومحطات الرصد سمعته من مسافة خمسة آلاف كيلومتر',
  'التسجيل اتنشر وسط تخمينات عن كائن ضخم مجهول بيعيش في الخندق وبقى لغز لسنين',
  'وفي النهاية المطابقة العلمية قالت إنه انشقاق جبل جليدي عملاق لكن التسجيل لسه بيرعب اللي يسمعه',
];
const sceneMeta = [
  {title: 'صوت من العمق', summary: 'رصد غامض', keyword: 'الصوت', template: 'phenomenon', labels: ['الصوت', 'المحيط'], values: [], kind: 'fact', expression: 3, action: 'point'},
  {title: 'تخمينات مخيفة', summary: 'كائن مجهول؟', keyword: 'كائن', template: 'cause', labels: ['كائن', 'خندق'], values: [], kind: 'legend', expression: 7, action: 'turn'},
  {title: 'الحقيقة', summary: 'جليد ينشق', keyword: 'جليد', template: 'journey', labels: ['جليد', 'مطابقة'], values: [], kind: 'fact', expression: 1, action: 'idle'},
];
const DUR = 8;
const scenes = sceneTexts.map((text, i) => {
  const ws = text.split(' ');
  return {...sceneMeta[i], text, duration: DUR, words: ws.map((w, k) => ({text: w, start: k * (DUR - 1) / ws.length, end: (k + 1) * (DUR - 1) / ws.length})), labels: sceneMeta[i].labels, values: [], claim: '', sourceId: 'local-proof', evidence: '', brollQuery: ''};
});
const props = {
  title: 'إيه الصوت الغامض اللي طلع من قاع المحيط؟',
  seriesLabel: 'أسرار المحيط',
  channelName: 'أسرار الكون',
  scenes,
  durationInFrames: scenes.length * DUR * 30,
  mascot: false,
  paper: {},
};

const plan = {
  strokes: [
    // hydrophone + sound arcs spreading through the deep
    {d: 'M 480 520 L 600 520 L 600 620 L 480 620 Z', width: 5, color: 'ink'},
    {d: 'M 540 620 L 540 700', width: 4, color: 'ink'},
    {d: 'M 640 540 C 700 560, 700 580, 640 600', width: 3, color: 'cyan'},
    {d: 'M 680 520 C 770 550, 770 590, 680 620', width: 3, color: 'cyan'},
    {d: 'M 120 1250 C 300 1200, 500 1280, 700 1230 C 850 1200, 950 1250, 980 1240', width: 4, color: 'ink'},
  ],
  fills: [
    {shape: 'path', d: 'M 120 1250 C 300 1200, 500 1280, 700 1230 C 850 1200, 950 1250, 980 1240 L 980 1480 L 120 1480 Z', color: 'blue', opacity: 0.5, hatch: true, delay: 8},
    {shape: 'circle', cx: 540, cy: 570, r: 12, color: 'gold', delay: 10},
  ],
  marks: [
    {x: 300, y: 560, r: 7, color: 'cyan', delay: 6},
    {x: 800, y: 700, r: 6, color: 'gold', delay: 9},
  ],
  labels: [
    {x1: 540, y1: 570, x2: 720, y2: 500, text: 'ميكروفون أعماق'},
    {x1: 540, y1: 1320, x2: 320, y2: 1400, text: 'قاع المحيط'},
  ],
  annotations: [],
  scenes: [
    {strokes: [{d: 'M 720 540 C 800 570, 800 590, 720 640', width: 3, color: 'cyan'}, {d: 'M 400 540 C 340 560, 340 580, 400 600', width: 3, color: 'cyan'}], fills: [], marks: [{x: 750, y: 590, r: 5, color: 'cyan'}], labels: [{x1: 760, y1: 590, x2: 860, y2: 560, text: 'خمسة آلاف كيلومتر'}], annotations: [{type: 'arrow', x1: 880, y1: 700, x2: 700, y2: 600, color: 'red', delay: 8}]},
    {strokes: [{d: 'M 380 1100 C 420 1050, 480 1050, 500 1100 C 520 1150, 460 1180, 420 1160 Z', width: 4, color: 'ink'}], fills: [], marks: [{x: 440, y: 1090, r: 6, color: 'red'}], labels: [{x1: 440, y1: 1100, x2: 250, y2: 1050, text: 'كائن مجهول؟'}], annotations: [{type: 'magnifier', x: 440, y: 1110, r: 120, zoom: 2, delay: 6}]},
    {strokes: [{d: 'M 620 1080 L 700 1000 L 780 1080 L 700 1140 Z', width: 4, color: 'starBlue'}], fills: [{shape: 'circle', cx: 700, cy: 1070, r: 9, color: 'red'}], marks: [{x: 700, y: 1020, r: 6, color: 'red'}], labels: [{x1: 700, y1: 1070, x2: 820, y2: 990, text: 'جليد ينشق'}], annotations: [{type: 'circle', x: 700, y: 1070, r: 80, color: 'red', delay: 4}, {type: 'pip', x: 830, y: 1330, w: 300, h: 200, text: 'تسجيل حقيقي', delay: 12}]},
  ],
  endStat: 'خمسة آلاف كيلومتر',
  summaryPoints: ['الصوت اتحفظ في تسجيل رسمي', 'التخمينات الأولى كانت كائن ضخم', 'المطابقة قالت جليد ينشق'],
};

const problems = validatePlan(plan, 3);
if (problems.length) { console.error('PLAN INVALID:', problems); process.exit(1); }
console.log('plan valid');
props.paper = {plan};

// zone-overlap check: no drawing element may enter the title or captions
// zones under any scene's camera (settled zoom and push-in peak).
const windows = scenes.map((s, i) => ({start: i * DUR * 30, frames: DUR * 30}));
const layers = [{strokes: plan.strokes, fills: plan.fills, marks: plan.marks, labels: plan.labels, annotations: plan.annotations}, ...plan.scenes];
const targets = camTargetsFor(windows, layers);
const violations = zoneViolations(windows, layers, targets);
if (violations.length) { console.error('ZONE VIOLATIONS:', violations.slice(0, 10)); process.exit(1); }
console.log('zone check clean; camera scales:', targets.map(t => t.s.toFixed(3)).join(', '));

await writeFile('/tmp/proof-props.json', JSON.stringify(props));
const t0 = Date.now();
const result = await renderEpisode(props, '/tmp/proof-out', {filename: 'proof.mp4'});
console.log('seconds', (Date.now() - t0) / 1000);
console.log('rendered', result.file);
