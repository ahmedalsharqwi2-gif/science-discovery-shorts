import React from 'react';
import {AbsoluteFill,Composition,Sequence,Audio,Img,registerRoot,staticFile,useCurrentFrame,interpolate,spring,useVideoConfig} from 'remotion';
import {BrandLogo} from './Logo';
import {Character} from './Character';
import config from '../config/channel.json';
type Word={text:string;start:number;end:number};
type Scene={title:string;text:string;summary:string;keyword:string;template:string;labels:string[];values:number[];kind:string;sourceUrl?:string;sourceLabel?:string;duration:number;words:Word[];background?:string;expression:number;action:string};
export type EpisodeProps={title:string;scenes:Scene[];audio?:string;durationInFrames:number;preview?:boolean;incomplete?:boolean;editorialLabel?:string|null};
const W=1080,H=1920;
const tokens={ink:'#15343a',cream:'#fff0d0',sage:'#b6dbc1',blue:'#45bce6',violet:'#ae7ff0',amber:'#f4a561'};
function Label({x,y,width,text,fontSize=30}:{x:number;y:number;width:number;text:string;fontSize?:number}){return <foreignObject x={x} y={y} width={width} height={110}><div data-text-box style={{fontFamily:'ChannelArabic',fontSize,lineHeight:1.3,textAlign:'center',color:'white',direction:'rtl',overflowWrap:'anywhere'}}>{text}</div></foreignObject>;}
function Diagram({scene,index}:{scene:Scene;index:number}){
 const f=useCurrentFrame(),t=f/30,{fps}=useVideoConfig();const p=spring({fps,frame:f,config:{damping:24}});
 const line=config.accent;const nodes=scene.labels;
 return <svg width={W} height="950" viewBox="0 0 1080 950" style={{position:'absolute',top:500,transform:`scale(${.92+p*.08})`}}>
 <defs><radialGradient id="orb"><stop stopColor={tokens.sage}/><stop offset="1" stopColor={line}/></radialGradient><filter id="glow"><feGaussianBlur stdDeviation="8"/></filter></defs>
 {scene.template==='phenomenon'&&<g transform="translate(540 420)">{Array.from({length:8},(_,i)=>{const a=i*Math.PI/4+t*.12;return <g key={i}><line x2={Math.cos(a)*290} y2={Math.sin(a)*290} stroke={line} opacity=".35"/><circle cx={Math.cos(a)*290} cy={Math.sin(a)*290} r={25+8*Math.sin(t+i)} fill="url(#orb)"/></g>})}<circle r="120" fill="url(#orb)"/><ellipse rx="365" ry="115" fill="none" stroke={line} strokeWidth="3" transform={`rotate(${index*20+t*4})`}/></g>}
 {scene.template==='comparison'&&[0,1].map(i=><g key={i} transform={`translate(${i?765:315} 410)`}><rect x="-180" y="-200" width="360" height="400" rx="55" fill={i?line:'#42676a'} opacity=".6"/><circle cy={-30+Math.sin(t*2+i)*18} r={65+i*30} fill="url(#orb)"/><Label x={-150} y={105} width={300} text={nodes[i]}/></g>)}
 {['steps','cause','journey'].includes(scene.template)&&nodes.map((s,i)=>{const x=880-i*(700/Math.max(1,nodes.length-1)),y=400+Math.sin(i)*110;return <g key={i} opacity={interpolate(f,[i*12,i*12+18],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'})}>{i>0&&<path d={`M${x+60} ${y} Q${x+130} ${y-160} ${x+700/(nodes.length-1)-60} ${400+Math.sin(i-1)*110}`} stroke={line} strokeWidth="7" fill="none" strokeDasharray="12 9"/>}<circle cx={x} cy={y} r="65" fill="url(#orb)"/><Label x={x-(nodes.length>3?85:130)} y={y+95} width={nodes.length>3?170:260} text={s} fontSize={nodes.length>3?28:32}/><text x={x} y={y+13} fill={tokens.ink} textAnchor="middle" fontSize="40">{i+1}</text></g>})}
 {scene.template==='chart'&&scene.values.length>0?scene.values.map((v,i)=><g key={i}><rect x={170+i*155} y={650-v*4*p} width="110" height={v*4*p} rx="15" fill={line}/><text x={225+i*155} y={620-v*4*p} textAnchor="middle" fill="white" fontSize="35">{v}%</text><Label x={160+i*155} y={680} width={130} text={nodes[i]||''} fontSize={26}/></g>):null}
 {(scene.template==='map'||scene.template==='chart'&&!scene.values.length)&&<g><ellipse cx="540" cy="430" rx="325" ry="295" stroke={line} strokeWidth="3" fill="#122d36"/><path d="M330 250 L450 200 570 280 535 390 640 430 595 600 500 630 470 490 350 420Z" fill={tokens.sage} opacity=".8"/><ellipse cx="540" cy="430" rx="325" ry="100" fill="none" stroke={line} opacity=".5"/><ellipse cx="540" cy="430" rx="135" ry="295" fill="none" stroke={line} opacity=".5"/><circle cx={540+Math.cos(t*.5)*300} cy={430+Math.sin(t*.5)*150} r="13" fill={tokens.amber}/><text x="540" y="815" fill="white" textAnchor="middle" fontSize="27">رسم توضيحي مبسط، مش خريطة حدود</text></g>}
 {Array.from({length:15},(_,i)=><circle key={'p'+i} cx={(i*97+f*.4)%1080} cy={(i*137)%900} r="3" fill={tokens.sage} opacity=".3"/>)}
 </svg>;
}
function Shot({scene,index,count,incomplete,editorialLabel}:{scene:Scene;index:number;count:number;incomplete?:boolean;editorialLabel?:string|null}){
 const f=useCurrentFrame(),time=f/30,entrance=interpolate(f,[0,16],[0,1],{extrapolateRight:'clamp'}),beat=Math.floor(f/90);
 const palettes=[['#152c36','#28453e'],['#252239','#535072'],['#183a35','#34655b'],['#493a36','#916453']];const palette=palettes[index%4];
 const active=scene.words.findIndex(w=>time>=w.start&&time<w.end);const start=active<0?0:Math.floor(active/5)*5;const visible=scene.words.slice(start,start+5);
 const horror=config.profile==='horror';
 return <AbsoluteFill style={{background:`linear-gradient(155deg,${horror?'#080d11':palette[0]},${horror?'#24322e':palette[1]})`,fontFamily:'ChannelArabic',color:'white',direction:'rtl',overflow:'hidden'}}>
 {scene.background&&<Img src={staticFile(scene.background)} style={{width:'100%',height:'100%',objectFit:'cover',opacity:.58,transform:`scale(${1+time*.002})`}}/>}
 <div style={{position:'absolute',top:170,left:80,right:80,display:'flex',justifyContent:'space-between',alignItems:'center',fontSize:26,color:tokens.cream}} data-text-box>
 <BrandLogo/>
 <span>{config.counter} · {index+1}/{count}</span></div>
 {(incomplete||editorialLabel)&&<div data-text-box style={{position:'absolute',top:310,left:95,right:95,textAlign:'center',fontSize:24,color:'#fff0d0'}}>{incomplete?'معاينة غير مكتملة • بدون صوت':editorialLabel}</div>}
 <div style={{position:'absolute',top:350,left:95,right:95,fontSize:58,fontWeight:800,lineHeight:1.4,opacity:entrance,transform:`translateY(${(1-entrance)*20}px)`,textAlign:'center'}} data-text-box>{scene.title}</div>
 <div style={{position:'absolute',inset:0,transform:`scale(${1+(beat%2)*.025})`,transition:'none'}}>{config.profile==='stickman'?<svg width={W} height={H}><Character frame={f} expression={scene.expression} action={scene.action}/><text x="540" y="1350" fill="white" textAnchor="middle" fontSize="44">{scene.labels[beat%scene.labels.length]}</text></svg>:<Diagram scene={scene} index={index}/>}</div>
 <div style={{position:'absolute',top:1380,left:100,right:100,height:174,boxSizing:'border-box',borderRadius:22,padding:'22px 30px',background:'#102c30ed',boxShadow:'0 10px 30px #0003',fontSize:visible.map(w=>w.text).join(' ').length>65?30:40,fontWeight:800,textAlign:'center',lineHeight:1.35,overflowWrap:'anywhere'}} data-text-box>
 {visible.length?visible.map((word,i)=><React.Fragment key={i}><span style={{color:start+i===active?tokens.amber:'white'}}>{word.text}</span>{' '}</React.Fragment>):scene.summary}</div>
 <div style={{position:'absolute',top:1600,left:100,right:100,fontSize:21,color:'#eee',textAlign:'center'}} data-text-box>{scene.kind==='legend'?'أسطورة — مش واقعة مؤكدة':scene.kind==='illustration'?'سيناريو تخيّلي للتوضيح':'المصدر: '+(scene.sourceLabel||'موثّق في بيانات الحلقة')}</div>
 </AbsoluteFill>;
}
export function Episode(props:EpisodeProps){let seconds=0;return <AbsoluteFill><style>{`@font-face{font-family:ChannelArabic;src:url('${staticFile('fonts/Arabic-Bold.ttf')}')} *{box-sizing:border-box}`}</style>{props.audio&&<Audio src={staticFile(props.audio)}/>} {props.scenes.map((scene,i)=>{const from=Math.round(seconds*30);seconds+=scene.duration;const end=i===props.scenes.length-1?props.durationInFrames:Math.round(seconds*30);return <Sequence key={i} from={from} durationInFrames={end-from}><Shot scene={scene} index={i} count={props.scenes.length} incomplete={props.incomplete} editorialLabel={props.editorialLabel}/></Sequence>})}</AbsoluteFill>;}
