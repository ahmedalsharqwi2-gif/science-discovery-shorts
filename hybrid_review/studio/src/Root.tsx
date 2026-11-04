import React from 'react';
import {AbsoluteFill,Composition,Img,Sequence,staticFile,useCurrentFrame,useVideoConfig,interpolate,Easing} from 'remotion';
import {Audio,Video} from '@remotion/media';
import {loadFont} from '@remotion/fonts';
import science from '../public/science.json';
import history from '../public/history.json';
loadFont({family:'Arabic',url:staticFile('fonts/Arabic-Bold.ttf'),weight:'700'});
loadFont({family:'Arabic',url:staticFile('fonts/Arabic-Regular.ttf'),weight:'400'});
type Caption={text:string;startMs:number;endMs:number;timestampMs:number|null;confidence:number|null};
const bounded={extrapolateLeft:'clamp',extrapolateRight:'clamp'} as const;
const ease={...bounded,easing:Easing.bezier(.16,1,.3,1)};
const Captions=({captions,paper=false}:{captions:Caption[];paper?:boolean})=>{const f=useCurrentFrame(),{fps}=useVideoConfig();const current=captions.find(c=>c.startMs<=f/fps*1000&&f/fps*1000<c.endMs);return current?<div dir="rtl" style={{position:'absolute',left:80,right:80,bottom:265,textAlign:'center',fontSize:45,lineHeight:1.65,fontWeight:700,color:paper?'#153e40':'#fff8e9',textShadow:paper?'none':'0 3px 16px #000'}}><span style={{background:paper?'#f4fbf2ee':'#151412dc',boxDecorationBreak:'clone',padding:'12px 20px',borderRadius:paper?12:0}}>{current.text}</span></div>:null;};
const ReviewMark=({paper=false}:{paper?:boolean})=><div dir="rtl" style={{position:'absolute',left:65,top:80,fontSize:22,color:paper?'#416469':'#ebd4a2',letterSpacing:1}}>عينة إخراج • للمراجعة</div>;
const ScienceOverlay=()=>{const f=useCurrentFrame(),{fps}=useVideoConfig(),t=f/fps,cluster=t>=17.28,local=cluster?t-17.28:t;return <>
 <div style={{position:'absolute',top:85,right:70,fontSize:25,color:'#416469'}}>اسرار الكون / كيمياء الحياة</div>
 <div dir="rtl" style={{position:'absolute',top:190,left:70,right:70,color:'#153e40',fontSize:91,fontWeight:700,lineHeight:1.4,translate:`0 ${interpolate(local,[0,.8],[24,0],ease)}px`,opacity:interpolate(local,[0,.45],[0,1],bounded)}}>{cluster?'الدهون تتحاصر':'جزيء واحد.. طرفان'}</div>
 <div dir="rtl" style={{position:'absolute',top:470,right:72,fontSize:31,lineHeight:1.7,color:'#487375'}}>{cluster?'الذيول للداخل / الرؤوس للخارج':'رأس يتفاعل مع الماء / ذيل ينجذب للدهون'}</div>
 <svg viewBox="0 0 1080 1920" style={{position:'absolute',inset:0,pointerEvents:'none'}}>
  <path d={cluster?'M775 750L900 655H950':'M745 940L885 725H960'} fill="none" stroke="#1e9ca9" strokeWidth="3" strokeDasharray="7 8" opacity=".7"/>
  <circle cx={cluster?775:745} cy={cluster?750:940} r="13" fill="none" stroke="#1e9ca9" strokeWidth="3"/>
 </svg>
 <div dir="rtl" style={{position:'absolute',top:1430,left:72,right:72,display:'flex',gap:35,justifyContent:'center',alignItems:'center',fontSize:28,color:'#31565c'}}><span><b style={{color:'#159cac'}}>●</b> الرأس المحب للماء</span><span><b style={{color:'#c59131'}}>━</b> الذيل المحب للدهون</span></div>
 <div dir="rtl" style={{position:'absolute',bottom:170,right:75,left:75,fontSize:23,textAlign:'center',color:'#56797b'}}>تصوّر جزيئي مبسّط • الأحجام والحركة توضيحية</div>
 <div dir="rtl" style={{position:'absolute',bottom:105,left:75,right:75,fontSize:25,textAlign:'center',color:'#2c7d7c'}}>#كيمياء_الحياة　#الصابون　#علوم</div>
 <ReviewMark paper/>
 </>;};
