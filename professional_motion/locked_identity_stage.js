/** Fixed reference framing, then measured projection; never a whole-scene CSS squeeze. */
import * as THREE from 'three';
import {proceduralDirector} from './procedural_story.js';
export function createIdentityStage(canvas,plan,profile,t){
 if(!t?.locked||t.channel!==profile)throw Error('Locked channel template required');
 const {w,h}=t.canvas,z=t.safe_zone,layout=t.layout;
 const renderer=new THREE.WebGLRenderer({canvas,antialias:true,preserveDrawingBuffer:true});renderer.setSize(w,h,false);renderer.setPixelRatio(1);renderer.setClearColor(t.palette.bg);renderer.toneMapping=THREE.ACESFilmicToneMapping;
 const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(35,w/h,.1,200);scene.add(new THREE.HemisphereLight(t.palette.ink,t.palette.bg,2));const light=new THREE.DirectionalLight(t.palette.ink,2.5);light.position.set(4,7,8);scene.add(light);
 const defs=plan.map(s=>({environment:'molecular_water',camera_start:[0,0,10],camera_end:[0,0,10],objects:[{kind:s.hero_object,position:[0,0,0],scale:[1,1,1],rotation:[0,0,0],motion:s.object_motion,color:t.palette.ink},...(s.secondary_object&&s.secondary_object!=='none'?[{kind:s.secondary_object,position:[2.2,0,0],scale:[.55,.55,.55],rotation:[0,0,0],motion:'none',color:t.palette.ink}]:[])]}));
 const director=proceduralDirector(scene,{profile,visual_plan:{world:'procedural_story'},scenes:defs});
 scene.traverse(o=>{if(o.isMesh&&o.material){for(const m of Array.isArray(o.material)?o.material:[o.material])if(m.color){const v=(m.color.r+m.color.g+m.color.b)/3;m.color=new THREE.Color(t.palette.bg).lerp(new THREE.Color(t.palette.ink),.25+v*.6);}}});
 const corners=box=>{const a=[];for(const x of [box.min.x,box.max.x])for(const y of [box.min.y,box.max.y])for(const z of [box.min.z,box.max.z])a.push(new THREE.Vector3(x,y,z));return a;};
 const projected=box=>{const a=corners(box).map(v=>v.project(camera));return [Math.min(...a.map(v=>(v.x+1)*w/2)),Math.min(...a.map(v=>(1-v.y)*h/2)),Math.max(...a.map(v=>(v.x+1)*w/2)),Math.max(...a.map(v=>(1-v.y)*h/2))];};
 const bounds=stage=>{const b=new THREE.Box3();for(const o of stage.objects)b.expandByObject(o.object);return b;};
 const distances=director.stages.map(stage=>{scene.updateMatrixWorld(true);const b=bounds(stage),center=b.getCenter(new THREE.Vector3());stage.group.position.sub(center);scene.updateMatrixWorld(true);const centered=bounds(stage);let d=12;camera.clearViewOffset();for(let n=0;n<8;n++){camera.position.set(0,0,d);camera.lookAt(0,0,0);camera.updateMatrixWorld(true);camera.updateProjectionMatrix();const bb=projected(centered);d*=Math.max(bb[2]-bb[0],bb[3]-bb[1])/layout.focal_reference_max_extent;}return d;});
 const scale=layout.focal_display_scale;if(scale<z.art_stage.min_scale_vs_reference)throw Error('Focal reference scale is below policy');
 return {render(index,p,time){director.update(index,p,time);for(const o of director.stages[index].objects)if(o.spec.motion==='grow')o.object.scale.set(...o.spec.scale).multiplyScalar(.96+.04*p);camera.position.set(0,0,distances[index]/scale);camera.lookAt(0,0,0);camera.setViewOffset(w,h,0,h/2-(z.art_stage.focal_y[0]+z.art_stage.focal_y[1])/2,w,h);camera.updateMatrixWorld(true);scene.updateMatrixWorld(true);const box=projected(bounds(director.stages[index]));canvas.dataset.focalBox=JSON.stringify(box);canvas.dataset.focalScale=String(scale);renderer.render(scene,camera);},dispose(){scene.traverse(o=>{o.geometry?.dispose();for(const m of Array.isArray(o.material)?o.material:o.material?[o.material]:[])m.dispose();});renderer.dispose();renderer.forceContextLoss();}};
}
