import * as THREE from 'three';
const ACTIONS=new Set(["cone_pulse","parcel_compress","track_compression","frequency_compare","sensor_respond","medium_remove","boundary_reflect","energy_transfer","temperature_compare"]);
export function acousticDirector(scene,story){
 if(story.source?.url!=='https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/speed-of-sound-interactive/')throw Error('Exact verified acoustic source required');
 if(story.visual_plan?.world!=='sound_wave_lab'||story.topic_key!=='sound-waves')throw Error('Unsupported source-specific science world');
 const root=new THREE.Group();scene.add(root);const stages={};
 const mat=(color,roughness=.65)=>new THREE.MeshStandardMaterial({color,roughness,metalness:.12});
 const materials={metal:mat(0x457080,.38),dark:mat(0x142b3b),gold:mat(0xe8b765,.5),glass:new THREE.MeshPhysicalMaterial({color:0x6ab9cb,transparent:true,opacity:.13,roughness:.1,side:THREE.DoubleSide})};
 function mesh(group,geometry,material,x=0,y=0,z=0){const m=new THREE.Mesh(geometry,material);m.position.set(x,y,z);m.castShadow=true;m.receiveShadow=true;group.add(m);return m;}
 function speaker(group,x,z=0){
  mesh(group,new THREE.BoxGeometry(.65,2.8,1.8),materials.dark,x,0,z);
  const rim=mesh(group,new THREE.CylinderGeometry(.72,.72,.18,40),materials.metal,x+.4,0,z);rim.rotation.z=Math.PI/2;
  const cone=mesh(group,new THREE.ConeGeometry(.62,.4,40),materials.gold,x+.55,0,z);cone.rotation.z=-Math.PI/2;return cone;
 }
 function receiver(group,x){mesh(group,new THREE.BoxGeometry(.55,2.5,1.5),materials.dark,x,-.1);const disc=mesh(group,new THREE.CylinderGeometry(.65,.65,.08,36),materials.gold,x-.35,0);disc.rotation.z=Math.PI/2;return disc;}
 function particles(group,count=12,yOffset=0,zOffset=0){
  const dots=new THREE.InstancedMesh(new THREE.SphereGeometry(.073,10,8),mat(0x7bd5e0),count*4*3);group.add(dots);
  return {dots,count,yOffset,zOffset};
 }
 for(const action of ACTIONS){
  const group=new THREE.Group();root.add(group);
  mesh(group,new THREE.BoxGeometry(12,.28,8),materials.dark,0,-2.1,0);
  mesh(group,new THREE.BoxGeometry(12,7,.2),materials.metal,0,1,-4);
  for(let i=0;i<7;i++)mesh(group,new THREE.BoxGeometry(.05,6,.07),materials.dark,-5.4+i*1.8,1,-3.85);
  const source=speaker(group,-4);
  const target=receiver(group,4);
  let rows=[particles(group)],bell=null,wall=null,paired=null;
  if(action==='frequency_compare'||action==='temperature_compare'){
   source.visible=false;target.visible=false;rows[0].dots.visible=false;
   paired=[speaker(group,-4,-1.5),speaker(group,-4,1.5)];
   rows=[particles(group,12,0,-1.5),particles(group,12,0,1.5)];
  }
  if(action==='medium_remove'){
   rows[0].dots.visible=false;
   bell=mesh(group,new THREE.CylinderGeometry(4.8,4.8,4,56,1,true),materials.glass,0,0,0);
   mesh(group,new THREE.CylinderGeometry(4.8,4.8,.12,56),materials.metal,0,-2);
   target.material=mat(0x647078);
  }
  if(action==='boundary_reflect'){target.visible=false;wall=mesh(group,new THREE.BoxGeometry(.24,3.5,4),materials.metal,3.5,0);}
  if(action==='cone_pulse'){rows[0].dots.visible=false;target.visible=false;}
  stages[action]={group,source,target,rows,bell,wall,paired};
 }
 const dummy=new THREE.Object3D();
 function update(index,p,t){
  const row=story.visual_plan.scenes[index];
  if(!row||!ACTIONS.has(row.action))throw Error('Unimplemented acoustic event');
  for(const [name,stage] of Object.entries(stages))stage.group.visible=name===row.action;
  const s=stages[row.action],phase=t*3;
  s.source.position.x=-3.45+.10*Math.sin(phase);
  s.target.position.x=3.65+(row.action==='sensor_respond'?.10*Math.sin(phase-7):0);
  s.paired?.forEach((m,i)=>m.position.x=-3.45+.10*Math.sin(phase*(row.action==='temperature_compare'?1:i+1)));
  s.rows.forEach((line,lineIndex)=>{
   if(!line.dots.visible)return;
   let n=0;
   const k=row.action==='frequency_compare'?1.5*(lineIndex+1):row.action==='temperature_compare'?1.7/(lineIndex+1):1.7;
   for(let i=0;i<line.count;i++)for(let j=0;j<4;j++)for(let z=0;z<3;z++){
    const base=-3+i*6/(line.count-1),wave=k*base-phase;
    let displacement=.16*Math.sin(wave);
    if(row.action==='boundary_reflect')displacement+=.16*Math.sin(k*(7-base)-phase);
    dummy.position.set(base+displacement,-.85+j*.55+line.yOffset,-.5+z*.5+line.zOffset);
    dummy.scale.setScalar(row.action==='track_compression'?1+.18*Math.cos(wave):1);
    dummy.updateMatrix();line.dots.setMatrixAt(n++,dummy.matrix);
   }
   line.dots.instanceMatrix.needsUpdate=true;
  });
  let position=[1.5,2,15],target=[0,0,0];
  if(row.shot==='driver_close'){position=[-1.8,1.3,7];target=[-3.5,0,0];}
  if(row.shot==='section_macro'){position=[0,1,8.5];target=[0,0,0];}
  if(row.shot==='wave_track'){position=[-2+4*p,1.3,11];target=[-2+4*p,0,0];}
  if(row.shot==='receiver_close'){position=[2,1.2,7];target=[3.4,0,0];}
  if(row.shot==='boundary_side'){position=[-4,2,11];target=[2,0,0];}
  if(row.shot==='pullback')position=[0,2,11+5*p];
  return {position,target,world:'sound_wave_lab',action:row.action,setting:row.setting,qualitative:true,particle_transport:false};
 }
 return {root,stages,update};
}
