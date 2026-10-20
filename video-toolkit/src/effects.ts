import {Application, Graphics} from 'pixi.js';
import {gsap} from 'gsap';
import * as THREE from 'three';
// Deterministic frame seeking: never rely on wall-clock animation for exported frames.
const app = new Application();
await app.init({width:540,height:960,preference:'webgl',background:'#101923'});
document.body.appendChild(app.canvas);
const glow = new Graphics().circle(270,480,180).fill(0xcda65c);
app.stage.addChild(glow);
const timeline = gsap.timeline({paused:true}).fromTo(glow,{alpha:0.2},{alpha:0.9,duration:2,ease:'power2.inOut'});
const renderer = new THREE.WebGLRenderer({alpha:true});
renderer.setSize(540,400);
renderer.domElement.style.cssText='position:absolute;top:280px;left:0';
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(45,540/400,0.1,100);
camera.position.z=4;
const object = new THREE.Mesh(new THREE.IcosahedronGeometry(1,1),new THREE.MeshNormalMaterial({wireframe:true}));
scene.add(object);
function seek(seconds:number){timeline.seek(seconds);object.rotation.set(seconds*.3,seconds*.5,0);renderer.render(scene,camera);app.renderer.render(app.stage);}
(window as any).toolkit={seek,ready:true};seek(1);
