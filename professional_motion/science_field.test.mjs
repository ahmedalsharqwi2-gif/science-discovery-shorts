import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import {scienceField,MMS_SPACECRAFT_COUNT} from './science_field.js';
test('the sourced mission scene contains exactly four individual spacecraft',()=>{
 const scene=new THREE.Scene(),field=scienceField(scene);
 const state=field.update(6,.5,120);
 assert.equal(MMS_SPACECRAFT_COUNT,4);assert.equal(state.spacecraft,4);
 assert.equal(state.notToScale,true);
 let spacecraft=0;field.root.traverse(o=>{if(/^MMS-[1-4]$/.test(o.name))spacecraft++;});
 assert.equal(spacecraft,4);
});
test('scene meaning switches geometry rather than relabelling one repeated globe',()=>{
 const scene=new THREE.Scene(),field=scienceField(scene);
 assert.equal(field.update(2,.5,42).mode,'earth-mars-comparison');
 assert.equal(field.update(5,.5,103).mode,'qualitative-reconnection');
 assert.equal(field.update(6,.5,125).mode,'four-spacecraft-formation');
 assert.equal(field.update(0,.5,2).mode,'dipole-and-solar-wind');
 assert.equal(field.root.children.filter(o=>o.visible).length,1);
});
