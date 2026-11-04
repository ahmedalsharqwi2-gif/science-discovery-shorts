import assert from 'node:assert/strict';
import * as THREE from './source/professional_motion/node_modules/three/build/three.module.js';
import {proceduralDirector} from './source/professional_motion/procedural_story.js';
const spec={kind:'micelle',position:[0,0,0],scale:[1,1,1],rotation:[0,0,0],motion:'assemble',color:'#45c5ca'};
const story={visual_plan:{world:'procedural_story'},scenes:Array.from({length:8},()=>({environment:'molecular_water',camera_start:[0,0,10],camera_end:[0,0,9],objects:[spec]}))};
const scene=new THREE.Scene(),director=proceduralDirector(scene,story);
assert.equal(director.stages.length,8);
for(const stage of director.stages){const parts=stage.objects[0].object.userData.surfactants;assert.equal(parts.length,38);for(const part of parts){const outward=part.userData.radial;const tail=new THREE.Vector3(-1,0,0).applyQuaternion(part.quaternion);assert.ok(tail.dot(outward)<-.999,'Tail must point toward oil, away from surrounding water');}}
director.update(3,.5,2);assert.equal(director.stages.filter(s=>s.group.visible).length,1);
assert.throws(()=>proceduralDirector(new THREE.Scene(),{visual_plan:{world:'procedural_story'},scenes:[]}),/eight-scene/);
console.log('38 inward-facing tails per micelle, all eight stages, scene visibility, invalid plan checks passed');
