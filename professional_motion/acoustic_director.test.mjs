import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import {readFileSync} from 'node:fs';
import {acousticDirector} from './acoustic_director.js';
const catalog=JSON.parse(readFileSync(new URL('./director_catalog.json',import.meta.url)));
const rows=catalog.worlds.sound_wave_lab.compatible_beats;
const story={topic_key:'sound-waves',source:{url:'https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/speed-of-sound-interactive/'},visual_plan:{world:'sound_wave_lab',scenes:rows}};
test('every catalog action has its own executable geometry, visibility and camera',()=>{
 const d=acousticDirector(new THREE.Scene(),story);
 rows.forEach((row,i)=>{const view=d.update(i,.5,2);
  assert.equal(Object.values(d.stages).filter(s=>s.group.visible).length,1);
  assert.equal(d.stages[row.action].group.visible,true);
  assert.equal(view.action,row.action);assert.ok(view.position.every(Number.isFinite));
 });
});
test('air parcels oscillate locally, medium absence has no propagating particles, reflection has a boundary',()=>{
 const d=acousticDirector(new THREE.Scene(),story),i=rows.findIndex(r=>r.action==='parcel_compress');
 d.update(i,.1,1);const a=d.stages.parcel_compress.rows[0].dots.instanceMatrix.array.slice();
 d.update(i,.8,2);const b=d.stages.parcel_compress.rows[0].dots.instanceMatrix.array;
 assert.ok(a.some((value,i)=>value!==b[i]));
 for(let i=12;i<a.length;i+=16)assert.ok(Math.abs(a[i]-b[i])<.33);
 assert.equal(d.stages.medium_remove.rows[0].dots.visible,false);
 assert.ok(d.stages.boundary_reflect.wall);
});
test('a different topic or source cannot borrow the acoustic apparatus',()=>{
 assert.throws(()=>acousticDirector(new THREE.Scene(),{...story,topic_key:'jupiter-storms'}),/Unsupported/);
 assert.throws(()=>acousticDirector(new THREE.Scene(),{...story,source:{url:'https://example.com'}}),/Exact verified/);
});
