import React from 'react';import {useCurrentFrame} from 'remotion';import {scientificSubject} from '../pipeline/subject-policy.mjs';
type Scene={title:string;text:string;labels:string[];template:string;values:number[]};
function Word({text,x,y,width=220}:{text:string;x:number;y:number;width?:number}){return <foreignObject x={x-width/2} y={y} width={width} height={100}><div data-text-box style={{fontFamily:'ChannelArabic',fontSize:28,color:'#fff0d0',textAlign:'center',lineHeight:1.35,direction:'rtl'}}>{text}</div></foreignObject>;}
export function ScientificDiagram({scene}:{scene:Scene}){
 const f=useCurrentFrame(),t=f/30,kind=scientificSubject(scene),labels=scene.labels.slice(0,5);
 return <svg width="1080" height="950" viewBox="0 0 1080 950" style={{position:'absolute',top:500}}>
 <defs><radialGradient id="star-core"><stop stopColor="#fffbdc"/><stop offset=".35" stopColor="#ffd578"/><stop offset="1" stopColor="#e96a44" stopOpacity=".02"/></radialGradient><radialGradient id="galaxy-core"><stop stopColor="#fff9db"/><stop offset=".35" stopColor="#d4b3ff" stopOpacity=".8"/><stop offset="1" stopColor="#8a91ed" stopOpacity="0"/></radialGradient></defs>
 {kind==='galaxy'&&<g transform={`translate(540 410) rotate(${-12+t*.25})`}>
  <ellipse rx="345" ry="220" fill="url(#galaxy-core)" opacity=".27"/>
  {Array.from({length:360},(_,i)=>{const arm=i%3,j=Math.floor(i/3),radius=35+j*2.6,angle=arm*Math.PI*2/3+j*.065+t*.008,noise=Math.sin(i*21.7)*14;return <circle key={i} cx={Math.cos(angle)*(radius+noise)} cy={Math.sin(angle)*(radius+noise)*.54} r={1.5+(i%5)*.6} fill={i%6===0?'#ffc987':i%4===0?'#a7c9ff':'#f5ecff'} opacity={.45+(i%7)*.07}/>;})}
  <ellipse rx="105" ry="64" fill="url(#galaxy-core)"/><ellipse rx="30" ry="18" fill="#fff3cc" opacity=".75"/>
 </g>}
 {kind==='star'&&(scene.template==='comparison'?<g>
  <circle cx="300" cy="430" r="80" fill="url(#star-core)"/><circle cx="760" cy="430" r="160" fill="url(#star-core)"/>
  <Word x={300} y={610} text={labels[0]||'الشمس'}/><Word x={760} y={610} text={labels[1]||'النجم العملاق'}/>
 </g>:<g transform="translate(540 410)">
  <circle r={210+Math.sin(t*1.2)*10} fill="url(#star-core)"/>
  {Array.from({length:18},(_,i)=>{const a=i*Math.PI/9+t*.018,r=138+Math.sin(t*1.2+i)*10;return <path key={i} d={`M${Math.cos(a)*r} ${Math.sin(a)*r} Q${Math.cos(a+.06)*250} ${Math.sin(a+.06)*250} ${Math.cos(a+.14)*300} ${Math.sin(a+.14)*300}`} fill="none" stroke={i%2?'#f1ae62':'#ffdb9c'} strokeWidth={i%3+1} opacity={.25+.2*Math.sin(t+i)**2}/>;})}
  <circle r="105" fill="url(#star-core)"/><circle r="54" fill="#ffdd9a" opacity=".55"/>
 </g>)}
 {kind==='cluster'&&<g transform="translate(540 410)">{Array.from({length:110},(_,i)=>{const a=i*2.39996,r=Math.sqrt(i)*25;return <circle key={i} cx={Math.cos(a)*r} cy={Math.sin(a)*r*.7} r={i%9===0?7:2.5} fill={i%7===0?'#fff0c9':'#a6d9ff'} opacity={.5+.4*Math.sin(i+1)**2}/>;})}<Word x={0} y={250} width={700} text="رسم توضيحي لتجمع نجمي — النجوم مش مجرة مستقلة"/></g>}
 {kind==='light'&&<g><path d="M180 450 Q540 210 900 450" fill="none" stroke="#96d8c4" strokeWidth="4" strokeDasharray="12 10"/><circle cx={180+((t*.12)%1)*720} cy={450-Math.sin(((t*.12)%1)*Math.PI)*120} r="11" fill="#ffe4a3"/><circle cx="180" cy="450" r="52" fill="#ffd578"/><circle cx="900" cy="450" r="35" fill="#85c6df"/><Word x={260} y={560} text={labels[0]||'مصدر الضوء'}/><Word x={820} y={560} text={labels[1]||'وصول الضوء'}/></g>}
 {kind==='planet'&&<g transform="translate(540 410)"><circle r="235" fill="#1e586f"/><ellipse rx="235" ry="90" fill="none" stroke="#7da6aa" opacity=".6"/><ellipse rx="100" ry="235" fill="none" stroke="#7da6aa" opacity=".6"/><path d="M-165 -125 L-72 -173 6 -112 -19 -30 76 32 27 124 -56 143 -83 27 -158 -12Z" fill="#a4c8a4"/><path d="M90 -128 L166 -79 139 -9 73 -38Z" fill="#a4c8a4"/></g>}
 {kind==='concept'&&<g>
  {labels.map((label,i)=>{const angle=-Math.PI/2+i*Math.PI*2/Math.max(3,labels.length),x=540+Math.cos(angle)*285,y=425+Math.sin(angle)*215;return <g key={i}><path d={`M540 425 Q${(540+x)/2+30} ${(425+y)/2-25} ${x} ${y}`} stroke="#8bcbbd" strokeWidth="3" fill="none" strokeDasharray="9 8"/><circle cx={x} cy={y} r="47" fill="#2b7271" stroke="#a8e3ce" strokeWidth="2"/><Word x={x} y={y+62} text={label} width={205}/></g>;})}
  <circle cx="540" cy="425" r="80" fill="#96d8c4" opacity=".9"/><circle cx="540" cy="425" r="50" fill="#214c51"/>
 </g>}
 <Word x={540} y={800} width={780} text={kind==='galaxy'?'رسم توضيحي لمجرة حلزونية — مش صورة رصدية':kind==='star'?'رسم توضيحي للشرح — الأحجام مش مقيّسة':kind==='cluster'?'توضيح للتجمع النجمي — الأحجام غير مقيسة':kind==='light'?'مسار توضيحي للضوء — المسافات غير مقيسة':kind==='planet'?'رسم توضيحي مبسط — مش خريطة حدود':'خريطة أفكار توضيحية — مش خريطة جغرافية'}/>
 </svg>;
}
