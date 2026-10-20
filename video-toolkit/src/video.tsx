import React from 'react';
import {AbsoluteFill, Composition, interpolate, registerRoot, useCurrentFrame} from 'remotion';
const Sample=()=>{
 const frame=useCurrentFrame();
 const x=interpolate(frame,[0,59],[-90,90]);
 return <AbsoluteFill style={{backgroundColor:'#101923',color:'#e9d4a8',fontFamily:'sans-serif',alignItems:'center',justifyContent:'center'}}>
  <div style={{fontSize:42,direction:'rtl'}}>اختبار محرك الفيديو</div>
  <div style={{height:160,width:160,borderRadius:'50%',background:'#cda65c',marginTop:70,transform:`translateX(${x}px)`}}/>
  <div style={{fontSize:20,marginTop:90}}>540 × 960 · 30 FPS</div>
 </AbsoluteFill>;
};
registerRoot(()=> <Composition id="ToolkitCheck" component={Sample} durationInFrames={60} fps={30} width={540} height={960}/>);
