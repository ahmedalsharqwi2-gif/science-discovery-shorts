import {hauntedStage} from './haunted.js';
import {channelStage} from './channels.js';
import * as THREE from 'three';
import {EffectComposer} from 'three/addons/postprocessing/EffectComposer.js';
import {RenderPass} from 'three/addons/postprocessing/RenderPass.js';
import {UnrealBloomPass} from 'three/addons/postprocessing/UnrealBloomPass.js';

const W=1080,H=1920;
const renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true,alpha:false});
renderer.setSize(W,H);renderer.setPixelRatio(1);renderer.setClearColor(0x030c14);
renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.02;
document.body.insertBefore(renderer.domElement,document.querySelector('#text'));
const scene=new THREE.Scene();scene.fog=new THREE.FogExp2(0x03121e,.035);
const camera=new THREE.PerspectiveCamera(40,W/H,.1,100);camera.position.set(0,1,14);
const composer=new EffectComposer(renderer);composer.addPass(new RenderPass(scene,camera));
const bloom=new UnrealBloomPass(new THREE.Vector2(W/2,H/2),.42,.55,.6);composer.addPass(bloom);bloom.setSize(W/2,H/2);
scene.add(new THREE.HemisphereLight(0x82d9e8,0x06131a,1.3));
function light(color,intensity,x,y,z){const l=new THREE.DirectionalLight(color,intensity);l.position.set(x,y,z);scene.add(l);return l;}
light(0xe9f0dc,2.4,3,5,5);light(0x3cdfff,1.5,-4,2,0);light(0xff8760,1.3,3,-1,-2);
const ambient=new THREE.PointLight(0x6ae4e3,35,25);ambient.position.set(0,2,-3);scene.add(ambient);

