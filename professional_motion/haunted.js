import * as THREE from 'three';
// Original procedural sets, props and silhouette. No sampled film imagery.
export function hauntedStage(parent){
 const root=new THREE.Group();parent.add(root);
 const groups={},mat=(c,r=.8,m=.03)=>new THREE.MeshStandardMaterial({color:c,roughness:r,metalness:m});
 const plaster=mat(0x62645a,.98),wood=mat(0x45352d,.86),metal=mat(0x626960,.5,.55),black=mat(0x020304,.95),red=new THREE.MeshStandardMaterial({color:0x982c21,emissive:0xa43122,emissiveIntensity:1});
 const mesh=(g,geo,m,x=0,y=0,z=0)=>{const o=new THREE.Mesh(geo,m);o.position.set(x,y,z);g.add(o);return o;};
 const box=(g,w,h,d,m,x=0,y=0,z=0)=>mesh(g,new THREE.BoxGeometry(w,h,d),m,x,y,z);
 const group=n=>{const g=new THREE.Group();root.add(g);groups[n]=g;return g;};
 function lamp(g,c,i,x,y,z,range=8){const l=new THREE.PointLight(c,i,range,2);l.position.set(x,y,z);g.add(l);return l;}
 // Long corridor: scratched timber floor, uneven plaster and recessed doors.
 const hall=group('hall');
 box(hall,4,.12,20,wood,0,-1.6,-5);box(hall,4,.13,20,plaster,0,2.05,-5);
 box(hall,.13,3.7,20,plaster,-2,.2,-5);box(hall,.13,3.7,20,plaster,2,.2,-5);box(hall,4,3.7,.2,plaster,0,.2,-14.8);
 for(let j=0;j<42;j++)box(hall,3.95,.012,.015,metal,0,-1.53,4.7-j*.47);
 for(let side of [-1,1]){
  box(hall,.04,.12,20,wood,side*1.91,-1.36,-5);
  for(let i=0;i<4;i++){
   const d=box(hall,.09,2.65,1.25,wood,side*1.9,-.1,2-i*4.0);box(hall,.04,2.8,.06,metal,side*1.83,-.1,1.31-i*4.0);box(hall,.04,2.8,.06,metal,side*1.83,-.1,2.69-i*4.0);
   mesh(hall,new THREE.SphereGeometry(.045,10,8),metal,side*1.8,-.08,2.45-i*4);
  }
 }
 const hinge=new THREE.Group();hall.add(hinge);hinge.position.set(-.72,-.1,-14.55);box(hinge,1.44,2.72,.11,wood,.72,0,0);mesh(hinge,new THREE.SphereGeometry(.055,12,10),metal,1.25,-.12,.11);
 const corridorLights=[];
 for(let i=0;i<4;i++){box(hall,.48,.06,.18,metal,0,1.9,2-i*4.6);corridorLights.push(lamp(hall,i%2?0x688f79:0xd5a979,30,0,1.72,2-i*4.6));}
 const figure=new THREE.Group();hall.add(figure);figure.position.set(0,-.68,-14.4);
 mesh(figure,new THREE.SphereGeometry(.22,20,16),black,0,1.08,0);mesh(figure,new THREE.CylinderGeometry(.28,.38,1.1,16),black,0,.4,0);
 for(const sign of [-1,1]){const arm=mesh(figure,new THREE.CylinderGeometry(.07,.095,1.0,10),black,sign*.32,.35,0);arm.rotation.z=sign*.12;mesh(figure,new THREE.CylinderGeometry(.09,.1,.78,10),black,sign*.13,-.48,0);}
 const doorwayLight=lamp(hall,0x4b8c84,7,0,.3,-14,5);
 // Close props have their own worn wall so the film alternates space and detail.
 const phone=group('phone');box(phone,4.6,5,.13,plaster,0,0,-.3);box(phone,1.4,2.15,.22,metal,0,0,0);
 box(phone,.34,1.55,.35,wood,-.42,.07,.23);box(phone,.55,.38,.3,wood,-.42,.82,.23);box(phone,.55,.38,.3,wood,-.42,-.68,.23);
 for(let i=0;i<18;i++)box(phone,.39,.016,.025,black,.3,.72-i*.039,.135);
 const phoneLED=mesh(phone,new THREE.SphereGeometry(.038,12,10),red,.35,-.55,.17);
 const handset=phone.children[2];const cablePoints=[];for(let i=0;i<90;i++)cablePoints.push(new THREE.Vector3(-.42+Math.cos(i*.65)*.06,-.75-i*.012,.16+Math.sin(i*.65)*.06));
 mesh(phone,new THREE.TubeGeometry(new THREE.CatmullRomCurve3(cablePoints),100,.016,6,false),black);
 lamp(phone,0xa1a889,48,-1,2,2,8);lamp(phone,0x8f372a,3,1,-1,1,5);
 const clock=group('clock');box(clock,4.5,5,.15,plaster,0,0,-.3);mesh(clock,new THREE.CylinderGeometry(1.05,1.05,.18,64),metal,0,0,0).rotation.x=Math.PI/2;
 mesh(clock,new THREE.CircleGeometry(.91,64),mat(0xc2bb9a,.8),0,0,.1);
 for(let i=0;i<12;i++){const tick=box(clock,.025,i%3===0?.15:.08,.02,black,Math.sin(i*Math.PI/6)*.79,Math.cos(i*Math.PI/6)*.79,.125);tick.rotation.z=-i*Math.PI/6;}
 const hands=[];for(let i=0;i<3;i++){const h=new THREE.Group();clock.add(h);h.position.z=.15+i*.015;box(h,i===2?.018:.035,[.48,.68,.73][i],.02,i===2?red:black,0,[.24,.34,.365][i],0);hands.push(h);}
 lamp(clock,0xb1ad8b,25,-2,2,2,8);
 const mirror=group('mirror');box(mirror,4.8,5,.16,plaster,0,0,-.35);box(mirror,2.08,3.03,.15,metal,0,0,0);box(mirror,1.86,2.82,.04,mat(0x0a171a,.13,.8),0,0,.1);
 const reflection=new THREE.Group();mirror.add(reflection);reflection.position.set(.2,-.7,.14);mesh(reflection,new THREE.SphereGeometry(.18,20,14),black,0,.85,0);mesh(reflection,new THREE.CylinderGeometry(.23,.31,.95,16),black,0,.25,0);
 for(let i=0;i<8;i++){const scratch=box(mirror,.008,1.4,.008,metal,-.75+i*.21,.2,.14);scratch.rotation.z=.12*Math.sin(i);}
 lamp(mirror,0x819e93,32,-1.1,1.8,1.5,6);
 const stairs=group('stairs');box(stairs,4.3,12,.12,plaster,0,-3,-2.7);box(stairs,.15,12,5,plaster,-2.1,-3,0);box(stairs,.15,12,5,plaster,2.1,-3,0);
 for(let i=0;i<30;i++){const a=i*Math.PI/8,x=Math.cos(a)*1.25,z=Math.sin(a)*1.25,y=1.8-i*.3;const step=box(stairs,1.1,.11,.7,wood,x,y,z);step.rotation.y=-a;const rail=box(stairs,.025,.85,.025,metal,x*1.4,y+.42,z*1.4);}
 lamp(stairs,0x8f9c77,70,0,3,2,13);lamp(stairs,0x8b8263,20,1,0,1,10);lamp(stairs,0x511c16,5,0,-5,0,8);
 const lift=group('lift');box(lift,3,.1,3.4,metal,0,-1.6,-.8);box(lift,3,.1,3.4,metal,0,1.85,-.8);box(lift,.12,3.4,3.4,metal,-1.5,.1,-.8);box(lift,.12,3.4,3.4,metal,1.5,.1,-.8);box(lift,3,3.4,.12,black,0,.1,-2.5);
 const doors=[box(lift,1.32,3.15,.08,metal,-.66,0,-1.95),box(lift,1.32,3.15,.08,metal,.66,0,-1.94)];
 for(let i=0;i<2;i++){box(doors[i],.025,3.1,.018,black,i?-.64:.64,0,.052);for(let j=0;j<7;j++)box(doors[i],.006,2.95,.012,wood,-.5+j*.16,0,.05);}
 box(lift,1.0,.22,.06,black,0,1.57,-1.8);for(let i=0;i<3;i++)box(lift,.05,.09,.025,red,-.18+i*.18,1.57,-1.75);
 box(lift,.15,1.05,.6,wood,1.4,.2,.4);for(let i=0;i<8;i++)mesh(lift,new THREE.SphereGeometry(.035,10,8),i===6?red:metal,1.31,.55-(i%4)*.21,.25+Math.floor(i/4)*.2);
 lamp(lift,0xc6b082,45,0,1.68,0,7);
 let active;
 function update(story,index,local,p,t,scareAge){
  Object.values(groups).forEach(g=>g.visible=false);
  const mode=story.scenes[index].visual_mode;
  active=['hall','door','reveal'].includes(mode)?hall:groups[mode];if(!active)throw Error('Unsupported original horror set: '+mode);
  active.visible=true;root.position.set(0,0,0);root.rotation.set(0,0,0);root.scale.setScalar(1);
  const near=scareAge>=0&&scareAge<.32;
  figure.visible=mode==='reveal'||(mode==='mirror'&&p>.55);figure.position.z=near?-5.0:-14.4;figure.rotation.y=.07*Math.sin(t*.13);
  hinge.rotation.y=mode==='door'?-.75*(.5-.5*Math.cos(p*Math.PI)):mode==='reveal'?-.9:0;
  corridorLights.forEach((l,i)=>l.intensity=(24+4*Math.sin(t*.7+i))*(mode==='reveal'&&p>.3?.35:1));doorwayLight.intensity=near?13:6;
  phoneLED.material.emissiveIntensity=1+.7*Math.sin(local*4);handset.position.z=.23+(near?.08:0);
  hands[0].rotation.z=-1.2;hands[1].rotation.z=-2.2;hands[2].rotation.z=-(Math.floor(local)*Math.PI/30);
  reflection.visible=local>1;reflection.position.x=.2+.08*Math.sin(local*.33);reflection.scale.setScalar(near?1.35:1);
  doors.forEach((d,i)=>d.position.x=(i?1:-1)*(.66+Math.max(0,p-.62)*1.8));
  const camera=mode==='door'?{position:[.05,.12,-6.0-p*.6],target:[0,.2,-14.4]}:['hall','reveal'].includes(mode)?{position:[.035*Math.sin(t*.6),.25,3.5-p*1.6],target:[0,.25,-12]}:mode==='stairs'?{position:[.8,2.6,4.4-p*.5],target:[0,-2.8,0]}:mode==='lift'?{position:[0,.2,3.4-p*.35],target:[0,.15,-2]}:{position:[.12*Math.sin(local*.15),.12,5.1-p*.5],target:[0,0,0]};
  if(near)camera.position[0]+=.035*Math.sin(scareAge*22);
  return camera;
 }
 return {root,update};
}
