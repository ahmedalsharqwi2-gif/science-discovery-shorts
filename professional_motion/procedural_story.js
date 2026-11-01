/** Bounded declarative 3D story scenes. No generated JavaScript is executed. */
import * as THREE from 'three';
const ASSETS=new Set(['cell','leaf','heart','dna','molecule','crystal','rock_layers','volcano','tree','pendulum','gear','magnet','circuit','river','fossil','scroll','book','temple','house','ship','cart','person','stickman','door','clock','lantern','table','sphere','box','cylinder','cone','torus','server','monitor','robot','satellite_dish','microphone','phone','chip','document','shield','network','waveform']);
const MOTIONS=new Set(['none','spin','pulse','drift','orbit','grow','assemble','split','swing','flow','slam','open','close','shake','float','backward','head_turn']);
function material(color,extra={}){return new THREE.MeshStandardMaterial({color,roughness:.58,metalness:.08,...extra});}
function mesh(parent,geometry,mat,x=0,y=0,z=0){const o=new THREE.Mesh(geometry,mat);o.position.set(x,y,z);o.castShadow=true;o.receiveShadow=true;parent.add(o);return o;}
function rod(parent,a,b,r,mat){const start=new THREE.Vector3(...a),end=new THREE.Vector3(...b),delta=end.clone().sub(start);const o=mesh(parent,new THREE.CylinderGeometry(r,r,delta.length(),10),mat);o.position.copy(start).add(end).multiplyScalar(.5);o.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),delta.normalize());return o;}
function shape(kind,color){
 const g=new THREE.Group(),m=material(color),dark=material(0x263644),light=material(0xdce7df),parts=[];
 const ball=(r,x=0,y=0,z=0,mat=m)=>mesh(g,new THREE.SphereGeometry(r,24,16),mat,x,y,z);
 const box=(x,y,z,px=0,py=0,pz=0,mat=m)=>mesh(g,new THREE.BoxGeometry(x,y,z),mat,px,py,pz);
 const tube=(r,h,x=0,y=0,z=0,mat=m)=>mesh(g,new THREE.CylinderGeometry(r,r,h,24),mat,x,y,z);
 if(kind==='sphere')ball(1);
 else if(kind==='box')box(1.8,1.8,1.8);
 else if(kind==='cylinder')tube(.8,1.8);
 else if(kind==='cone')mesh(g,new THREE.ConeGeometry(1,2,40),m);
 else if(kind==='torus')mesh(g,new THREE.TorusGeometry(.8,.2,12,40),m);
 else if(kind==='server'){
  box(1.5,3,1,0,0,0,dark);
  for(let i=0;i<6;i++){box(1.3,.3,.08,0,-1.15+i*.45,.55,m);for(let j=0;j<3;j++)ball(.035,.25+j*.16,-1.15+i*.45,.61,material(0x82d6b4));}
 }else if(kind==='monitor'||kind==='phone'){
  const phone=kind==='phone';box(phone?.8:2.6,phone?1.6:1.7,.15,0,.2,0,dark);box(phone?.66:2.35,phone?1.36:1.45,.03,0,.2,.1,m);
  if(!phone){tube(.08,.7,0,-.95);box(1,.1,.6,0,-1.3);}
  for(let i=0;i<4;i++)box(phone?.45:1.7,.035,.02,0,.65-i*.28,.14,light);
 }else if(kind==='robot'){
  box(.8,.9,.5,0,.1);box(.6,.5,.5,0,.9,0,dark);ball(.05,-.15,.93,.27,material(0x84dfdf));ball(.05,.15,.93,.27,material(0x84dfdf));
  for(const side of [-1,1]){rod(g,[side*.4,.5,0],[side*.8,-.1,.1],.09,m);rod(g,[side*.8,-.1,.1],[side*.55,-.6,.25],.08,light);rod(g,[side*.2,-.3,0],[side*.3,-1.2,0],.13,dark);}
 }else if(kind==='satellite_dish'){
  tube(.12,1.7,0,-.6,0,dark);box(1.8,.12,1.6,0,-1.5,0,dark);
  const points=[];for(let i=0;i<=24;i++){const r=i/24*1.25;points.push(new THREE.Vector2(r,r*r*.48));}
  const dish=mesh(g,new THREE.LatheGeometry(points,48),material(color,{side:THREE.DoubleSide}),0,.1,0);dish.rotation.z=.35;
  rod(g,[0,.1,0],[0,1.4,0],.035,dark);ball(.12,0,1.4,0,light);
 }else if(kind==='microphone'){
  tube(.24,.8,0,.45,0,m);ball(.24,0,.85,0,dark);tube(.05,1,0,-.5,0,dark);tube(.5,.08,0,-1,0,dark);
 }else if(kind==='chip'){
  box(1.6,.25,1.6,0,0,0,dark);box(1,.08,1,0,.18,0,m);
  for(let i=0;i<7;i++)for(const side of [-1,1]){box(.1,.08,.3,-.65+i*.22,0,side*.9,light);box(.3,.08,.1,side*.9,0,-.65+i*.22,light);}
 }else if(kind==='document'){
  box(1.6,2.1,.08,0,0,0,light);for(let i=0;i<7;i++)box(1.1,.035,.02,0,.7-i*.22,.06,m);
 }else if(kind==='shield'){
  const s=new THREE.Shape();s.moveTo(0,-1.3);s.lineTo(-1,.1);s.lineTo(-1,1);s.lineTo(0,1.25);s.lineTo(1,1);s.lineTo(1,.1);s.closePath();
  mesh(g,new THREE.ExtrudeGeometry(s,{depth:.14,bevelEnabled:true,bevelSize:.04,bevelThickness:.04,bevelSegments:2}),m);
 }else if(kind==='network'){
  ball(.3,0,0,0,m);
  for(let i=0;i<8;i++){const a=i/8*Math.PI*2,p=[Math.cos(a)*1.4,Math.sin(a)*1.2,Math.sin(i*2)*.5];ball(.16,...p,i%2?m:light);rod(g,[0,0,0],p,.025,dark);}
 }else if(kind==='waveform'){
  const points=[];for(let i=0;i<80;i++)points.push(new THREE.Vector3(-2+i/20,Math.sin(i*.32)*.65,0));
  mesh(g,new THREE.TubeGeometry(new THREE.CatmullRomCurve3(points),100,.045,8,false),m);
 }else if(kind==='cell'){
  ball(1.35,0,0,0,material(color,{transparent:true,opacity:.3,side:THREE.DoubleSide}));
  ball(.43,-.2,.1,.2,material(0x9568ad));ball(.16,-.15,.18,.55,material(0xd9acd6));
  for(let i=0;i<11;i++){const o=ball(.13,Math.sin(i*2.4)*.8,Math.cos(i*3.1)*.8,Math.sin(i*4.3)*.7,material(i%2?0xe8ad64:0x70b8a3));o.scale.set(1.7,.65,1);parts.push(o);}
  for(let i=0;i<20;i++)ball(.07,1.34*Math.cos(i/20*Math.PI*2),1.34*Math.sin(i/20*Math.PI*2),0,material(0x89c6b1));
 }else if(kind==='leaf'){
  const s=new THREE.Shape();s.moveTo(0,-1.4);s.bezierCurveTo(-1.7,-.5,-1.2,1.1,0,1.65);s.bezierCurveTo(1.2,1.1,1.7,-.5,0,-1.4);
  mesh(g,new THREE.ExtrudeGeometry(s,{depth:.07,bevelEnabled:true,bevelSize:.03,bevelThickness:.03,bevelSegments:2,steps:1}),m);
  rod(g,[0,-1.65,.15],[0,1.25,.15],.035,material(0xaccf79));
  for(let i=0;i<5;i++)for(const side of [-1,1])rod(g,[0,-.9+i*.42,.16],[side*(.75-Math.abs(i-2)*.12),-.5+i*.4,.17],.018,material(0xa4c770));
 }else if(kind==='heart'){
  const s=new THREE.Shape();s.moveTo(0,-1.3);s.bezierCurveTo(-2,.1,-1.5,1.5,-.5,1.1);s.bezierCurveTo(-.15,1.05,0,.7,0,.65);s.bezierCurveTo(.5,1.55,1.8,1.1,1.4,.1);s.bezierCurveTo(1.1,-.6,.4,-1.1,0,-1.3);
  mesh(g,new THREE.ExtrudeGeometry(s,{depth:.5,bevelEnabled:true,bevelSize:.12,bevelThickness:.15,bevelSegments:4}),m);
  tube(.13,1,0,1.2,.2,material(0xc9444a));tube(.12,.8,.4,1.05,.1,material(0x5d8cb3));
 }else if(kind==='dna'){
  const blue=material(0x5ebbd1),gold=material(0xe1b776);
  for(let i=0;i<20;i++){const a=i*.55,y=-2+i*.21,p=[Math.cos(a)*.65,y,Math.sin(a)*.65],q=[-p[0],y,-p[2]];ball(.12,...p,blue);ball(.12,...q,gold);rod(g,p,q,.045,i%2?blue:gold);}
 }else if(kind==='molecule'){
  const atoms=[[0,0,0],[1,0,0],[-.6,.8,.4],[-.5,-.7,.6],[.2,.8,-.8]];
  atoms.forEach((p,i)=>{ball(i?.32:.45,...p,material(i%2?0x7daacb:color));if(i)rod(g,atoms[0],p,.075,light);});
 }else if(kind==='crystal'){
  for(let i=0;i<5;i++){const o=mesh(g,new THREE.CylinderGeometry(.15,.38,1+i%3*.4,6),material(color,{metalness:.28,roughness:.25}),Math.sin(i*2.4)*.55,-.2,Math.cos(i*2.4)*.45);o.rotation.z=(i-2)*.16;}
 }else if(kind==='rock_layers'||kind==='fossil'){
  for(let i=0;i<5;i++)box(3,.32,1.7,0,-.8+i*.33,0,material([0x5b4534,0x92704d,0xb69768,0xd1ba8f,0x867c5b][i]));
  if(kind==='fossil'){for(let i=0;i<8;i++){const a=i*.7;ball(.1,Math.cos(a)*i*.08,.85,Math.sin(a)*i*.08,material(0xe9d6a5));}}
 }else if(kind==='volcano'){
  mesh(g,new THREE.CylinderGeometry(.35,1.8,2.2,40),m,0,-.2);mesh(g,new THREE.CylinderGeometry(.28,.28,.03,32),material(0xef793b,{emissive:0xb83511,emissiveIntensity:.8}),0,.91);
  for(let i=0;i<6;i++){const o=ball(.13,Math.sin(i*2)*.3,1.3+i*.25,Math.cos(i*2)*.3,material(0xd8d4c3,{transparent:true,opacity:.45}));parts.push(o);}
 }else if(kind==='tree'){
  tube(.13,1.7,0,-.6);for(let i=0;i<5;i++)ball(.65,Math.sin(i*2)*.5,.45+(i%2)*.5,Math.cos(i*2)*.4,material(0x4f9366));
 }else if(kind==='pendulum'){
  box(2.7,.14,.7,0,1.6,0,dark);tube(.07,3,-1.2,0,0,dark);tube(.07,3,1.2,0,0,dark);
  const arm=new THREE.Group();arm.position.y=1.5;g.add(arm);rod(arm,[0,0,0],[0,-2.2,0],.027,light);mesh(arm,new THREE.SphereGeometry(.28,24,16),m,0,-2.2);g.userData.swingPart=arm;
 }else if(kind==='gear'){
  tube(.8,.35).rotation.x=Math.PI/2;
  for(let i=0;i<14;i++){const a=i/14*Math.PI*2;const o=box(.28,.35,.35,.85*Math.sin(a),.85*Math.cos(a),0);o.rotation.z=-a;}
  tube(.22,.45,0,0,0,dark).rotation.x=Math.PI/2;
 }else if(kind==='magnet'){
  mesh(g,new THREE.TorusGeometry(.7,.22,12,32,Math.PI),m).rotation.z=Math.PI;
  box(.44,.8,.44,-.7,.4,0,material(0xc45253));box(.44,.8,.44,.7,.4,0,material(0x4e86bf));
 }else if(kind==='circuit'){
  box(3,.13,2,0,-.2,0,material(0x3d7d67));
  const points=[[-1,-.05,-.6],[1,-.05,-.6],[1,-.05,.6],[-1,-.05,.6],[-1,-.05,-.6]];
  for(let i=1;i<points.length;i++)rod(g,points[i-1],points[i],.045,material(0xdfbb6a));
  box(.7,.2,.5,0,0,-.6,dark);g.userData.flowDot=ball(.1,-1,.12,-.6,material(0xffe094,{emissive:0xe7b24d,emissiveIntensity:.6}));
 }else if(kind==='river'){
  box(4,.16,2.7,0,-.5,0,material(0x7b9566));
  const points=[];for(let i=0;i<16;i++)points.push(new THREE.Vector3(-1.8+i*.24,-.35,Math.sin(i*.5)*.5));
  mesh(g,new THREE.TubeGeometry(new THREE.CatmullRomCurve3(points),50,.18,10,false),material(0x4cacc9,{roughness:.2}));
 }else if(kind==='scroll'||kind==='book'){
  box(1.8,2.3,.13,0,0,0,material(kind==='scroll'?0xdcc89b:color));
  if(kind==='scroll'){tube(.16,1.9,0,-1.1,0,light).rotation.z=Math.PI/2;tube(.16,1.9,0,1.1,0,light).rotation.z=Math.PI/2;}
  else box(1.65,2.15,.17,.04,0,.1,light);
  for(let i=0;i<7;i++)box(1.15,.025,.02,0,.7-i*.23,.21,material(0x927c61));
 }else if(kind==='temple'){
  box(3,.18,2,0,-1.1);
  for(const x of [-1.15,-.38,.38,1.15]){tube(.13,1.8,x,-.1,.55);box(.4,.12,.4,x,.86,.55);}
  const roof=mesh(g,new THREE.ConeGeometry(2,.9,4),m,0,1.2,0);roof.rotation.y=Math.PI/4;roof.scale.z=.65;
 }else if(kind==='house'){
  box(2,1.7,1.7,0,-.15);const roof=mesh(g,new THREE.ConeGeometry(1.6,1,4),material(0x986347),0,1.2);roof.rotation.y=Math.PI/4;box(.45,.9,.05,.4,-.5,.88,dark);
 }else if(kind==='ship'){
  const hull=mesh(g,new THREE.SphereGeometry(1.2,32,16),m,0,-.5);hull.scale.set(2,.4,.65);
  tube(.045,2.8,0,.7,0,dark);const sail=mesh(g,new THREE.PlaneGeometry(1.6,1.7),light,.4,1,.03);sail.rotation.y=-.15;
  box(2.8,.08,1,0,-.2,0,material(0xa88559));
 }else if(kind==='cart'){
  box(1.8,.8,1.2,0,0);
  for(const x of [-.65,.65])for(const z of [-.7,.7])mesh(g,new THREE.TorusGeometry(.4,.09,8,24),dark,x,-.6,z);
  rod(g,[.8,-.25,0],[1.9,-.25,0],.07,m);
 }else if(kind==='person'||kind==='stickman'){
  ball(.26,0,1.15,0,light);rod(g,[0,.85,0],[0,-.1,0],.09,m);
  const armL=rod(g,[0,.65,0],[-.55,.1,0],.065,m),armR=rod(g,[0,.65,0],[.55,.1,0],.065,m);
  rod(g,[0,-.1,0],[-.35,-1.1,0],.075,m);rod(g,[0,-.1,0],[.35,-1.1,0],.075,m);g.userData.arms=[armL,armR];
 }else if(kind==='door'){
  box(.16,3.2,.3,-.9);box(.16,3.2,.3,.9);box(2,.16,.3,0,1.6);
  const hinge=new THREE.Group();hinge.position.set(-.8,0,0);g.add(hinge);
  mesh(hinge,new THREE.BoxGeometry(1.6,3,.13),m,.8);mesh(hinge,new THREE.SphereGeometry(.08,12,8),material(0xdfbd72),1.4,0,.15);g.userData.swingPart=hinge;
 }else if(kind==='clock'){
  tube(1,.18).rotation.x=Math.PI/2;
  for(let i=0;i<12;i++){const a=i/12*Math.PI*2;ball(.04,Math.sin(a)*.8,Math.cos(a)*.8,.13,light);}
  const hand=new THREE.Group();g.add(hand);rod(hand,[0,0,.18],[.45,.25,.18],.035,dark);rod(hand,[0,0,.18],[0,.65,.18],.025,dark);g.userData.clockHands=hand;
 }else if(kind==='lantern'){
  tube(.35,.1,0,-.4,0,dark);tube(.35,.1,0,.4,0,dark);
  ball(.22,0,0,0,material(0xffc56b,{emissive:0xffaf43,emissiveIntensity:1}));
  for(const x of [-.3,.3])for(const z of [-.3,.3])rod(g,[x,-.4,z],[x,.4,z],.025,dark);
 }else if(kind==='table'){
  box(2.5,.15,1.6,0,.6);for(const x of [-1,1])for(const z of [-.6,.6])box(.12,1.6,.12,x,-.2,z);
 }else throw Error('Unsupported declarative asset');
 g.userData.parts=parts;return g;
}
function environment(group,name){
 const indoors=['laboratory','body_section','workshop','dark_interior'].includes(name),night=['dark_interior','forest','ocean'].includes(name);
 const ground=material(name==='ocean'?0x234f70:name==='landscape'||name==='forest'?0x537452:indoors?0x274858:0x8b7356);
 mesh(group,new THREE.BoxGeometry(24,.2,22),ground,0,-3,0);
 if(indoors){
  mesh(group,new THREE.BoxGeometry(24,12,.2),material(night?0x19303d:0x527a87),0,2,-7);
  for(let i=0;i<7;i++)mesh(group,new THREE.BoxGeometry(.08,10,.12),material(0x1b3948),-9+i*3,1,-6.8);
  mesh(group,new THREE.BoxGeometry(10,.18,4),material(0x486372),0,-2.5,-.2);
 }else{
  for(let i=0;i<8;i++){const hill=mesh(group,new THREE.ConeGeometry(2+(i%3),3+(i%2),6),material(night?0x183b3f:0x7b8f70),-10+i*3,-1.5,-7-(i%2));hill.rotation.y=i*.7;}
 }
}
export function proceduralDirector(scene,story){
 if(story.visual_plan?.world!=='procedural_story'||story.scenes?.length!==8)throw Error('An authored declarative eight-scene plan is required');
 const root=new THREE.Group();scene.add(root);
 const stages=story.scenes.map(s=>{
  if(!Array.isArray(s.objects)||s.objects.length<1||s.objects.length>16)throw Error('Invalid object count');
  const group=new THREE.Group();root.add(group);environment(group,s.environment);
  const objects=s.objects.map(spec=>{
   if(!ASSETS.has(spec.kind)||!MOTIONS.has(spec.motion)||!/^#[0-9a-fA-F]{6}$/.test(spec.color))throw Error('Unimplemented object or motion');
   for(const key of ['position','scale','rotation'])if(!Array.isArray(spec[key])||spec[key].length!==3||!spec[key].every(Number.isFinite))throw Error('Invalid transform');
   const object=shape(spec.kind,spec.color);object.position.set(...spec.position);object.scale.set(...spec.scale);object.rotation.set(...spec.rotation);group.add(object);return {object,spec};
  });return {group,objects,definition:s};
 });
 function update(index,p,t){
  stages.forEach((s,i)=>s.group.visible=i===index);const stage=stages[index],q=p*p*(3-2*p);
  stage.objects.forEach(({object:o,spec:s},i)=>{
   o.position.set(...s.position);o.scale.set(...s.scale);o.rotation.set(...s.rotation);
   const phase=t*1.5+i*.8;
   if(s.motion==='spin')o.rotation.y+=q*Math.PI*1.4;
   if(s.motion==='backward'){if(o.userData.clockHands)o.userData.clockHands.rotation.z=t*3;else o.rotation.z+=q*Math.PI*2;}
   if(s.motion==='open'||s.motion==='close'||s.motion==='slam'){const part=o.userData.swingPart||o;part.rotation.y=(s.motion==='open'?q:1-Math.min(1,p*5))*1.3;}
   if(s.motion==='shake'){o.rotation.z+=Math.sin(t*15)*.045;o.position.x+=Math.sin(t*12)*.04;}
   if(s.motion==='float')o.position.y+=Math.sin(t*.8+i)*.25;
   if(s.motion==='head_turn')o.rotation.y+=q*1.3;
   if(s.motion==='pulse')o.scale.multiplyScalar(1+.06*Math.sin(phase*2));
   if(s.motion==='drift')o.position.x+=(q-.5)*1.4;
   if(s.motion==='orbit'){o.position.x+=Math.cos(phase)*.55;o.position.z+=Math.sin(phase)*.55;}
   if(s.motion==='grow')o.scale.multiplyScalar(.25+.75*q);
   if(s.motion==='assemble'){o.position.y+=(1-q)*(1+i%3)*.7;o.rotation.y+=(1-q)*.8;}
   if(s.motion==='split')o.position.x+=(i%2?1:-1)*q*.85;
   if(s.motion==='swing'){const part=o.userData.swingPart||o;part.rotation.z=s.kind==='door'?0:Math.sin(phase)*.55;if(s.kind==='door')part.rotation.y=q*1.25;}
   if(s.motion==='flow'){
    if(o.userData.flowDot){const dot=o.userData.flowDot,x=(t*.5)%4;dot.position.set(x<1?-1+2*x:x<2?1:x<3?1-2*(x-2):-1,.12,x<1?-.6:x<2?-.6+1.2*(x-1):x<3?.6:.6-1.2*(x-3));}
    else o.position.x+=((t*.3+i*.2)%1-.5)*.65;
   }
   o.userData.arms?.forEach((arm,j)=>arm.rotation.z=Math.sin(phase+j*Math.PI)*.18);
  });
  const s=stage.definition,pos=s.camera_start.map((v,i)=>v+(s.camera_end[i]-v)*q);
  return {position:pos,target:[0,0,0],world:'procedural_story',environment:s.environment,objects:stage.objects.map(o=>o.spec.kind),actions:stage.objects.map(o=>o.spec.motion)};
 }
 return {root,stages,update};
}