const uniforms={clock:{value:0},morph:{value:0},reveal:{value:1}};
function skinMaterial(){
 const m=new THREE.MeshPhysicalMaterial({color:0xffffff,roughness:.48,metalness:.04,clearcoat:.26,clearcoatRoughness:.3});
 m.onBeforeCompile=s=>{
  Object.assign(s.uniforms,uniforms);
  s.vertexShader=s.vertexShader.replace('#include <common>','#include <common>\nvarying vec3 skinP;uniform float morph;');
  s.vertexShader=s.vertexShader.replace('#include <begin_vertex>','#include <begin_vertex>\nskinP=position;transformed+=normal*morph*.035*sin(position.x*22.)*sin(position.y*24.);');
  s.fragmentShader=s.fragmentShader.replace('#include <common>',`#include <common>
    varying vec3 skinP;uniform float clock;uniform float morph;uniform float reveal;
    float hash21(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
    float dots(vec2 p){vec2 g=floor(p);vec2 f=fract(p);float md=1.;
      for(int y=-1;y<=1;y++)for(int x=-1;x<=1;x++){vec2 o=vec2(float(x),float(y));vec2 j=vec2(hash21(g+o),hash21(g+o+4.7));md=min(md,length(o+j-f));}return md;}
  `);
  s.fragmentShader=s.fragmentShader.replace('#include <color_fragment>',`#include <color_fragment>
    vec2 uv=vec2(skinP.x*1.8+skinP.z*.5,skinP.y*1.5);
    float wave=sin(uv.x*2.7+uv.y*2.-clock*.6)*.5+.5;
    float pigmentSpot=1.-smoothstep(.16,.35,dots(uv*7.));
    float fine=1.-smoothstep(.035,.15,dots(uv*28.));
    float front=smoothstep(-.7,.8,sin(uv.y*1.2+uv.x*.9-clock*.55));
    vec3 copper=vec3(.54,.17,.075);vec3 turquoise=vec3(.035,.33,.32);vec3 violet=vec3(.25,.085,.43);
    vec3 base=mix(copper,turquoise,front);
    base=mix(base,violet,wave*.42);
    base=mix(base,vec3(.40,.32,.19),morph);
    base=mix(base,vec3(.85,.45,.16),pigmentSpot*(.3+.35*front));
    base=mix(base,vec3(.05,.09,.10),fine*.65);
    diffuseColor.rgb*=base*1.25;
  `);
 };
 return m;
}
const skin=skinMaterial();
const octopus=new THREE.Group();scene.add(octopus);
const mantle=new THREE.Mesh(new THREE.SphereGeometry(1,64,48),skin);
mantle.scale.set(.79,1.20,.71);mantle.position.y=.85;octopus.add(mantle);
const collar=new THREE.Mesh(new THREE.SphereGeometry(1,48,32),skin);collar.scale.set(.68,.46,.6);collar.position.y=-.02;octopus.add(collar);
const pupilMat=new THREE.MeshPhysicalMaterial({color:0x020607,roughness:.08,clearcoat:1});
const eyeMat=new THREE.MeshPhysicalMaterial({color:0xaaa986,roughness:.22,metalness:.15});
for(const sign of [-1,1]){
 const eye=new THREE.Mesh(new THREE.SphereGeometry(.125,32,24),eyeMat);
 eye.position.set(sign*.53,.12,.46);eye.scale.set(1,1,1);octopus.add(eye);
 const pupil=new THREE.Mesh(new THREE.SphereGeometry(.088,32,20),pupilMat);pupil.position.set(sign*.53,.12,.585);pupil.scale.set(1,.29,.3);octopus.add(pupil);
 const dot=new THREE.Mesh(new THREE.SphereGeometry(.027,12,10),new THREE.MeshBasicMaterial({color:0xf1f4dd}));dot.position.set(sign*.53-.025,.17,.62);octopus.add(dot);
}
const arms=[];const N=56,R=10;
const suckerMat=new THREE.MeshStandardMaterial({color:0xd3b69d,roughness:.45,metalness:.1});
const suckers=new THREE.InstancedMesh(new THREE.TorusGeometry(.035,.014,5,12),suckerMat,8*22);octopus.add(suckers);
const dummy=new THREE.Object3D();
function center(s,k,t){
 const angle=(k/8)*Math.PI*2;
 const fan=Math.sin(angle),depth=Math.cos(angle);
 const curl=Math.pow(s,2.7);
 return new THREE.Vector3(
  fan*(.48+2.25*s)+Math.sin(s*6.5+t*1.05+k)*.22*s+Math.cos(k*2.2)*curl*.42,
  -.16-1.65*s+Math.sin(s*4.8+t*.9+k*.7)*.23*s+curl*(.65+.35*Math.sin(k)),
  depth*(.35+1.16*s)+Math.cos(s*5+t*.8+k)*.22*s);
}
for(let k=0;k<8;k++){
 const geo=new THREE.BufferGeometry();const pos=new Float32Array((N+1)*(R+1)*3);const idx=[];
 for(let i=0;i<N;i++)for(let j=0;j<R;j++){let a=i*(R+1)+j,b=a+R+1;idx.push(a,b,a+1,b,b+1,a+1);}
 geo.setAttribute('position',new THREE.BufferAttribute(pos,3));geo.setIndex(idx);
 const mesh=new THREE.Mesh(geo,skin);octopus.add(mesh);arms.push(mesh);
}
const up=new THREE.Vector3(0,0,1),axis=new THREE.Vector3(),normal=new THREE.Vector3(),binormal=new THREE.Vector3();
function poseOctopus(t){
 for(let k=0;k<8;k++){
  const positions=arms[k].geometry.attributes.position;
  for(let i=0;i<=N;i++){
   const s=i/N,c=center(s,k,t),next=center(Math.min(1,s+.01),k,t),prev=center(Math.max(0,s-.01),k,t);
   axis.copy(next).sub(prev).normalize();normal.crossVectors(axis,up).normalize();binormal.crossVectors(axis,normal).normalize();
   const radius=.155*Math.pow(1-s,.78)+.010;
   for(let j=0;j<=R;j++){
    const a=j/R*Math.PI*2;const v=c.clone().addScaledVector(normal,Math.cos(a)*radius).addScaledVector(binormal,Math.sin(a)*radius);
    positions.setXYZ(i*(R+1)+j,v.x,v.y,v.z);
   }
  }
  positions.needsUpdate=true;arms[k].geometry.computeVertexNormals();
  for(let j=0;j<22;j++){
   const s=.12+j*.036,c=center(s,k,t);c.z+=.10*(1-s);
   dummy.position.copy(c);dummy.rotation.set(0,0,Math.sin(t+k)*.1);dummy.scale.setScalar(1-.65*s);dummy.updateMatrix();suckers.setMatrixAt(k*22+j,dummy.matrix);
  }
 }
 suckers.instanceMatrix.needsUpdate=true;
 mantle.rotation.z=Math.sin(t*.7)*.055;
}
// Light shafts and suspended marine particles establish depth, not an empty template background.
const particles=new THREE.BufferGeometry();const pa=new Float32Array(260*3);
for(let i=0;i<260;i++){pa[i*3]=(Math.sin(i*127.13)*.5+.5)*16-8;pa[i*3+1]=(Math.sin(i*33.71)*.5+.5)*20-10;pa[i*3+2]=-Math.abs(Math.sin(i*19.23))*12;}
particles.setAttribute('position',new THREE.BufferAttribute(pa,3));
const dust=new THREE.Points(particles,new THREE.PointsMaterial({color:0x8ce4e0,size:.025,transparent:true,opacity:.45,depthWrite:false}));scene.add(dust);
const shafts=[];
for(let i=0;i<5;i++){
 const mat=new THREE.ShaderMaterial({uniforms:{opacity:{value:.025}},vertexShader:'varying vec2 uvp;void main(){uvp=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',fragmentShader:'varying vec2 uvp;uniform float opacity;void main(){float edge=pow(sin(uvp.x*3.14159265),2.);float fade=smoothstep(0.,.3,uvp.y)*(1.-smoothstep(.7,1.,uvp.y));gl_FragColor=vec4(.15,.4,.5,opacity*edge*fade);}',transparent:true,depthWrite:false,side:THREE.DoubleSide,blending:THREE.AdditiveBlending});
 const mesh=new THREE.Mesh(new THREE.PlaneGeometry(.25+i*.09,17),mat);mesh.position.set(-5+i*2.1,2,-5-i*.2);mesh.rotation.z=-.32;scene.add(mesh);shafts.push(mesh);
}
// Microscopic pigment sac with radial muscles.
const macro=new THREE.Group();scene.add(macro);macro.position.set(0,-.15,.5);
const sac=new THREE.Mesh(new THREE.SphereGeometry(1,72,40),new THREE.MeshPhysicalMaterial({color:0xc46838,roughness:.45,metalness:.02,clearcoat:.22,transparent:true,opacity:.9}));
sac.scale.set(1,1,.16);macro.add(sac);
const rim=new THREE.Mesh(new THREE.TorusGeometry(1,.018,8,128),new THREE.MeshStandardMaterial({color:0xffd8a2,emissive:0x764011,emissiveIntensity:.5}));macro.add(rim);
const fibers=[];
for(let k=0;k<28;k++){
 const a=k/28*Math.PI*2;
 const geo=new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(),new THREE.Vector3()]);
 const line=new THREE.Line(geo,new THREE.LineBasicMaterial({color:k%2?0x87d7ca:0xb5e8dd,transparent:true,opacity:.7}));macro.add(line);fibers.push({line,a});
 const tip=new THREE.Mesh(new THREE.SphereGeometry(.025,10,8),new THREE.MeshBasicMaterial({color:0xc4efe7}));tip.position.set(Math.cos(a)*2.05,Math.sin(a)*2.05,0);macro.add(tip);
}
const fleckGeo=new THREE.SphereGeometry(.025,8,6);const flecks=new THREE.InstancedMesh(fleckGeo,new THREE.MeshBasicMaterial({color:0xa4512d}),90);macro.add(flecks);
for(let k=0;k<90;k++){const a=k*2.399,r=Math.sqrt(k/90)*.91;dummy.position.set(Math.cos(a)*r,Math.sin(a)*r,.17);dummy.scale.setScalar(.4+(k%5)/4);dummy.updateMatrix();flecks.setMatrixAt(k,dummy.matrix);}
// Axon/dendrite network with travelling impulses and distinct downstream targets.
const neural=new THREE.Group();scene.add(neural);
const curves=[],impulses=[];
for(let i=0;i<12;i++){
 const y=-2.5+(i%4)*1.5,x=i<4?-2.6:i<8?2.6:(i%2?1.2:-1.2);
 const curve=new THREE.CatmullRomCurve3([new THREE.Vector3(0,1.5,0),new THREE.Vector3(x*.3,.7,.1),new THREE.Vector3(x*.75,y+.3,0),new THREE.Vector3(x,y,0)]);
 const tube=new THREE.Mesh(new THREE.TubeGeometry(curve,40,.016,5,false),new THREE.MeshStandardMaterial({color:0x298c91,emissive:0x1a7678,emissiveIntensity:.4}));neural.add(tube);curves.push(curve);
 const impulse=new THREE.Mesh(new THREE.SphereGeometry(.065,12,8),new THREE.MeshBasicMaterial({color:i%2?0xffd287:0x9af4ee}));neural.add(impulse);impulses.push(impulse);
 const target=new THREE.Mesh(new THREE.SphereGeometry(.2,20,16),new THREE.MeshStandardMaterial({color:0xd18338,emissive:0x7c4018,emissiveIntensity:.4,roughness:.4}));target.position.copy(curve.getPoint(1));target.scale.z=.25;neural.add(target);
}
const hub=new THREE.Mesh(new THREE.SphereGeometry(.25,24,16),new THREE.MeshPhysicalMaterial({color:0x95e7da,emissive:0x228f8f,emissiveIntensity:.5,roughness:.2}));hub.position.set(0,1.5,0);neural.add(hub);
// Exploded skin: translucent membrane, pigment plane, reflective crystal plane.
const layers=new THREE.Group();scene.add(layers);layers.rotation.set(-.7,.1,-.35);
const skinLayers=[];
for(let i=0;i<3;i++){
 const material=new THREE.MeshPhysicalMaterial({color:[0x79beae,0xd49251,0x77a5d8][i],transparent:true,opacity:[.35,.72,.55][i],roughness:.35,metalness:i===2?.5:.1,side:THREE.DoubleSide});
 const plane=new THREE.Mesh(new THREE.BoxGeometry(3.8,.04,3.0),material);plane.position.y=(1-i)*.8;layers.add(plane);skinLayers.push(plane);
 for(let k=0;k<36;k++){
  const gem=new THREE.Mesh(i===2?new THREE.OctahedronGeometry(.085):new THREE.SphereGeometry(.065+(k%4)*.014,10,8),new THREE.MeshStandardMaterial({color:i===1?(k%3?0xc48032:0x643a2a):i===2?0xb8e7fb:0x7ab5a9,metalness:i===2?.5:.1,roughness:.28}));
  gem.position.set(-1.6+(k%6)*.64,(1-i)*.8+.08,-1.2+Math.floor(k/6)*.48);if(i!==2)gem.scale.y=.2;layers.add(gem);
 }
}
const photons=[];
for(let i=0;i<12;i++){
 const p=new THREE.Mesh(new THREE.SphereGeometry(.04,10,8),new THREE.MeshBasicMaterial({color:0xd5f0ff}));layers.add(p);photons.push(p);
}
// Seabed props: deliberately illustrative geometry, no downloaded stock.
const reef=new THREE.Group();scene.add(reef);
const sand=new THREE.Mesh(new THREE.CircleGeometry(9,80),new THREE.MeshStandardMaterial({color:0x28423c,roughness:.9}));sand.rotation.x=-Math.PI/2;sand.position.y=-2.65;reef.add(sand);
for(let i=0;i<16;i++){
 const geo=new THREE.SphereGeometry(.4+(i%4)*.15,16,12);const m=new THREE.MeshStandardMaterial({color:i%3?0x3a6658:0x78533f,roughness:.9});const rock=new THREE.Mesh(geo,m);
 rock.position.set(Math.sin(i*12.3)*4,-2.5,Math.cos(i*7.2)*2-1);rock.scale.set(1,.45+(.5*Math.abs(Math.sin(i))),1);reef.add(rock);
}
const overlay=document.querySelector('#text'),ctx=overlay.getContext('2d');
const endCanvas=document.createElement('canvas');endCanvas.width=W;endCanvas.height=H;const endCtx=endCanvas.getContext('2d');
const channel=channelStage(scene);
const storyResponse=await fetch('./delivery/story.json');if(!storyResponse.ok)throw Error('Missing authored daily story');
let config=await storyResponse.json();const useOctopus=config.visual_family==='octopus',useHaunted=config.visual_family==='haunted_interior';
const haunted=useHaunted?hauntedStage(scene):null;
if(useHaunted){scene.fog.density=.043;renderer.toneMappingExposure=1.22;scene.traverse(o=>{if(o.isDirectionalLight)o.intensity*=.30;if(o.isHemisphereLight)o.intensity*=.55;});ambient.intensity=1.0;}
const backdrop={science:0x030c14,horror:0x030b10,history:0x100d09,news:0x090713}[config.profile];
renderer.setClearColor(backdrop);scene.fog.color.setHex(backdrop);
let timing=null;const response=await fetch('./delivery/timing.json');if(response.ok)timing=await response.json();
const DEFAULT=[0,4.4,9.5,15.1,21.2,27.4,33.5,40];
const defaultDuration=46.5;
const times=timing?timing.scenes.map(s=>s.start/timing.duration):DEFAULT.map(t=>t/defaultDuration);
let D=timing?.duration||defaultDuration;
const ACCENT='#87e7d8',ORANGE='#ffb16d',WHITE='#f1f0df',MUTED='#749894';
const clamp=(v,a=0,b=1)=>Math.max(a,Math.min(b,v));
const ease=x=>1-Math.pow(1-clamp(x),3);
function type(text,x,y,size=65,color=WHITE,align='center',alpha=1){ctx.save();ctx.globalAlpha=alpha;ctx.font=`700 ${size}px Noto`;ctx.fillStyle=color;ctx.textAlign=align;ctx.direction='rtl';ctx.textBaseline='middle';ctx.fillText(text,x,y);ctx.restore();}
function mono(text,x,y,size=23,color=MUTED,align='left'){ctx.save();ctx.font=`${size}px Plex`;ctx.fillStyle=color;ctx.textAlign=align;ctx.direction='ltr';ctx.fillText(text,x,y);ctx.restore();}
function line(x,y,x2,y2,color=ACCENT,alpha=.55){ctx.save();ctx.globalAlpha=alpha;ctx.strokeStyle=color;ctx.lineWidth=1.5;ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x2,y2);ctx.stroke();ctx.restore();}
function label(text,x,y,size=29){ctx.font=`${size}px Noto`;let w=ctx.measureText(text).width+42;ctx.fillStyle='rgba(5,25,29,.83)';ctx.strokeStyle='rgba(135,231,216,.3)';ctx.lineWidth=1;ctx.beginPath();ctx.roundRect(x-w/2,y-28,w,56,8);ctx.fill();ctx.stroke();type(text,x,y,size,ACCENT);}
function ring(cx,cy,r,t){ctx.save();ctx.translate(cx,cy);ctx.rotate(t*.12);ctx.strokeStyle='rgba(139,225,212,.25)';ctx.lineWidth=1;ctx.setLineDash([3,14]);ctx.beginPath();ctx.arc(0,0,r,0,Math.PI*2);ctx.stroke();ctx.setLineDash([]);for(let i=0;i<4;i++){const a=i*Math.PI/2;line(Math.cos(a)*(r-12),Math.sin(a)*(r-12),Math.cos(a)*(r+12),Math.sin(a)*(r+12));}ctx.restore();}
function caption(time){
 let content='';
 if(timing?.caption_groups){content=timing.caption_groups.find(g=>time>=g.start&&time<g.end)?.text||'';}
 else if(timing){const words=timing.words;const index=words.findIndex(w=>time>=w.start&&time<w.end+.08);if(index>=0){const start=Math.floor(index/6)*6;content=words.slice(start,start+6).map(w=>w.text).join(' ');}}
 if(!content)return;
 const words=content.split(' '),rows=[''];ctx.font='38px Noto';for(const word of words){const test=(rows[rows.length-1]+' '+word).trim();if(ctx.measureText(test).width>860)rows.push(word);else rows[rows.length-1]=test;}
 rows.forEach((r,i)=>type(r,W/2,1710+i*60,38,WHITE));
}
function drawText(t,index,local,p){
 ctx.clearRect(0,0,W,H);
 let g=ctx.createLinearGradient(0,0,0,620);g.addColorStop(0,'rgba(2,12,19,.96)');g.addColorStop(.75,'rgba(2,12,19,.45)');g.addColorStop(1,'rgba(2,12,19,0)');ctx.fillStyle=g;ctx.fillRect(0,0,W,620);
 g=ctx.createLinearGradient(0,1470,0,H);g.addColorStop(0,'rgba(2,12,19,0)');g.addColorStop(.5,'rgba(2,12,19,.76)');g.addColorStop(1,'rgba(2,12,19,.98)');ctx.fillStyle=g;ctx.fillRect(0,1470,W,450);
 mono('OCEAN / FIELD NOTES',75,100,22);type('أسرار الكون',1005,90,27,WHITE,'right');
 line(75,142,1005,142,ACCENT,.18);mono('0'+(index+1)+' / 08',75,202,21);mono('CEPHALOPODA',1005,202,20,MUTED,'right');
 const a=ease(local/.7),yy=(1-a)*35;
 if(index===0){if(p<.64){type('ده مش',W/2,315+yy,101,WHITE,'center',a);type('مجرد لون.',W/2,445+yy,116,ORANGE,'center',a);}else{type('في لحظة.',W/2,325,104,WHITE);type('بس إزاي؟',W/2,455,100,ORANGE);}mono('A LIVING DISPLAY',W/2,555,24,ACCENT,'center');}
 if(index===1){type('السر تحت السطح',W/2,345+yy,81,WHITE,'center',a);type('خلايا صغيرة. تأثير مذهل.',W/2,455+yy,36,ACCENT,'center',a);const point=mantle.localToWorld(new THREE.Vector3(.35,.1,.8)).project(camera);const px=(point.x+1)*W/2,py=(1-point.y)*H/2;ring(px,py,105,t);line(px+90,py-50,850,750);label('كروماتوفورات',800,700);}
 if(index===2){type('كيس صغير،',W/2,330+yy,88,WHITE,'center',a);type('فرق كبير.',W/2,440+yy,96,ORANGE,'center',a);label('صبغة داخل خلية',540,1490);mono('EXPAND / CONTRACT',540,1555,23,ACCENT,'center');}
 if(index===3){type('العضلات هي المحرّك',W/2,345+yy,76,WHITE,'center',a);line(760,1050,900,850);label('شدّ العضلات',820,800);line(390,1030,200,1250);label('كيس الصبغة',240,1320);ring(540,1040,365,t);}
 if(index===4){type('إشارة عصبية.',W/2,325+yy,83,WHITE,'center',a);type('استجابة بصرية.',W/2,435+yy,83,ACCENT,'center',a);label('أعصاب',540,690);label('عضلات',250,1450);label('لون',800,1450);}
 if(index===5){type('والضوء له دور',W/2,345+yy,84,WHITE,'center',a);type('مقطع توضيحي لطبقات الجلد',W/2,460+yy,32,ACCENT,'center',a);label('سطح الجلد',780,810);label('خلايا لونية',820,1020);label('خلايا عاكسة',750,1310);}
 if(index===6){type('تمويه.',W/2,335+yy,104,WHITE,'center',a);type('وأحيانًا تواصل.',W/2,465+yy,85,ORANGE,'center',a);mono('COLOR / PATTERN / TEXTURE',540,1500,22,ACCENT,'center');if(p>.6)label('تغيير الملمس كمان',540,1430);}
 if(index===7){type('جلد حيّ.',W/2,325+yy,100,WHITE,'center',a);type('نظام مذهل.',W/2,455+yy,108,ACCENT,'center',a);ring(540,1060,390,t);type('عضلات  ·  أعصاب  ·  خلايا ضوئية',540,1510,31,WHITE);}
 caption(t);
 if(!timing)mono('VISUAL + MUSIC STUDY / ORIGINAL VOICE PENDING',540,1790,16,'#749894','center');
 else mono('ILLUSTRATIVE SCIENCE / ORIGINAL CHARON NARRATION',540,1810,15,'#749894','center');
 const prog=clamp(t/D);ctx.fillStyle='#183337';ctx.fillRect(75,1848,930,3);ctx.fillStyle=ACCENT;ctx.fillRect(75,1848,930*prog,3);
 mono('SMITHSONIAN OCEAN · SCIENTIFIC ILLUSTRATION',540,1890,16,'#617f7e','center');
 // A brief asymmetric slit transition masks the cut without obscuring the whole film.
 const flash=1-clamp(local/.28);if(index>0&&flash>0){ctx.fillStyle=`rgba(103,228,208,${flash*.13})`;ctx.fillRect(W*(1-flash),230,10+flash*26,1330);}
}

