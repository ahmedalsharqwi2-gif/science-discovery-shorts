/** Qualitative NASA magnetosphere explainer; geometry is explicitly not to scale.
 * No field measurements, orbital elements or spacecraft paths are invented.
 */
import * as THREE from 'three';
export const MMS_SPACECRAFT_COUNT=4;

export function scienceField(scene){
 const root=new THREE.Group();root.name='science-magnetosphere-v2';scene.add(root);
 const group=()=>{const g=new THREE.Group();root.add(g);return g;};
 const earthStage=group(),comparison=group(),reconnection=group(),mission=group();
 const all=[earthStage,comparison,reconnection,mission];
 const metal=new THREE.MeshStandardMaterial({color:0xadb9c5,roughness:.35,metalness:.65});
 const blue=new THREE.MeshPhysicalMaterial({color:0x205a88,roughness:.55,metalness:.06,clearcoat:.12});
 const lineMaterial=new THREE.MeshBasicMaterial({color:0x68d3d2,transparent:true,opacity:.65});
 const mesh=(parent,geometry,material,x=0,y=0,z=0)=>{const m=new THREE.Mesh(geometry,material);m.position.set(x,y,z);parent.add(m);return m;};
 const globe=(parent,radius=0.72)=>{
  const g=new THREE.Group();parent.add(g);
  mesh(g,new THREE.SphereGeometry(radius,48,32),blue);
  const grid=new THREE.Mesh(new THREE.SphereGeometry(radius*1.006,24,12),new THREE.MeshBasicMaterial({color:0x85c4df,wireframe:true,transparent:true,opacity:.12}));g.add(grid);
  mesh(g,new THREE.SphereGeometry(radius*1.065,40,24),new THREE.MeshBasicMaterial({color:0x5a99ba,transparent:true,opacity:.08,side:THREE.BackSide,depthWrite:false}));
  return g;
 };
 const earth=globe(earthStage);
 const curves=[];
 for(let longitude=0;longitude<12;longitude++){
  const phi=longitude/12*Math.PI*2,points=[];
  // Analytic dipole form r = L sin²(theta), qualitatively illustrating loops.
  for(let k=0;k<=48;k++){
   const theta=.40+k/48*(Math.PI-.80),r=2.05*Math.sin(theta)**2;
   points.push(new THREE.Vector3(r*Math.sin(theta)*Math.cos(phi),r*Math.cos(theta),r*Math.sin(theta)*Math.sin(phi)));
  }
  const curve=new THREE.CatmullRomCurve3(points);curves.push(curve);
  mesh(earthStage,new THREE.TubeGeometry(curve,48,.009,5,false),lineMaterial);
 }
 const pulses=curves.map((curve,i)=>mesh(earthStage,new THREE.SphereGeometry(.025,8,6),new THREE.MeshBasicMaterial({color:0xc4f7e2})));
 const wind=[];const windMaterial=new THREE.MeshBasicMaterial({color:0xefbc73,transparent:true,opacity:.65});
 for(let i=0;i<24;i++)wind.push(mesh(earthStage,new THREE.SphereGeometry(.025,8,6),windMaterial));
 const earthComparison=globe(comparison,.65);earthComparison.position.x=-1.45;
 const mars=mesh(comparison,new THREE.SphereGeometry(.45,40,24),new THREE.MeshStandardMaterial({color:0xa66a4b,roughness:.95}),1.3);
 const earthHalo=mesh(comparison,new THREE.SphereGeometry(.88,32,24),new THREE.MeshBasicMaterial({color:0x66b9db,wireframe:true,transparent:true,opacity:.12}),-1.45);
 const reconnectGroups=[];
 for(const side of [-1,1]){
  const g=new THREE.Group();reconnection.add(g);reconnectGroups.push(g);
  for(let n=0;n<5;n++){
   const x=side*(.15+n*.18);
   const curve=new THREE.CatmullRomCurve3([new THREE.Vector3(x+side*.8,-1.4,0),new THREE.Vector3(x,-.5,.1),new THREE.Vector3(x,.5,.1),new THREE.Vector3(x+side*.8,1.4,0)]);
   mesh(g,new THREE.TubeGeometry(curve,40,.012,5,false),side<0?lineMaterial:new THREE.MeshBasicMaterial({color:0xe7b882}));
  }
 }
 const energy=mesh(reconnection,new THREE.SphereGeometry(.12,20,12),new THREE.MeshBasicMaterial({color:0xcff8e8,transparent:true,opacity:.65}));
 const earthMission=globe(mission,.52);earthMission.position.set(-1.4,-.1,-.4);
 const spacecraft=[];
 const vertices=[[-.48,-.32,.32],[.48,-.32,.32],[0,.5,.32],[0,0,-.48]];
 for(let i=0;i<MMS_SPACECRAFT_COUNT;i++){
  const craft=new THREE.Group();mission.add(craft);craft.name='MMS-'+(i+1);craft.position.set(1+vertices[i][0],vertices[i][1],vertices[i][2]);spacecraft.push(craft);
  mesh(craft,new THREE.CylinderGeometry(.1,.1,.08,8),metal);
  for(let arm=0;arm<4;arm++){
   const a=arm*Math.PI/2;
   const boom=mesh(craft,new THREE.CylinderGeometry(.004,.004,.34,5),metal,Math.cos(a)*.22,0,Math.sin(a)*.22);
   boom.rotation.z=Math.PI/2;boom.rotation.y=-a;
  }
 }
 // A light tetrahedral guide makes the exact four-vehicle formation legible.
 const linkPositions=[];
 for(let a=0;a<4;a++)for(let b=a+1;b<4;b++)linkPositions.push(...spacecraft[a].position.toArray(),...spacecraft[b].position.toArray());
 const links=new THREE.BufferGeometry();links.setAttribute('position',new THREE.Float32BufferAttribute(linkPositions,3));mission.add(new THREE.LineSegments(links,new THREE.LineBasicMaterial({color:0x7096a9,transparent:true,opacity:.3})));
 return {
  root,
  update(index,progress,time){
   all.forEach(g=>g.visible=false);
   const current=index===2?comparison:index===5?reconnection:index===6?mission:earthStage;current.visible=true;
   root.position.y=-.25;root.rotation.y=.12*Math.sin(time*.075);
   earth.rotation.y=time*.06;earthComparison.rotation.y=time*.05;earthMission.rotation.y=time*.05;mars.rotation.y=time*.04;
   earthHalo.rotation.y=time*.035;
   pulses.forEach((p,i)=>{p.position.copy(curves[i].getPoint((time*.075+i/12)%1));p.visible=index===0||index===4||index===7;});
   wind.forEach((p,i)=>{const q=(time*.16+i/24)%1;const height=(i%6-2.5)*.36;const deflect=Math.sin(q*Math.PI);p.position.set(3.3-q*6.6,height+Math.sign(height||1)*deflect*1.65,Math.sin(i)*.25);p.visible=index===1||index===3||index===4;});
   reconnectGroups.forEach((g,i)=>g.position.x=(i===0?-1:1)*(.22+.12*Math.cos(progress*Math.PI*2)));
   energy.scale.setScalar(.6+.4*Math.sin(progress*Math.PI)**2);
   spacecraft.forEach((g,i)=>{g.rotation.y=time*.12+i;});
   return {mode:current===comparison?'earth-mars-comparison':current===mission?'four-spacecraft-formation':current===reconnection?'qualitative-reconnection':'dipole-and-solar-wind',spacecraft:current===mission?MMS_SPACECRAFT_COUNT:0,notToScale:true};
  }
 };
}
