/** Scientific mechanism checks on the actual Three.js geometry used in LockedFilm. */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import * as THREE from '../professional_motion/node_modules/three/build/three.module.js';
import {proceduralDirector} from '../professional_motion/procedural_story.js';
const kinds=['water_oil','water_oil','surfactant','micelle','soap_rinse','wash_timer','cleaning_compare','soap_finish'];
const d=proceduralDirector(new THREE.Scene(),{visual_plan:{world:'procedural_story'},scenes:kinds.map(kind=>({environment:'molecular_water',camera_start:[0,0,10],camera_end:[0,0,10],objects:[{kind,color:'#153e40',position:[0,0,0],scale:[1,1,1],rotation:[0,0,0],motion:'none'}]}))});
const micelle=d.stages[3].objects[0].object;assert.equal(micelle.userData.surfactants.length,38);
for(const s of micelle.userData.surfactants){const head=s.position.clone();const tail=new THREE.Vector3(-1.4,0,0).multiply(s.scale).applyQuaternion(s.quaternion).add(head);assert(tail.length()<head.length(),'Hydrophobic tails must point inward toward oil; hydrophilic heads face water');}
const layer=d.stages[0].objects[0].object;layer.updateMatrixWorld(true);const oilBox=new THREE.Box3().setFromObject(layer.userData.oil),waterBox=new THREE.Box3().setFromObject(layer.children[0]);assert(Math.abs(oilBox.min.y-waterBox.max.y)<.02,'Oil must meet the water interface, not float across an invented air gap');
d.update(6,1,12);const remaining=d.stages[6].objects[0].object.userData.dirt.filter(x=>x.visible).length;assert(remaining>0&&remaining<12,'Cleaning illustration must remove dirt without claiming complete sterilization');
const result={pass:true,geometry:'actual Three.js scene objects',micelle_molecules:38,tails_toward_oil:true,heads_toward_water:true,oil_water_interface_gap:oilBox.min.y-waterBox.max.y,cleaning_residual_illustrative_markers:remaining,scale_note:'Illustrative molecular shapes and relative sizes; not a measured simulation or microscope image'};
console.log(JSON.stringify(result,null,2));if(process.argv[2])await fs.writeFile(process.argv[2],JSON.stringify(result,null,2));
