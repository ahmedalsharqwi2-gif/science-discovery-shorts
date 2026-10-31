import test from 'node:test';
import assert from 'node:assert/strict';
import {scienceShot} from './science_shots.js';
test('every authored science shot stays bounded at every frame and eases at endpoints',()=>{
 for(let shot=0;shot<8;shot++){
  const begin=scienceShot(shot,0),end=scienceShot(shot,1);
  for(let frame=0;frame<=1800;frame++){
   const position=scienceShot(shot,frame/1800);
   assert.ok(Math.abs(position.truck)<=.35);
   assert.ok(Math.abs(position.crane)<=.12);
   assert.ok(Math.abs(position.dolly)<=.7);
  }
  assert.ok(Math.abs(scienceShot(shot,.0001).truck-begin.truck)<1e-6);
  assert.ok(Math.abs(scienceShot(shot,.9999).truck-end.truck)<1e-6);
 }
});
test('invalid authored shots fail, and out-of-range time clamps to endpoints',()=>{
 assert.deepEqual(scienceShot(0,-1),scienceShot(0,0));
 assert.deepEqual(scienceShot(7,2),scienceShot(7,1));
 assert.throws(()=>scienceShot(8,0));assert.throws(()=>scienceShot(0,NaN));
});
