import * as THREE from 'three';
const TAU=Math.PI*2;
export function channelStage(scene){
 const root=new THREE.Group();scene.add(root);
 const groups={};
 const mat=(color,roughness=.4,metalness=.15)=>new THREE.MeshStandardMaterial({color,roughness,metalness});
 const brass=mat(0xad7944,.32,.5),stone=mat(0xb6a58c,.8,.02),iceMat=mat(0x97d5e3,.25,.1),blue=mat(0x243d51,.35,.4),copper=mat(0xb57540,.3,.6);
 const emit=c=>new THREE.MeshStandardMaterial({color:c,emissive:c,emissiveIntensity:1.2,roughness:.3});
 const aqua=emit(0x49d3c7),violet=emit(0x9975ee);
 const group=name=>{const g=new THREE.Group();root.add(g);groups[name]=g;return g;};
 const mesh=(g,geo,m,x=0,y=0,z=0)=>{let o=new THREE.Mesh(geo,m);o.position.set(x,y,z);g.add(o);return o;};
 const box=(g,x,y,z,m,px=0,py=0,pz=0)=>mesh(g,new THREE.BoxGeometry(x,y,z),m,px,py,pz);
 function curve(g,points,m,r=.018){const c=new THREE.CatmullRomCurve3(points.map(p=>new THREE.Vector3(...p)));const o=mesh(g,new THREE.TubeGeometry(c,48,r,7,false),m);return {curve:c,mesh:o};}
 function ship(g,scale=1){
  const s=new THREE.Group();g.add(s);s.scale.setScalar(scale);
  const hull=new THREE.Shape();hull.moveTo(-1.8,.1);hull.lineTo(-1.35,-.6);hull.lineTo(1.2,-.6);hull.lineTo(1.95,.2);hull.lineTo(-1.8,.1);
  const h=mesh(s,new THREE.ExtrudeGeometry(hull,{depth:.78,bevelEnabled:true,bevelSegments:2,steps:1,bevelSize:.04,bevelThickness:.04}),mat(0x594031,.7,.05));h.position.z=-.39;
  box(s,3.3,.12,.8,brass,0,.1,0);
  const sails=[];
  for(let i=0;i<3;i++){
   const x=-1+i*.96;mesh(s,new THREE.CylinderGeometry(.025,.035,2.25,10),brass,x,1.12,0);
   for(let j=0;j<2;j++){
    const sail=mesh(s,new THREE.PlaneGeometry(.75,.7,12,10),new THREE.MeshStandardMaterial({color:0xc6c3a8,side:THREE.DoubleSide,roughness:.85}),x,.7+j*.85,.03);sails.push(sail);
    const bar=mesh(s,new THREE.CylinderGeometry(.018,.018,.86,8),brass,x,1.08+j*.85,.02);bar.rotation.z=Math.PI/2;
   }
   curve(s,[[x,2.25,0],[x-.55,.1,.38]],brass,.008);curve(s,[[x,2.25,0],[x+.55,.1,-.38]],brass,.008);
  }
  s.userData.sails=sails;return s;
 }
 const fleet=group('fleet');const ships=[ship(fleet,.85),ship(fleet,.62)];ships[0].position.set(-.7,-.2,.1);ships[1].position.set(1.45,.1,-2.1);
 const ocean=mesh(fleet,new THREE.PlaneGeometry(20,18,45,45),new THREE.MeshStandardMaterial({color:0x082c3f,roughness:.27,metalness:.3,transparent:true,opacity:.8}),0,-.85,-2);ocean.rotation.x=-Math.PI/2;
 const ice=[];
 for(let i=0;i<30;i++){const o=mesh(fleet,new THREE.DodecahedronGeometry(.3+(i%5)*.12,0),iceMat,Math.sin(i*14.3)*5,-.68,Math.cos(i*8.7)*5-2);o.scale.set(1,.18,1);o.rotation.y=i;ice.push(o);}
 const globe=group('globe');mesh(globe,new THREE.SphereGeometry(2,48,32),mat(0x113247,.5,.2));
 mesh(globe,new THREE.SphereGeometry(2.015,24,16),new THREE.MeshBasicMaterial({color:0x3d8e98,wireframe:true,transparent:true,opacity:.25}));
 const route=curve(globe,[[-1,1.65,1],[0,2.3,.2],[1.2,1.6,-.5]],brass,.028);const routePoint=mesh(globe,new THREE.SphereGeometry(.08,16,12),aqua);
 const wreck=group('wreck');const wreckShip=ship(wreck,1.0);wreckShip.rotation.set(.1,0,-.22);wreckShip.position.y=-.8;
 mesh(wreck,new THREE.CircleGeometry(5,64),mat(0x122b30,.9),0,-1.55,0).rotation.x=-Math.PI/2;
 const scanRings=[];for(let i=0;i<4;i++){let o=mesh(wreck,new THREE.TorusGeometry(.65+i*.6,.012,6,100),aqua,0,0,.9);scanRings.push(o);}
 // Architecture: actual authored geometry, not a photographic placeholder.
 const building=group('building');const columns=[];const arches=[];
 box(building,4.8,.3,3.4,stone,0,-1.5,0);
 const cylinder=mesh(building,new THREE.CylinderGeometry(1.65,1.65,1.7,64,1,true),stone,.3,-.5,-.3);
 const dome=mesh(building,new THREE.SphereGeometry(1.68,64,32,0,TAU,.13,Math.PI/2-.13),stone,.3,.35,-.3);dome.scale.y=.72;
 const oculus=mesh(building,new THREE.TorusGeometry(.225,.025,10,64),brass,.3,1.55,-.3);oculus.rotation.x=Math.PI/2;
 for(let i=0;i<8;i++){let x=-1.75+(i%4)*.85,z=1.0+Math.floor(i/4)*.7;let c=mesh(building,new THREE.CylinderGeometry(.11,.14,2.0,16),stone,x,-.35,z);columns.push(c);mesh(building,new THREE.CylinderGeometry(.19,.19,.12,16),stone,x,.68,z);}
 const pediment=new THREE.Shape();pediment.moveTo(-2.1,0);pediment.lineTo(0,.65);pediment.lineTo(2.1,0);pediment.lineTo(-2.1,0);
 mesh(building,new THREE.ExtrudeGeometry(pediment,{depth:.5,bevelEnabled:false}),stone,0,.74,1.25);
 const aquaBridge=group('aqueduct');
 const bridgeBlocks=[];
 // Three levels: broad lower arches, smaller upper arches, channel at the top.
 for(let floor=0;floor<3;floor++){
  const span=floor===2?.5:1, count=floor===2?12:6;
  const base=-1.55+floor*1.15, radius=span*.39;
  for(let i=0;i<=count;i++)bridgeBlocks.push(box(aquaBridge,span*.19,.74,.68,stone,-3+i*span,base+.37,0));
  for(let i=0;i<count;i++){
   const x=-3+(i+.5)*span;
   const a=mesh(aquaBridge,new THREE.TorusGeometry(radius,span*.10,8,28,Math.PI),stone,x,base+.69,0);arches.push(a);bridgeBlocks.push(a);
  }
  bridgeBlocks.push(box(aquaBridge,6.3,.18,.8,stone,0,base+1.08,0));
 }
 box(aquaBridge,6.3,.18,.85,stone,0,1.96,0);
 const waterLine=box(aquaBridge,6,.045,.32,aqua,0,2.08,0);
 const waterDrops=[];for(let i=0;i<14;i++)waterDrops.push(mesh(aquaBridge,new THREE.SphereGeometry(.045,8,8),aqua,0,2.12,0));
 const archDemo=group('archDemo'),archStones=[];
 for(let i=0;i<13;i++){
  const o=mesh(archDemo,new THREE.RingGeometry(1.05,1.48,4,1,i*Math.PI/13+.012,Math.PI/13-.024),i===6?brass:stone,0,-.3,.15);
  archStones.push(o);
 }
 box(archDemo,.43,1.45,.65,stone,-1.28,-1.02,0);box(archDemo,.43,1.45,.65,stone,1.28,-1.02,0);
 const archPulse=mesh(archDemo,new THREE.SphereGeometry(.085,12,10),aqua);
 const pierDemo=group('pierDemo');
 box(pierDemo,.9,2.6,1.2,stone,0,-.15,0);
 const nose=new THREE.Shape();nose.moveTo(-.45,0);nose.lineTo(0,1.1);nose.lineTo(.45,0);nose.closePath();
 const cutwater=mesh(pierDemo,new THREE.ExtrudeGeometry(nose,{depth:2.6,bevelEnabled:false}),stone);cutwater.rotation.x=Math.PI/2;cutwater.position.set(0,1.15,.6);
 const stream=[];for(let i=0;i<16;i++)stream.push(mesh(pierDemo,new THREE.SphereGeometry(.05,10,8),aqua));
 const pump=group('pump');box(pump,3,.2,1.7,mat(0x594031,.8),0,-1.3,0);
 mesh(pump,new THREE.CylinderGeometry(.36,.36,1.65,28,1,true),brass,0,-.35,0);
 const piston=mesh(pump,new THREE.CylinderGeometry(.07,.07,1.55,12),copper,0,.9,0);
 const handle=box(pump,1.8,.12,.13,brass,.5,1.5,0);
 curve(pump,[[0,-.8,0],[.8,-.8,0],[1,.1,0],[1.5,.1,0]],brass,.09);
 const pumpDrop=mesh(pump,new THREE.SphereGeometry(.09,12,10),aqua,1.5,0,0);
 const arena=group('arena');for(let floor=0;floor<3;floor++)for(let i=0;i<28;i++){const a=i/28*TAU,x=Math.cos(a)*2.2,z=Math.sin(a)*1.5,y=-1.15+floor*.72;const c=mesh(arena,new THREE.CylinderGeometry(.07,.08,.7,8),stone,x,y,z);const arch=mesh(arena,new THREE.TorusGeometry(.19,.055,6,18,Math.PI),stone,x,y+.3,z);arch.rotation.y=-a+Math.PI/2;}
 const pyramid=group('pyramid');const pyr=mesh(pyramid,new THREE.ConeGeometry(2.7,3.3,4),stone,0,-.05,0);pyr.rotation.y=Math.PI/4;
 for(let i=0;i<7;i++){const e=new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(3.7-i*.45,.01,3.7-i*.45)),new THREE.LineBasicMaterial({color:0xaa8050}));e.position.y=-1.5+i*.44;pyramid.add(e);}
 // Material and structural forces: non-quantitative explanatory diagrams.
 const structure=group('structure');
 const ribs=[];for(let i=0;i<8;i++){const a=i/8*TAU;const c=curve(structure,[[Math.cos(a)*1.8,-1,Math.sin(a)*1.8],[Math.cos(a)*1.2,1,Math.sin(a)*1.2],[0,1.7,0]],brass,.045);ribs.push(c);}
 const loads=ribs.map(()=>mesh(structure,new THREE.SphereGeometry(.09,12,10),aqua));
 const material=group('material');
 const blocks=[];for(let i=0;i<3;i++){box(material,3.5,.25,2.4,mat([0x927a59,0xb4a78f,0xd7ceb9][i],.85),0,i*.8-.8,0);for(let k=0;k<25;k++){const o=mesh(material,new THREE.DodecahedronGeometry(.065+(k%3)*.04),stone,-1.4+(k%5)*.7,i*.8-.58,-.9+Math.floor(k/5)*.45);blocks.push(o);}}
 const papers=group('papers');for(let i=0;i<3;i++){const sheet=box(papers,2.6,1.6,.04,mat(0x9c947a,.85),-.4+i*.4,-.7+i*.6,-i*.35);sheet.rotation.z=.08-i*.08;for(let j=0;j<5;j++)box(papers,1.7,.018,.02,brass,-.4+i*.4,-.3+i*.6-j*.2,-i*.35+.04);}
 const timeline=group('timeline');const timePoints=[];
 for(let i=0;i<3;i++){const o=mesh(timeline,new THREE.TorusGeometry(.25,.04,8,40),brass,-1.8+i*1.8,0,0);timePoints.push(o);}
 curve(timeline,[[-2.1,0,0],[0,0,0],[2.1,0,0]],brass,.02);const cursor=mesh(timeline,new THREE.SphereGeometry(.12,16,12),aqua);
 // Computing: chip, racks, network and explicit conceptual comparison cards.
 const chip=group('chip');box(chip,4,.12,3.4,mat(0x102e31,.6),0,-.4,0);const die=box(chip,1.6,.25,1.6,mat(0x22283e,.25,.55),0,-.15,0);
 for(let i=0;i<12;i++)for(let side=0;side<4;side++){let x=-.75+i*.14,z=.96;const pin=box(chip,.07,.08,.25,copper,x,-.19,z);pin.rotation.y=side*Math.PI/2;const v=new THREE.Vector3(x,0,z).applyAxisAngle(new THREE.Vector3(0,1,0),side*Math.PI/2);pin.position.set(v.x,-.19,v.z);}
 const cores=[];for(let i=0;i<36;i++)cores.push(box(chip,.19,.025,.19,i%5?violet:aqua,-.64+i%6*.255,0,-.64+Math.floor(i/6)*.255));
 const racks=group('racks');const leds=[];
 for(let i=0;i<4;i++){const x=-1.8+i*1.2;box(racks,.85,2.8,.9,blue,x,-.1,0);for(let j=0;j<9;j++){box(racks,.72,.18,1,mat(0x283b4a,.5),x,-1.2+j*.28,.02);leds.push(box(racks,.05,.04,.015,aqua,x+.22,-1.2+j*.28,.54));}}
 const network=group('network');const nodes=[],links=[],pulses=[];
 for(let layer=0;layer<3;layer++)for(let i=0;i<5;i++){nodes.push(mesh(network,new THREE.SphereGeometry(.13,16,12),layer===1?violet:aqua,-1.8+layer*1.8,-1.6+i*.8,Math.sin(i+layer)*.45));}
 for(let layer=0;layer<2;layer++)for(let i=0;i<5;i++)for(let j=0;j<5;j++){
  const a=nodes[layer*5+i].position,b=nodes[(layer+1)*5+j].position;let c=curve(network,[a.toArray(),[(a.x+b.x)/2,(a.y+b.y)/2,.15],b.toArray()],mat(0x255258,.5),.008);links.push(c.curve);pulses.push(mesh(network,new THREE.SphereGeometry(.035,8,6),i%2?aqua:violet));
 }
 const compare=group('compare');for(let i=0;i<2;i++){box(compare,1.7,2.6,.12,blue,-1.2+i*2.4,0,0);for(let j=0;j<4;j++)box(compare,1.25,.035,.04,j%2?aqua:violet,-1.2+i*2.4,.8-j*.5,.09);}
 const compareDot=mesh(compare,new THREE.SphereGeometry(.10,12,10),aqua);
 // Space / waves / magnetic fields provide fresh science subject families.
 const cosmos=group('cosmos');const planet=mesh(cosmos,new THREE.SphereGeometry(1.2,64,40),mat(0xa99567,.65),0,0,0);
 const rings=mesh(cosmos,new THREE.RingGeometry(1.5,2.3,128),new THREE.MeshStandardMaterial({color:0xbda97f,side:THREE.DoubleSide,roughness:.8,transparent:true,opacity:.7}));rings.rotation.x=-Math.PI/2+.25;
 const moon=mesh(cosmos,new THREE.SphereGeometry(.26,32,20),mat(0xbdb9a9,.9));
 const sun=mesh(cosmos,new THREE.SphereGeometry(.7,48,32),emit(0xffc265),-3,0,-1);
 const field=group('field');mesh(field,new THREE.SphereGeometry(.72,48,32),mat(0x286c90,.6));
 for(let i=0;i<12;i++){const a=i/12*TAU;curve(field,[[0,.8,0],[Math.cos(a)*2.1,.6,Math.sin(a)*2.1],[Math.cos(a)*2.1,-.6,Math.sin(a)*2.1],[0,-.8,0]],aqua,.012);}
 const wave=group('wave');const beads=[];for(let j=0;j<6;j++)for(let i=0;i<28;i++)beads.push(mesh(wave,new THREE.SphereGeometry(.035,8,6),j%2?aqua:violet,-2.4+i*.18,-.9+j*.36,0));
 const disk=mesh(wave,new THREE.CylinderGeometry(.8,.8,.18,48),blue,-2.9,0,0);disk.rotation.z=Math.PI/2;
 const all=Object.values(groups);
 function update(story,index,local,p,t){
  all.forEach(g=>{g.visible=false;g.position.set(0,-.25,0);g.rotation.set(0,0,0);g.scale.setScalar(1);});
  let g;const family=story.visual_family;
  if(family==='maritime'){
   const modes={hero:fleet,route:globe,weather:fleet,timeline,research:globe,evidence:story.variant==='polar'?wreck:pump,papers,wreck,pump};
   const mode=story.scenes[index].visual_mode;g=mode?modes[mode]:[fleet,globe,fleet,timeline,story.variant==='polar'?wreck:globe,story.variant==='polar'?wreck:pump,papers,fleet][index];
   if(!g)throw Error('Unsupported maritime visual mode');
   piston.position.y=.9+Math.sin(local*2)*.2;handle.rotation.z=Math.sin(local*2)*.16;pumpDrop.position.y=.1-(local*.8%1);
   ships[1].visible=story.topic_key!=='mary-celeste-1872';
   ice.forEach(o=>o.visible=story.variant==='polar');ocean.material.color.setHex(story.variant==='polar'?0x143e51:0x092f4a);
   ships.forEach((s,i)=>{s.rotation.set(Math.sin(t*.7+i)*.035,Math.sin(t*.13)*.12,Math.sin(t*.8+i)*.045);s.position.y=(i?.1:-.2)+Math.sin(t*.8+i)*.035;s.userData.sails.forEach(o=>{const pos=o.geometry.attributes.position;for(let k=0;k<pos.count;k++)pos.setZ(k,.03+Math.sin(pos.getX(k)*3+t*.8)*.05);pos.needsUpdate=true;o.geometry.computeVertexNormals();});});
   const positions=ocean.geometry.attributes.position;for(let k=0;k<positions.count;k++)positions.setZ(k,Math.sin(positions.getX(k)*2+t)*.035+Math.sin(positions.getY(k)*2-t*.8)*.025);positions.needsUpdate=true;ocean.geometry.computeVertexNormals();
   routePoint.position.copy(route.curve.getPoint((local*.12)%1));scanRings.forEach((o,i)=>o.scale.setScalar(.7+((local*.18+i*.22)%1)));
   wreckShip.rotation.y=.15*Math.sin(local*.2);
   if(index===2)g.scale.setScalar(1.18);
  }else if(family==='architecture'){
   const hero=story.variant==='aqueduct'?aquaBridge:story.variant==='pyramid'?pyramid:story.variant==='arena'?arena:building;
   const modes={hero,levels:hero,arch:story.variant==='aqueduct'||story.variant==='arena'?archDemo:structure,section:story.variant==='aqueduct'?pierDemo:hero,water:hero,material,assembly:hero};
   const mode=story.scenes[index].visual_mode;g=mode?modes[mode]:[hero,story.variant==='aqueduct'?hero:structure,story.variant==='aqueduct'?pierDemo:hero,hero,story.variant==='aqueduct'?archDemo:structure,material,hero,hero][index];
   if(!g)throw Error('Unsupported architecture visual mode');
   bridgeBlocks.forEach((o,i)=>{if(o.userData.baseY===undefined)o.userData.baseY=o.position.y;o.position.y=o.userData.baseY+(mode==='assembly'?(1-Math.min(1,Math.max(0,local*.7-i*.035)))*1.8:0);});
   waterDrops.forEach((o,i)=>o.position.x=-3+((local*.8+i*.43)%6));
   archStones.forEach((o,i)=>o.position.z=.15+(mode==='assembly'?(1-p)*i*.08:0));archPulse.position.set(Math.cos(local*.8)*1.26,Math.abs(Math.sin(local*.8))*1.26-.3,.24);
   stream.forEach((o,i)=>{const z=2-((local*.9+i*.3)%4);o.position.set((i%2?1:-1)*(.7+.3*Math.exp(-z*z)), -1.1,z);});
   dome.visible=!(index===2&&p>.35);cylinder.material.transparent=true;cylinder.material.opacity=index===2?.42:1;
   loads.forEach((o,i)=>o.position.copy(ribs[i].curve.getPoint((local*.3+i*.1)%1)));
   if(index===3)g.rotation.x=.35*Math.sin(p*Math.PI);
   if(index===6)g.position.y=-.25+(1-Math.min(1,local/2))*.7;
   waterLine.material.emissiveIntensity=1+.5*Math.sin(local*2);
  }else if(family==='compute'){
   const modes={chip,network,comparison:compare,deployment:racks,flow:network,limits:compare};const mode=story.scenes[index].visual_mode;g=mode?modes[mode]:[chip,network,network,compare,racks,chip,compare,chip][index];if(!g)throw Error('Unsupported computing visual mode');
   cores.forEach((o,i)=>o.material=i%5?violet:aqua);leds.forEach((o,i)=>o.visible=Math.sin(local*3+i)>.0);
   pulses.forEach((o,i)=>o.position.copy(links[i].getPoint((local*.32+i*.037)%1)));compareDot.position.set(Math.sin(local)*1.2,.7*Math.cos(local*.7),.25);
   if(g===chip){g.rotation.x=.38;g.rotation.y=.1+local*.1;}
  }else if(family==='space'){
   g=cosmos;rings.visible=story.variant==='saturn';sun.visible=story.variant==='eclipse'||index===3;
   planet.material.color.setHex(story.variant==='saturn'?0xa99567:0x286c90);
   moon.position.set(Math.cos(local*.3)*2.3,Math.sin(local*.3)*.35,Math.sin(local*.3)*2.3);planet.rotation.y=t*.1;rings.rotation.z=.12;
  }else if(family==='field'){g=field;g.rotation.y=local*.12;}
  else if(family==='wave'){g=wave;beads.forEach((b,i)=>b.position.x=-2.4+(i%28)*.18+Math.sin(i%28*.45-local*4)*.09);}
  else throw Error('Unsupported authored visual family: '+family);
  g.visible=true;
  if(!['field','compute'].includes(family))g.rotation.y+=.15*Math.sin(local*.18)+.18;
  root.rotation.z=.008*Math.sin(t*.3);
  cursor.position.x=-2.1+((local*.38)%1)*4.2;timePoints.forEach((o,i)=>o.scale.setScalar(1+.07*Math.sin(local*2-i)));
 }
 return {root,update};
}
