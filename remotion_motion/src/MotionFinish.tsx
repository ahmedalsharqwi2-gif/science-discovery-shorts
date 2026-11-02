import React from 'react';
import {AbsoluteFill,interpolate,useCurrentFrame,useVideoConfig} from 'remotion';
export const MotionFinish=({accent,paper=false,archive=false}:{accent:string;paper?:boolean;archive?:boolean})=>{const f=useCurrentFrame();const {fps}=useVideoConfig();const t=f/fps;return <>
 {!paper&&<AbsoluteFill style={{pointerEvents:'none',background:`radial-gradient(ellipse at ${62+Math.sin(t*.13)*16}% ${25+Math.cos(t*.15)*13}%,${accent}08,transparent 65%)`,mixBlendMode:'screen'}}/>}
 {archive&&<svg width="1080" height="1920" style={{position:'absolute',inset:0,pointerEvents:'none',opacity:.035,mixBlendMode:'soft-light'}}><filter id="archive-grain"><feTurbulence type="fractalNoise" baseFrequency=".7" numOctaves="2" seed="12"/></filter><rect width="100%" height="100%" filter="url(#archive-grain)"/></svg>}
 <AbsoluteFill style={{pointerEvents:'none',background:paper?'#fffaf0':accent,opacity:interpolate(f,[0,9],[paper?.09:.045,0],{extrapolateRight:'clamp'})}}/>
 </>};
export const KineticTitle=({text}:{text:string})=>{const f=useCurrentFrame();return <>{text.split(/\s+/).map((word,i)=><React.Fragment key={i}><span style={{display:'inline-block',opacity:interpolate(f,[4+i*2,15+i*2],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'}),translate:`0 ${interpolate(f,[4+i*2,20+i*2],[18,0],{extrapolateLeft:'clamp',extrapolateRight:'clamp'})}px`}}>{word}</span>{' '}</React.Fragment>)}</>};
