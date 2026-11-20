// Vertical slice for the pro-motion spec: 7 scenes, blueprint-dark theme,
// storyboard.json first, validated plan, zone check, render, motion QA.
// Silent preview (no local TTS keys): synthetic word timings.
import {writeFile} from 'node:fs/promises';
import {renderEpisode} from './pipeline/render.mjs';
import {validatePlan} from './pipeline/drawplan.mjs';
import {camTargetsFor, zoneViolations, endCardProblems, autoLayoutLabels} from './src/paper/camera.js';
import {buildStoryboard, validateStoryboard} from './director/storyboard.mjs';
import {check as motionCheck} from './pipeline/motion-qa.mjs';

const sceneTexts = [
  'سنة ألف وتسعمية سبعة وتسعين أجهزة الرصد سجلت صوت غامض في أعماق المحيط',
  'الصوت كان أعلى من أي كائن حي معروف واتسمع من مسافة خمسة آلاف كيلومتر',
  'التسجيل اتنشر وسط تخمينات عن كائن ضخم مجهول بيعيش في الخندق',
  'العلماء قارنوا الترددات بكل الظواهر المعروفة من غير نتيجة',
  'بعد سنين المطابقة العلمية قالت إنه انشقاق جبل جليدي عملاق',
  'لكن التسجيل الأصلي لسه بيثير الأسئلة لحد النهارده',
  'القاع لسه بيخبي أسراره ومفيش حد سمع كل حاجة',
];
const meta = [
  {title: 'رصد غامض', summary: 'الصوت الأول', keyword: 'الرصد', template: 'phenomenon', labels: ['الرصد', 'المحيط']},
  {title: 'أعلى صوت', summary: 'خمسة آلاف كم', keyword: 'خمسة', template: 'stat', labels: ['خمسة', 'كيلومتر'], values: [{v: '5000', l: 'كيلومتر'}]},
  {title: 'تخمينات', summary: 'كائن مجهول؟', keyword: 'كائن', template: 'phenomenon', labels: ['كائن', 'خندق']},
  {title: 'مقارنة الترددات', summary: 'بلا نتيجة', keyword: 'الترددات', template: 'comparison', labels: ['الترددات', 'مقارنة']},
  {title: 'الحقيقة', summary: 'جليد ينشق', keyword: 'جليد', template: 'cause', labels: ['جليد', 'مطابقة']},
  {title: 'أسئلة باقية', summary: 'لغز مستمر', keyword: 'الأسئلة', template: 'journey', labels: ['الأسئلة', 'لغز']},
  {title: 'القاع يخبي', summary: 'أسرار المحيط', keyword: 'أسرار', template: 'quote', labels: ['أسرار', 'المحيط']},
];
const DUR = 8;
const scenes = sceneTexts.map((text, i) => {
  const ws = text.split(' ');
  return {...meta[i], text, duration: DUR, words: ws.map((w, k) => ({text: w, start: k * (DUR - 1) / ws.length, end: (k + 1) * (DUR - 1) / ws.length})), labels: meta[i].labels};
});
const props = {
  title: 'إيه الصوت الغامض اللي طلع من قاع المحيط؟',
  seriesLabel: 'أسرار المحيط', channelName: 'أسرار الكون',
  scenes, durationInFrames: scenes.length * DUR * 30, mascot: false,
  paper: {theme: 'blueprint-dark'},
};
const storyboard = buildStoryboard(props);
const sbProblems = validateStoryboard(storyboard);
if (sbProblems.length) { console.error('STORYBOARD INVALID:', sbProblems); process.exit(1); }
await writeFile('/tmp/slice-out/storyboard.json', JSON.stringify(storyboard, null, 2));
console.log('storyboard ok:', storyboard.scenes.map(s => s.template).join(', '));

