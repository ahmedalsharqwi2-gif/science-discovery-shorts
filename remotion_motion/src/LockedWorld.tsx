import React,{useLayoutEffect,useRef,useState} from 'react';
import {AbsoluteFill,useCurrentFrame,useVideoConfig,delayRender,continueRender} from 'remotion';
// @ts-ignore declared JavaScript API belongs to this repository
import {createIdentityStage} from '../../professional_motion/locked_identity_stage.js';
import template from '../../config/visual_template.json';
export const LockedWorld=({scenes,index,profile,duration}:any)=>{const canvas=useRef<HTMLCanvasElement>(null),stage=useRef<any>(null);const [h]=useState(()=>delayRender('Subject-specific 3D'));const f=useCurrentFrame(),{fps}=useVideoConfig();useLayoutEffect(()=>{if(!canvas.current)return;stage.current=createIdentityStage(canvas.current,scenes,profile,template);stage.current.render(index,0,0);continueRender(h);return()=>stage.current?.dispose()},[scenes,index,profile,duration]);useLayoutEffect(()=>stage.current?.render(index,Math.min(1,f/fps/duration),f/fps),[f,fps,index,duration]);return <AbsoluteFill><canvas ref={canvas} style={{width:'100%',height:'100%'}}/></AbsoluteFill>};