function drawMeme(t,index){
 const s=config.scenes[index],measured=timing?.scenes[index];
 if(!s.punchline||measured?.meme_beat===undefined)return;
 const age=t-measured.meme_beat,span=Math.min(2.6,Math.max(1.6,(measured.meme_end??measured.meme_beat+1)-measured.meme_beat+.55));
 if(age<0||age>span)return;
 const enter=1-Math.pow(1-clamp(age/.18),3),exit=clamp((span-age)/.18),gain=enter*exit;
 ctx.save();ctx.globalAlpha=gain;ctx.translate(860,1205+(1-enter)*70);ctx.rotate(Math.sin(age*15)*.045*Math.exp(-age*4));ctx.scale(.8+.2*enter,.8+.2*enter);
 const face=ctx.createRadialGradient(-25,-35,8,0,0,100);face.addColorStop(0,'#ffe392');face.addColorStop(1,'#ec9c3c');
 ctx.shadowColor='rgba(0,0,0,.45)';ctx.shadowBlur=22;ctx.fillStyle=face;ctx.beginPath();ctx.arc(0,0,86,0,Math.PI*2);ctx.fill();ctx.shadowBlur=0;
 ctx.strokeStyle='#241c21';ctx.fillStyle='#241c21';ctx.lineWidth=8;ctx.lineCap='round';
 const reaction=s.reaction;
 if(reaction==='suspicious'){
  for(const side of [-1,1]){ctx.beginPath();ctx.moveTo(side*53,-37);ctx.lineTo(side*18,-26);ctx.stroke();ctx.beginPath();ctx.ellipse(side*33,-14,10,6,0,0,Math.PI*2);ctx.fill();}
  ctx.beginPath();ctx.moveTo(-30,38);ctx.lineTo(30,30);ctx.stroke();
 }else if(reaction==='smug'){
  for(const side of [-1,1]){ctx.beginPath();ctx.moveTo(side*50,-17);ctx.lineTo(side*18,-17);ctx.stroke();}
  ctx.beginPath();ctx.arc(0,9,40,.1,Math.PI-.1);ctx.stroke();
 }else{
  for(const side of [-1,1]){ctx.beginPath();ctx.ellipse(side*32,-22,reaction==='loading'?7:12,reaction==='loading'?7:17,0,0,Math.PI*2);ctx.fill();}
  ctx.beginPath();ctx.ellipse(0,36,16,reaction==='loading'?14:22,0,0,Math.PI*2);ctx.fill();
  if(reaction==='loading')for(let i=0;i<5;i++){ctx.fillStyle=`rgba(255,245,195,${.3+.7*(.5+.5*Math.sin(age*8+i))})`;ctx.beginPath();ctx.arc(-38+i*19,-112,5,0,Math.PI*2);ctx.fill();}
 }
 ctx.restore();
 ctx.save();ctx.globalAlpha=gain;ctx.fillStyle='#efbd65';ctx.beginPath();ctx.roundRect(88,1355,904,126,24);ctx.fill();
 let size=42;ctx.font=`${size}px Noto`;while(ctx.measureText(s.punchline).width>840&&size>28){size-=2;ctx.font=`${size}px Noto`;}
 type(s.punchline,540,1431,size,'#181727','center');ctx.restore();
}

