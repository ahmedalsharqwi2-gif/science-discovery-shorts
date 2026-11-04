import * as THREE from 'three';
import {proceduralDirector} from './procedural_story.js';
import {scienceCinema} from './cinema.js';
const renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});renderer.setSize(720,1280);renderer.setPixelRatio(1);renderer.setClearColor('#e5f2ed');renderer.toneMapping=THREE.ACESFilmicToneMapping;document.body.appendChild(renderer.domElement);
const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(35,9/16,.1,100);
scene.add(new THREE.HemisphereLight('#ffffff','#839b9b',2.8));const key=new THREE.DirectionalLight('#ffffff',3);key.position.set(4,7,8);scene.add(key);
const spec=(kind,position,scale,motion='none',rotation=[0,0,0],color='#45c5ca')=>({kind,position,scale,motion,rotation,color});
const scenes=Array.from({length:8},(_,i)=>({environment:'molecular_water',camera_start:[0,.3,10],camera_end:[.2,.4,9.4],objects:i===2?[spec('surfactant',[.75,0,0],[1.05,1.05,1.05],'spin')]:i===3?[spec('micelle',[0,0,0],[.72,.72,.72],'assemble')]:[spec('surfactant',[0,0,0],[1,1,1],'float')]}));
const story={profile:'science',visual_family:'chemistry',visual_plan:{world:'procedural_story'},scenes};
const director=proceduralDirector(scene,story),cinema=scienceCinema({scene,camera,renderer});
// Keep the legacy camera/light director, omit its space-like decorative points.
scene.getObjectByName('science-observatory-depth').visible=false;
window.renderAt=(seconds)=>{
 seconds=Math.max(0,seconds-.56);
 const second=seconds>=16.72,index=second?3:2,local=second?seconds-16.72:seconds,duration=second?17.96:16.72,p=Math.min(1,local/duration);
 const view=director.update(index,p,local);camera.position.set(...view.position);camera.lookAt(0,0,0);cinema.update(story,index,p,seconds);
 const object=director.stages[index].objects[0].object;
 // All surfactant tails point inward toward oil, hydrophilic heads outward.
 if(second){object.rotation.y=seconds*.12;const gather=Math.min(1,local/5);for(const part of object.userData.surfactants||[]){part.position.copy(part.userData.radial).multiplyScalar(1.95+(1-gather)*1.2);}}
 renderer.render(scene,camera);return {index,review_only:true,engines:['proceduralDirector','scienceCinema']};
};
window.captureFrame=()=>renderer.domElement.toDataURL('image/jpeg',.94).split(',')[1];window.renderAt(0);window.ready=true;
