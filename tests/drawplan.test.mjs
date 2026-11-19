import {test} from 'node:test';
import assert from 'node:assert/strict';
import {parsePath, validatePlan, drawplan, DRAW_BOX} from '../pipeline/drawplan.mjs';

const goodStroke = {d: 'M 100 500 L 300 500 C 400 500, 500 600, 500 700 Z', width: 4, color: 'ink'};
const goodPlan = (sceneCount) => ({
  strokes: [goodStroke],
  fills: [{cx: 540, cy: 900, r: 120, color: 'cyan'}, {shape: 'path', d: 'M 500 800 L 580 800 L 540 900 Z', color: '#ffda34'}],
  marks: [{x: 200, y: 600, r: 10, color: 'gold'}],
  labels: [{x1: 540, y1: 900, x2: 800, y2: 850, text: 'الكرة الأرضية'}],
  scenes: Array.from({length: sceneCount}, () => ({strokes: [], fills: [], marks: [{x: 300, y: 700, r: 6}], labels: []})),
  endStat: '١٦٧٠ كم/ساعة',
  summaryPoints: ['نقطة أولى قصيرة', 'نقطة تانية قصيرة', 'نقطة تالتة قصيرة'],
});

function mockClient(plans) {
  let calls = 0;
  return {
    calls: () => calls,
    async generate() {
      const plan = plans[Math.min(calls, plans.length - 1)];
      calls++;
      return {candidates: [{content: {parts: [{text: JSON.stringify(plan)}]}}], _pipeline: {model: 'mock-model'}};
    },
  };
}

test('parsePath accepts absolute M/L/C/Z paths', () => {
  assert.equal(parsePath('M 100 200 L 300 400 Z').ok, true);
  assert.equal(parsePath('M 100 200 C 150 250, 200 250, 250 200').ok, true);
});

test('parsePath rejects relative commands, arcs and out-of-canvas points', () => {
  assert.match(parsePath('M 100 200 l 50 50').error, /relative/);
  assert.match(parsePath('M 100 200 A 50 50 0 0 1 300 300').error, /unsupported tokens/);
  assert.match(parsePath('M 100 200 L 3000 400').error, /outside canvas/);
  assert.match(parsePath('M 100 200 Z L 5 5').error, /after Z/);
});

test('validatePlan passes a well-formed plan', () => {
  assert.deepEqual(validatePlan(goodPlan(9), 9), []);
});

test('validatePlan catches scene-count mismatch, bad paths and cap breaches', () => {
  const plan = goodPlan(9);
  assert.ok(validatePlan(plan, 8).some(p => p.includes('scene count')));
  const bad = goodPlan(9);
  bad.strokes = [{d: 'M 0 0 L 50 50', color: 'ink'}]; // y=0 above the drawing box is fine for path coords? paths may roam canvas; color check only
  bad.fills = [{cx: 10, cy: 10, r: 5, color: 'cyan'}];
  assert.ok(validatePlan(bad, 9).some(p => p.includes('outside drawing box')));
  const many = goodPlan(9);
  many.strokes = Array.from({length: 95}, () => goodStroke);
  assert.ok(validatePlan(many, 9).some(p => p.includes('exceeds cap')));
  const longLabel = goodPlan(9);
  longLabel.labels = [{x1: 540, y1: 900, x2: 700, y2: 850, text: 'كلمة '.repeat(20)}];
  assert.ok(validatePlan(longLabel, 9).some(p => p.includes('1-24 chars')));
  assert.ok(DRAW_BOX.y0 > 0 && DRAW_BOX.y1 < 1920);
});

test('drawplan retries with feedback after an invalid plan, then succeeds', async () => {
  const invalid = goodPlan(9);
  invalid.scenes = invalid.scenes.slice(0, 5); // wrong scene count
  const client = mockClient([invalid, goodPlan(9)]);
  const {plan, drawModel} = await drawplan({title: 't', hook: 'h', scenes: Array.from({length: 9}, () => ({title: 's', summary: 'x', keyword: 'k', template: 'phenomenon', labels: ['أ', 'ب']}))}, {name: 'افترض كده'}, {client});
  assert.equal(client.calls(), 2);
  assert.equal(drawModel, 'mock-model');
  assert.equal(plan.scenes.length, 9);
});

test('drawplan throws DRAWPLAN_SCHEMA_INVALID after 3 invalid attempts', async () => {
  const invalid = goodPlan(9);
  invalid.endStat = '';
  const client = mockClient([invalid]);
  await assert.rejects(
    drawplan({title: 't', hook: 'h', scenes: Array.from({length: 9}, () => ({title: 's', summary: 'x', keyword: 'k', template: 'steps', labels: ['أ', 'ب']}))}, {name: 'x'}, {client}),
    /DRAWPLAN_SCHEMA_INVALID/);
  assert.equal(client.calls(), 3);
});

test('a scene adding zero visible ops is rejected so the drawing must evolve', () => {
  const plan = goodPlan(3);
  plan.scenes[1] = {strokes: [], fills: [], marks: [], labels: []};
  assert(validatePlan(plan, 3).some(p => p.includes('adds no visible ops')));
});

test('digits and Latin letters are rejected in endStat, labels and summaryPoints', () => {
  const plan = goodPlan(2);
  plan.endStat = '400 كم ارتفاع المدار';
  assert(validatePlan(plan, 2).some(p => p.includes('endStat must write numbers as Arabic words')));
  plan.endStat = 'أربعمائة كم ارتفاع المدار';
  plan.labels = [{x1: 540, y1: 900, x2: 800, y2: 850, text: 'بحيرة Pelku'}];
  assert(validatePlan(plan, 2).some(p => p.includes('no Latin letters')));
  plan.labels = [{x1: 540, y1: 900, x2: 800, y2: 850, text: 'بحيرة عميقة'}];
  plan.summaryPoints = ['نقطة فيها 3 أشياء', 'نقطة تانية قصيرة', 'نقطة تالتة قصيرة'];
  assert(validatePlan(plan, 2).some(p => p.includes('summaryPoints 0')));
});