export const ScienceHybrid=()=>{const {fps}=useVideoConfig();return <AbsoluteFill style={{background:'#e5f2ed',fontFamily:'Arabic'}}>
 <Video name="Legacy Three.js molecular world" src={staticFile('science/base-aligned.mp4')} muted premountFor={fps} objectFit="cover" style={{width:'100%',height:'100%'}}/>
 <ScienceOverlay/>
 <Captions captions={science.captions} paper/>
 <Audio src={staticFile('science/mix.wav')} premountFor={fps}/>
 </AbsoluteFill>;};
const HistoryOverlay=()=>{const f=useCurrentFrame(),{fps}=useVideoConfig(),t=f/fps;const opening=t<10;const headline=opening?'إزاي تنقل معبد؟':t<15.14?'منحوت في الجبل':t<25?'قبل ما المياه توصل':'إنقاذ الأصل.. مش نسخة';const changed=t<10?0:t<15.14?10:t<25?15.14:25;return <>
 <AbsoluteFill style={{background:'linear-gradient(180deg,#0e1517d9 0%,transparent 32%,transparent 64%,#121712ee 100%)',pointerEvents:'none'}}/>
 <div dir="rtl" style={{position:'absolute',top:85,right:65,fontSize:26,color:'#f0d9a9'}}>نقص ونروى / إنقاذ أبو سمبل</div>
 <div dir="rtl" style={{position:'absolute',top:210,left:65,right:65,fontSize:opening?104:84,lineHeight:1.4,fontWeight:700,color:'#fff8e8',opacity:interpolate(t-changed,[0,.55],[0,1],bounded),translate:`0 ${interpolate(t-changed,[0,.7],[35,0],ease)}px`,textShadow:'0 3px 30px #0009'}}>{headline}</div>
 <div style={{position:'absolute',left:70,top:opening?520:470,width:interpolate(t-changed,[0,.8],[0,180],ease),height:5,background:'#edc37a'}}/>
 {t<5.5?<svg viewBox="0 0 1080 1920" style={{position:'absolute',inset:0}}><path d="M140 940H320L460 800" stroke="#f4d598" strokeWidth="3" fill="none" strokeDasharray="8 7"/><circle cx="460" cy="800" r={25+Math.sin(t*3)*3} stroke="#f4d598" strokeWidth="3" fill="none"/></svg>:null}
 {t>=15.14&&t<21.5?<div dir="rtl" style={{position:'absolute',top:1170,left:65,padding:'13px 20px',fontSize:30,color:'#fff8e8',background:'#1c3339c9',borderRight:'5px solid #ddbc7e'}}>خطر خزان المياه الجديد</div>:null}
 <div dir="rtl" style={{position:'absolute',bottom:180,left:70,right:70,fontSize:22,color:'#ddcba5',textAlign:'center'}}>صور أرشيفية حقيقية • Per-Olow Anderson / UNESCO • الملكية العامة</div>
 <div dir="rtl" style={{position:'absolute',bottom:112,left:70,right:70,fontSize:25,color:'#f0d7a4',textAlign:'center'}}>#أبو_سمبل　#تاريخ_مصر　#قصة_حقيقية</div>
 <ReviewMark/>
 </>;};
export const HistoryHybrid=()=>{const {fps}=useVideoConfig();return <AbsoluteFill style={{background:'#101817',fontFamily:'Arabic'}}>
 <Video name="Legacy Photo Motion archival camera" src={staticFile('history/base.mp4')} muted premountFor={fps} objectFit="cover" style={{width:'100%',height:'100%'}}/>
 <HistoryOverlay/>
 <Captions captions={history.captions}/>
 <Audio src={staticFile('history/mix.wav')} premountFor={fps}/>
 </AbsoluteFill>;};
export const Root=()=> <>
 <Composition id="ScienceHybrid" component={ScienceHybrid} width={1080} height={1920} fps={30} durationInFrames={1037}/>
 <Composition id="HistoryHybrid" component={HistoryHybrid} width={1080} height={1920} fps={30} durationInFrames={871}/>
 </>;
