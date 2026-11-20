import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {coerceNumericStrings} from '../pipeline/drawplan.mjs';

test('paper channels never silently fall back to the classic template', async () => {
  const run = await readFile('pipeline/run.mjs', 'utf8');
  assert.equal(run.includes('classic template instead'), false, 'silent classic fallback returned');
});

test('drawplan coercion converts numeric strings before validation and leaves true junk invalid', () => {
  const plan = {scenes: [{annotations: [{type: 'arrow', x1: '350', y1: '400', x2: '900.5', y2: '1200'}], marks: [{x: 'abc', y: 5}]}]};
  coerceNumericStrings(plan);
  const a = plan.scenes[0].annotations[0];
  assert.deepEqual([a.x1, a.y1, a.x2, a.y2], [350, 400, 900.5, 1200]);
  assert.equal(plan.scenes[0].marks[0].x, 'abc', 'non-numeric strings must still fail validation');
});