function drawChannelText(t,index,local,p){
 ctx.clearRect(0,0,W,H);
 let g=ctx.createLinearGradient(0,0,0,650);g.addColorStop(0,'rgba(2,12,19,.97)');g.addColorStop(.7,'rgba(2,12,19,.6)');g.addColorStop(1,'rgba(2,12,19,0)');ctx.fillStyle=g;ctx.fillRect(0,0,W,650);
 g=ctx.createLinearGradient(0,1480,0,H);g.addColorStop(0,'rgba(2,12,19,0)');g.addColorStop(.45,'rgba(2,12,19,.7)');g.addColorStop(1,'rgba(2,12,19,.98)');ctx.fillStyle=g;ctx.fillRect(0,1480,W,440);
 const colors={science:'#87e7d8',history:'#efbb80',horror:'#a6cec9',news:'#b7a1ff'},accent=colors[config.profile];
 const names={science:'SCIENCE / FIELD NOTES',history:'HISTORY / STRUCTURES',horror:config.fiction?'HORROR / AFTER DARK':'DOCUMENTED / MYSTERIES',news:'AI / OFFICIAL SOURCE'};
 mono(names[config.profile],75,100,21);type(config.series,1005,90,27,WHITE,'right');line(75,142,1005,142,accent,.25);mono('0'+(index+1)+' / 08',75,202,21);
 const s=config.scenes[index],a=ease(local/.65),y=335+(1-a)*30;
 const words=s.label.split(' ');let size=76;ctx.font=`${size}px Noto`;while(ctx.measureText(s.label).width>930&&size>46){size-=2;ctx.font=`${size}px Noto`;}
 type(s.label,540,y,size,index===0||index===7?accent:WHITE,'center',a);
 if(index===0)type(config.title,540,455,35,WHITE,'center',a);
 if(config.visual_family==='maritime'&&index===1)label('مسار تخطيطي، مش خريطة ملاحة',540,1460,25);
 if(config.visual_family==='maritime'&&index===3){const dates=(config.milestones||[]).slice(0,3);dates.forEach((v,i)=>type(v,205+i*335,1110,32,accent));}
 
 const labels=s.labels||[];labels.slice(0,2).forEach((v,i)=>{if(local>.7+i*.5){label(v,i?820:260,i?1350:700,28);line(i?770:310,i?1300:750,i?670:420,i?1200:850,accent,.45);}});
 if(config.profile==='news')drawMeme(t,index);
 caption(t);
 if(config.profile==='news'&&config.source.published)type('تاريخ الخبر: '+config.source.published.slice(0,10),540,1772,21,MUTED,'center');
 mono(config.source.publisher.slice(0,48),540,1810,17,MUTED,'center');ctx.fillStyle='#183337';ctx.fillRect(75,1848,930,3);ctx.fillStyle=accent;ctx.fillRect(75,1848,930*clamp(t/D),3);
 type(config.profile==='news'?'الخبر من المصدر • القفشات تعليق ساخر':config.fiction?'ملفات غامضة • رعب':'رسوم توضيحية، مش تصوير للأحداث',540,1890,21,MUTED);
 const flash=1-clamp(local/.28);if(index>0&&flash>0){ctx.fillStyle=`rgba(103,228,208,${flash*.12})`;ctx.fillRect(W*(1-flash),230,10+flash*26,1330);}
}

