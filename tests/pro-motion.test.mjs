import test from 'node:test';
import assert from 'node:assert/strict';
import {buildStoryboard, validateStoryboard} from '../director/storyboard.mjs';
import {motionEnergy} from '../pipeline/motion-qa.mjs';
import tokens from '../brand/motion-tokens.json' with {type: 'json'};

const ep = t => ({title: 'عنوان', scenes: t.map(template => ({template, text: 'نص المشهد هنا', keyword: 'كلمة', labels: ['كلمة'], duration: 8}))});

test('storyboard: template by information type, no adjacent repeat', () => {
  const sb = buildStoryboard(ep(['phenomenon', 'phenomenon', 'stat', 'comparison']));
  assert.deepEqual(validateStoryboard(sb), []);
  assert.notEqual(sb.scenes[0].template, sb.scenes[1].template);
  assert.equal(sb.scenes[2].template, 'big-number');
  assert.equal(sb.scenes[3].template, 'comparison');
  assert.ok(sb.scenes[1].swappedFrom);
});
test('storyboard: emphasis carries keyword and labels; transitions cycle', () => {
  const sb = buildStoryboard(ep(['phenomenon', 'cause', 'journey']));
  assert.deepEqual(sb.scenes[0].emphasis, ['كلمة']);
  assert.equal(sb.scenes[0].transitionIn, null);
  assert.ok(sb.scenes[1].transitionIn);
});
test('storyboard: empty episode is invalid', () => {
  assert.ok(validateStoryboard(buildStoryboard({title: 'x', scenes: []})).length > 0);
});
test('tokens: both themes complete, safe area and durations per spec', () => {
  for (const name of ['paper-technical', 'blueprint-dark']) {
    const t = tokens.themes[name];
    for (const k of ['paper', 'ink', 'grid', 'cyan', 'gold']) assert.ok(t[k], name + ' missing ' + k);
  }
  assert.deepEqual(tokens.canvas.durationRangeSeconds, [90, 180]);
  assert.equal(tokens.safeArea.topPx, 150);
  assert.equal(tokens.safeArea.bottomPx, 250);
  assert.equal(tokens.sound.loudnessLUFS, -14);
});
test('motion energy: static frames score ~0, changing frames score high', () => {
  const a = Buffer.alloc(64 * 36, 0), b = Buffer.alloc(64 * 36, 0), c = Buffer.alloc(64 * 36, 200);
  assert.deepEqual(motionEnergy([a, b]), [0]);
  assert.ok(motionEnergy([b, c])[0] > 100);
});
