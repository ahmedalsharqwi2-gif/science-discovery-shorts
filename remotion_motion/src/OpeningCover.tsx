import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';

/** A cover over the episode's own opening artwork, never unrelated stock art. */
export const OpeningCover=({text,series,accent,paper=false}:{text:string;series:string;accent:string;paper?:boolean})=>{
 const frame=useCurrentFrame();
 if(frame>=18)return null;
 const ink=paper?'#122b32':'#fff9ef';
 const base=paper?'#f7f1e7':'#071522';
 return <AbsoluteFill dir="rtl" lang="ar" style={{fontFamily:'Arabic',opacity:interpolate(frame,[12,18],[1,0],{extrapolateLeft:'clamp',extrapolateRight:'clamp'}),background:`linear-gradient(180deg,${base} 0%,${base} 31%,transparent 47%,transparent 78%,${base} 100%)`}}>
  <div style={{position:'absolute',top:98,left:80,right:80,color:accent,fontSize:34,fontWeight:700}}>{series}</div>
  <div style={{position:'absolute',top:210,left:80,right:80,color:ink,fontSize:text.length>65?76:text.length>42?96:120,fontWeight:700,lineHeight:1.35,overflowWrap:'anywhere',textShadow:paper?'none':'0 6px 25px #0009'}}>{text}</div>
  <div style={{position:'absolute',left:80,right:80,bottom:110,display:'flex',justifyContent:'space-between',alignItems:'center',color:ink,fontSize:26}}><span style={{borderRight:`5px solid ${accent}`,paddingRight:18}}>تصور توضيحي</span><span style={{color:accent}}> {paper?'ماذا لو؟':'اكتشف الحكاية'} </span></div>
 </AbsoluteFill>;
};