window.renderAt=(time,duration=D)=>{
 D=duration;const t=Math.max(0,time),u=t/D;
 let index=times.findLastIndex(s=>s<=u);index=Math.max(0,index);
 const sceneStart=times[index]*D,sceneEnd=(times[index+1]??1)*D,local=t-sceneStart,p=clamp(local/(sceneEnd-sceneStart));
 uniforms.clock.value=t;uniforms.morph.value=index===6?(.5-.5*Math.cos(p*Math.PI*2)):0;
 if(useOctopus)poseOctopus(t);
 octopus.visible=useOctopus&&[0,1,6,7].includes(index);macro.visible=useOctopus&&[2,3].includes(index);neural.visible=useOctopus&&index===4;layers.visible=useOctopus&&index===5;reef.visible=useOctopus&&index===6;channel.root.visible=!useOctopus&&!useHaunted;if(!useOctopus&&!useHaunted)channel.update(config,index,local,p,t);
 octopus.scale.setScalar(index===0?.78+.14*ease(p*2):index===6?.85:index===7?.9:.91);
 octopus.position.set(index===0?Math.sin(t*.3)*.08:0,index===0?-.4+.25*ease(p*2):-.25,0);
 octopus.rotation.set(.08*Math.sin(t*.3),index===0?-.45+.5*ease(p):.12*Math.sin(t*.2),index===0?-.18*(1-ease(p)):.035*Math.sin(t*.3));
 let camX=index===0?1.5*(1-ease(p)):index===3?.7*Math.sin(p*Math.PI):index===5?1.2*Math.sin(p*1.5):Math.sin(t*.11)*.25;
 camera.position.set(camX,index===5?1.5:1.1, index===1?14-3.2*ease(Math.max(0,p-.35)/.65):index===2?13:index===5?13.5:14);camera.lookAt(0,index===1?.35+.3*p:.35,0);
 const expansion=.52+.38*(.5-.5*Math.cos(local*1.15));sac.scale.set(expansion,expansion,.18);rim.scale.setScalar(expansion);flecks.scale.set(expansion,expansion,1);
 macro.rotation.set(index===3?.24:.08,.08*Math.sin(local*.4),.025*Math.sin(local*.6));macro.scale.setScalar(index===2?1.26:1.1);macro.position.y=-.25;
 for(const f of fibers){const pos=f.line.geometry.attributes.position;pos.setXYZ(0,Math.cos(f.a)*expansion,Math.sin(f.a)*expansion,0);pos.setXYZ(1,Math.cos(f.a)*2.05,Math.sin(f.a)*2.05,.02);pos.needsUpdate=true;}
 neural.rotation.y=.12*Math.sin(local*.22);neural.position.y=-.25;neural.scale.setScalar(.92);
 impulses.forEach((m,i)=>m.position.copy(curves[i].getPoint((local*.36+i*.13)%1)));
 hub.scale.setScalar(1+.1*Math.sin(local*5));
 layers.rotation.y=.12+Math.sin(local*.25)*.11;layers.position.y=-.3;layers.scale.setScalar(1.03);
 photons.forEach((m,i)=>{const q=(local*.35+i*.13)%1,travel=q<.5?q*2:2-q*2;m.position.set(-1.5+(i%4)+Math.max(0,q-.5)*.8,1.7-travel*2.5,Math.sin(i)*.8);m.material.color.setHex(q<.5?0xe2f6ff:0x87d5ff);});
 if(useHaunted){const beat=timing?.scenes[index]?.scare_beat;const view=haunted.update(config,index,local,p,t,beat===undefined?-1:t-beat);camera.position.set(...view.position);camera.lookAt(...view.target);}
 dust.visible=!useHaunted;shafts.forEach(o=>o.visible=!useHaunted);
 dust.rotation.y=t*.012;dust.position.y=Math.sin(t*.11)*.5;shafts.forEach((m,i)=>m.material.uniforms.opacity.value=.025+.015*(.5+.5*Math.sin(t*.2+i)));
 composer.render();if(useOctopus)drawText(t,index,local,p);else drawChannelText(t,index,local,p);
 return {scene:index+1,time:t,duration:D,originalVoice:!!timing};
};
window.captureFrame=()=>{endCtx.drawImage(renderer.domElement,0,0);endCtx.drawImage(overlay,0,0);return endCanvas.toDataURL('image/jpeg',.96).split(',')[1];};
await document.fonts.load('700 96px Noto');await document.fonts.load('24px Plex');window.renderAt(0);window.ready=true;
