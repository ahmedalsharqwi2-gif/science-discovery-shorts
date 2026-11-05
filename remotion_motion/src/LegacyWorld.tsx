import React,{useLayoutEffect,useRef,useState} from 'react';
import {AbsoluteFill,useCurrentFrame,useVideoConfig,delayRender,continueRender} from 'remotion';
// The preserved runtime is JavaScript; only its bounded declarative API is used.
// @ts-ignore legacy engine has no TypeScript declaration
import {createIdentityStage} from '../../professional_motion/identity_stage.js';
export type DirectedScene={id:string;shot_type:string;hero_object:string;object_motion:string;secondary_object?:string;interaction?:string;asset?:string;asset_label?:string;background_clip?:string;asset_representation?:string;visual_rationale?:string;scenario?:string};
export const LegacyWorld=({scenes,index,profile,duration}:{scenes:DirectedScene[];index:number;profile:string;duration:number})=>{const canvas=useRef<HTMLCanvasElement>(null),stage=useRef<{render:(i:number,p:number,t:number)=>void;dispose:()=>void}|null>(null);const [handle]=useState(()=>delayRender('Legacy Three.js authored scene'));const frame=useCurrentFrame(),{fps}=useVideoConfig();
 useLayoutEffect(()=>{if(!canvas.current)return;stage.current=createIdentityStage(canvas.current,scenes,profile);stage.current!.render(index,Math.min(1,frame/fps/duration),frame/fps);continueRender(handle);return()=>{stage.current?.dispose();stage.current=null;};},[handle,profile,scenes,index,duration]);
 useLayoutEffect(()=>{stage.current?.render(index,Math.min(1,frame/fps/duration),frame/fps);},[frame,fps,index,duration]);
 return <AbsoluteFill><canvas ref={canvas} style={{width:'100%',height:'100%'}}/></AbsoluteFill>;
};