const plan = {
  strokes: [
    {d: 'M 480 520 L 600 520 L 600 620 L 480 620 Z', width: 5, color: 'ink'},
    {d: 'M 540 620 L 540 700', width: 4, color: 'ink'},
    {d: 'M 640 540 C 700 560, 700 580, 640 600', width: 3, color: 'cyan'},
    {d: 'M 680 520 C 770 550, 770 590, 680 620', width: 3, color: 'cyan'},
    {d: 'M 120 1250 C 300 1200, 500 1280, 700 1230 C 850 1200, 950 1250, 980 1240', width: 4, color: 'ink'},
  ],
  fills: [
    {shape: 'path', d: 'M 120 1250 C 300 1200, 500 1280, 700 1230 C 850 1200, 950 1250, 980 1240 L 980 1480 L 120 1480 Z', color: 'blue', opacity: 0.5, hatch: true},
    {shape: 'circle', cx: 540, cy: 570, r: 12, color: 'gold', delay: 10},
  ],
  marks: [
    {x: 300, y: 560, r: 7, color: 'cyan', delay: 6},
    {x: 800, y: 700, r: 6, color: 'gold', delay: 9},
  ],
  labels: [
    {x1: 540, y1: 570, x2: 720, y2: 500, text: 'ميكروفون أعماق'},
    {x1: 540, y1: 1320, x2: 400, y2: 1400, text: 'قاع المحيط'},
  ],
  annotations: [
    {type: 'circle', x: 540, y: 570, r: 90, delay: 30, color: 'gold'},
    {type: 'magnifier', x: 440, y: 1120, zoom: 2.2, r: 110, delay: 30},
    {type: 'arrow', x1: 850, y1: 900, x2: 700, y2: 1070, delay: 25, color: 'gold'},
    {type: 'pip', x: 230, y: 430, w: 260, h: 150, delay: 35, text: 'التسجيل الأصلي'},
  ],
  scenes: [
    {strokes: [{d: 'M 720 540 C 800 570, 800 590, 720 640', width: 3, color: 'cyan'}, {d: 'M 400 540 C 340 560, 340 580, 400 600', width: 3, color: 'cyan'}, {d: 'M 200 760 C 400 730, 640 780, 880 740', width: 2, color: 'starBlue'}, {d: 'M 200 820 C 420 790, 660 840, 880 800', width: 2, color: 'cyan'}], fills: [], marks: [{x: 250, y: 745, r: 5, color: 'cyan', delay: 40}, {x: 830, y: 785, r: 5, color: 'gold', delay: 80}, {x: 500, y: 770, r: 4, color: 'starBlue', delay: 130}], labels: [], annotations: []},
    {strokes: [{d: 'M 380 900 L 700 900', width: 4, color: 'gold'}, {d: 'M 380 950 L 640 950', width: 3, color: 'cyan'}], fills: [], marks: [{x: 700, y: 900, r: 8, color: 'gold', delay: 8}], labels: [{x1: 700, y1: 900, x2: 760, y2: 830, text: 'خمسة آلاف'}], annotations: []},
    {strokes: [{d: 'M 380 1100 C 420 1050, 480 1050, 500 1100 C 520 1150, 460 1180, 420 1160 Z', width: 4, color: 'ink'}], fills: [], marks: [{x: 440, y: 1120, r: 6, color: 'gold', delay: 5}], labels: [], annotations: []},
    {strokes: [{d: 'M 300 800 C 400 780, 500 820, 600 800', width: 3, color: 'cyan'}, {d: 'M 300 860 C 400 890, 500 850, 600 870', width: 3, color: 'gold'}], fills: [], marks: [], labels: [{x1: 600, y1: 800, x2: 700, y2: 750, text: 'تردد معروف'}, {x1: 600, y1: 870, x2: 700, y2: 930, text: 'تردد اللغز'}], annotations: []},
    {strokes: [{d: 'M 620 1080 L 700 1000 L 780 1080 L 700 1140 Z', width: 4, color: 'starBlue'}], fills: [{shape: 'circle', cx: 700, cy: 1070, r: 9, color: 'gold', delay: 6}], marks: [], labels: [{x1: 700, y1: 1070, x2: 830, y2: 990, text: 'انشقاق الجليد'}], annotations: []},
    {strokes: [{d: 'M 420 700 C 460 660, 540 660, 580 700 C 540 740, 460 740, 420 700 Z', width: 3, color: 'cyan'}], fills: [], marks: [{x: 500, y: 700, r: 5, color: 'gold', delay: 4}], labels: [], annotations: []},
    {strokes: [{d: 'M 200 1000 C 400 950, 600 1030, 880 980', width: 3, color: 'ink'}, {d: 'M 200 1060 C 400 1010, 600 1090, 880 1040', width: 2, color: 'cyan'}], fills: [], marks: [], labels: [], annotations: []},
  ],
  endStat: 'خمسة آلاف كيلومتر',
  summaryPoints: ['الصوت اتحفظ في تسجيل رسمي', 'التخمينات الأولى كانت كائن ضخم', 'المطابقة قالت جليد ينشق'],
};
const labelMoves = autoLayoutLabels(plan);
if (labelMoves.length) console.log('labels auto-laid-out:', labelMoves.join(' | '));
if (labelMoves.some(m => m.startsWith('NO_HOME'))) { console.error('LABEL LAYOUT FAILED'); process.exit(1); }
const problems = validatePlan(plan, scenes.length).concat(endCardProblems(plan));
if (problems.length) { console.error('PLAN INVALID:', problems); process.exit(1); }
props.paper.plan = plan;
const windows = scenes.map((s, i) => ({start: i * DUR * 30, frames: DUR * 30}));
const layers = [{strokes: plan.strokes, fills: plan.fills, marks: plan.marks, labels: plan.labels, annotations: plan.annotations}, ...plan.scenes];
const targets = camTargetsFor(windows, layers);
const violations = zoneViolations(windows, layers, targets);
if (violations.length) { console.error('ZONE VIOLATIONS:', violations.slice(0, 10)); process.exit(1); }
console.log('zone check clean; scales:', targets.map(t => t.s.toFixed(2)).join(', '));
const t0 = Date.now();
const result = await renderEpisode(props, '/tmp/slice-out', {filename: 'vertical-slice.mp4'});
const secs = (Date.now() - t0) / 1000;
console.log('rendered', result.file, 'in', secs, 's');
const qa = motionCheck(result.file, scenes.map(() => ({duration: DUR})), {out: '/tmp/slice-out/motion-qa.json'});
console.log('motion-qa passed:', qa.passed, qa.scenes.map(s => s.meanDiff).join(','));
if (!qa.passed) process.exit(1);
