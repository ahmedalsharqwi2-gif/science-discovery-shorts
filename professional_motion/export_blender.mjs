/** Export the implemented Three.js geometry, not a second guessed asset catalog. */
import {readFile,writeFile} from 'node:fs/promises';
import * as THREE from 'three';
import {GLTFExporter} from 'three/addons/exporters/GLTFExporter.js';
import {proceduralDirector} from './procedural_story.js';
globalThis.FileReader=class{
 readAsArrayBuffer(blob){blob.arrayBuffer().then(value=>{this.result=value;this.onloadend?.();}).catch(error=>this.onerror?.(error));}
 readAsDataURL(blob){blob.arrayBuffer().then(value=>{this.result=`data:${blob.type};base64,${Buffer.from(value).toString('base64')}`;this.onloadend?.();}).catch(error=>this.onerror?.(error));}
};
const args=process.argv.slice(2);if(args.length!==5)throw Error('Usage: export_blender.mjs story.json scene-index progress time output.glb');
const [input,idx,p,t,output]=args;const story=JSON.parse(await readFile(input));
const index=Number(idx),progress=Number(p),time=Number(t);
if(!Number.isInteger(index)||index<0||index>=8||!Number.isFinite(progress)||progress<0||progress>1||!Number.isFinite(time)||time<0)throw Error('Invalid Blender scene sample');
const scene=new THREE.Scene();const director=proceduralDirector(scene,story);const view=director.update(index,progress,time);
scene.updateMatrixWorld(true);const binary=await new GLTFExporter().parseAsync(scene,{binary:true,onlyVisible:true});
await writeFile(output,Buffer.from(binary));await writeFile(output+'.json',JSON.stringify({engine:'blender',view,index,progress,time,geometry_source:'professional_motion/procedural_story.js',publishable:false},null,2));
