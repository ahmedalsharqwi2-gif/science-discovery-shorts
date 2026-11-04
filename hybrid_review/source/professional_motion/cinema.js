/** Opt-in science cinematography. Existing subject geometry remains authoritative. */
import * as THREE from 'three';
import {scienceShot} from './science_shots.js';

export function scienceCinema({scene,camera,renderer}) {
 const key=scene.children.find(o=>o.isDirectionalLight);
 if(key){key.color.setHex(0xf3f5ff);key.intensity=2.1;key.position.set(4,6,7);}
 const rim=new THREE.DirectionalLight(0x78bede,1.35);rim.position.set(-5,2,-4);scene.add(rim);
 renderer.toneMappingExposure=1.04;
 // A deterministic, low-cost observatory backdrop supplies depth cues without
 // introducing extra planets, field lines or other scientifically loaded objects.
 const backdrop=new THREE.Group();backdrop.name='science-observatory-depth';scene.add(backdrop);
 let seed=1945;const random=()=>{seed=(1664525*seed+1013904223)>>>0;return seed/4294967296;};
 const positions=new Float32Array(160*3);
 for(let i=0;i<160;i++){positions[i*3]=(random()-.5)*34;positions[i*3+1]=(random()-.5)*32;positions[i*3+2]=-12-random()*18;}
 const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.BufferAttribute(positions,3));
 const points=new THREE.Points(geometry,new THREE.PointsMaterial({color:0xa0b4c2,size:.025,transparent:true,opacity:.55,depthWrite:false}));backdrop.add(points);
 const target=new THREE.Vector3();
 return {
  update(story,index,progress,time){
   const shot=scienceShot(index,progress);
   // Offset from the author's framing, preserving close-up and explanatory views.
   camera.position.x+=shot.truck;camera.position.y+=shot.crane;camera.position.z+=shot.dolly;
   target.set(shot.targetX,.35+shot.targetY,0);camera.lookAt(target);
   backdrop.rotation.y=shot.truck*.014;backdrop.position.x=-shot.truck*.12;
   points.material.opacity=story.visual_family==='space'?.32:.16;
   return {version:2,shot:shot.name,time};
  },
  dispose(){geometry.dispose();points.material.dispose();scene.remove(backdrop,rim);}
 };
}

