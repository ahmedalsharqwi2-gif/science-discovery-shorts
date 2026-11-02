import React from 'react';
import {interpolate,useCurrentFrame,useVideoConfig} from 'remotion';
const ink='#141d35',paper='#fff7e8',coral='#d65d47';
const mix=(a:number,b:number,p:number)=>a+(b-a)*p;
const smooth=(p:number)=>{p=Math.max(0,Math.min(1,p));return p*p*(3-2*p);};
const elbow=(a:[number,number],b:[number,number],bend:number):[number,number]=>{const dx=b[0]-a[0],dy=b[1]-a[1],d=Math.max(1,Math.hypot(dx,dy)),h=Math.sqrt(Math.max(0,78*78-Math.min(155,d)**2/4));return [(a[0]+b[0])/2-dy/d*h*bend,(a[1]+b[1])/2+dx/d*h*bend];};
const Limb=({from,to,bend=1}:{from:[number,number];to:[number,number];bend?:number})=>{const e=elbow(from,to,bend);return <path d={`M${from}L${e}L${to}`} fill="none" stroke={ink} strokeWidth="10" strokeLinecap="round" strokeLinejoin="round"/>;};
export const StickmanPlate=({action,duration}:{action:string;duration:number})=>{const f=useCurrentFrame();const {fps}=useVideoConfig();const time=f/fps,p=f/(duration*fps),act=smooth((p-.2)/.55),late=smooth((p-.55)/.25);const walk=action==='untie'?Math.sin(time*7)*smooth(p*4)*(1-smooth((p-.5)*4)):action==='sneeze'?Math.sin(time*5)*Math.max(0,1-p*3):0;
 const x=action==='untie'?mix(370,700,smooth(p*2)):action==='sneeze'?mix(500,640,smooth(p*2)):420;
 const y=1165-Math.abs(walk)*5,sh:[number,number]=[x,y-90],hips:[number,number]=[x+Math.sin(time*.8)*2,y+35];
 const right:[number,number]=['focus','tether'].includes(action)?[x+120,y-145]:action==='catch'?[x+130,y-75]:action==='untie'?[x+90,y+25]:[x+92,y-65-Math.sin(time)*4];
 const left:[number,number]=action==='shout'?[x-70,y-145]:action==='catch'?[x-35,y-70]:[x-76,y-12];
 let key:[number,number]=[920-act*32,802];if(action==='shout')key=[890-act*60,802];if(['whisper','focus','tether'].includes(action))key=[830-act*45,802];if(action==='catch')key=[mix(785,x+130,act),mix(802,y-75,act)-Math.sin(act*Math.PI)*70];if(action==='sneeze')key=[x-14,y+26];
 const happy=['catch','sneeze'].includes(action),shocked=['discover','shout','tether'].includes(action);const headX=x+(action==='shout'?11:0),headY=y-167;
 return <svg viewBox="0 0 1080 1920" style={{position:'absolute',inset:0,width:'100%',height:'100%'}}>
 <defs><pattern id="paperDots" width="28" height="28" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r=".7" fill="#a79c88" opacity=".18"/></pattern><filter id="shadow"><feGaussianBlur stdDeviation="9"/></filter></defs>
 <rect width="1080" height="1920" fill="#f7f1e7"/><rect width="1080" height="1920" fill="url(#paperDots)"/>
 <path d="M80 1390H1020M95 1398L1010 1398" fill="none" stroke={ink} strokeWidth="4"/><path d="M1040 1375V590H700" fill="none" stroke="#b9b0a2" strokeWidth="3"/>
 <path d="M720 835H1020L1000 850H740Z" fill="#d4b384" stroke={ink} strokeWidth="4"/>
 <path d="M720 1205H1030V1260H730Z" fill="#e2d0af" stroke={ink} strokeWidth="4"/><path d="M755 1260V1375M995 1260V1375" stroke={ink} strokeWidth="6"/>
 <path d={`M755 1209H1010V1255H755Z`} fill="#e4c999" stroke={ink} strokeWidth="4"/><path d="M861 1231H910" stroke={ink} strokeWidth="5" strokeLinecap="round"/>
 {Array.from({length:3},(_,i)=>{const shove=action==='shout'?act:action==='sneeze'?late:0;return <g key={i} style={{translate:`${-shove*(100+i*55)}px ${shove*shove*(75+i*40)}px`,rotate:`${-shove*(13+i*8)}deg`,transformOrigin:`${850+i*40}px 825px`}}><rect x={840+i*40} y={755-i*4} width="31" height={75+i*4} rx="3" fill={['#d86551','#79a09d','#e9b961'][i]} stroke={ink} strokeWidth="3"/><path d={`M${846+i*40} 773H${865+i*40}`} stroke="#fff6e5" strokeWidth="3"/></g>;})}
 <g style={{translate:action==='shout'?`${-act*200}px ${act*act*300}px`:undefined,rotate:action==='shout'?`${act*55}deg`:undefined,transformOrigin:'770px 810px'}}><path d="M744 780H790L785 824H750Z" fill="#d9ecdf" stroke={ink} strokeWidth="4"/><path d="M790 788Q815 790 801 811H789" fill="none" stroke={ink} strokeWidth="4"/></g>
 {['discover','whisper','focus','tether','untie'].includes(action)?<path d={`M${key}Q${950-act*60} 935 886 1230`} fill="none" stroke="#94795d" strokeWidth="3" strokeDasharray={action==='untie'&&late>.1?'3 12':undefined} opacity={action==='untie'?1-late:1}/>:null}
 <ellipse cx={x} cy="1382" rx="112" ry="13" fill="#3b3543" opacity=".15" filter="url(#shadow)"/>
 <Limb from={hips} to={[x-52-walk*22,1377-Math.max(0,walk)*30]} bend={1}/><Limb from={hips} to={[x+55+walk*22,1377-Math.max(0,-walk)*30]} bend={-1}/>
 <path d={`M${sh}Q${x-5} ${y-20} ${hips}`} fill="none" stroke={ink} strokeWidth="12" strokeLinecap="round"/>
 <Limb from={sh} to={left} bend={1}/><Limb from={sh} to={right} bend={-1}/>
 {[left,right].map((h,i)=><circle key={i} cx={h[0]} cy={h[1]} r="10" fill="#ffcf78" stroke={ink} strokeWidth="3"/>)}
 <circle cx={headX} cy={headY} r="47" fill={paper} stroke={ink} strokeWidth="8"/>
 {[headX-13,headX+15].map((xx,i)=><ellipse key={i} cx={xx+5} cy={headY-5} rx="4.5" ry={shocked?7:5} fill={ink}/>)}
 {happy?<path d={`M${headX-14} ${headY+15}Q${headX+2} ${headY+35} ${headX+21} ${headY+13}`} fill="none" stroke={ink} strokeWidth="4"/>:action==='shout'||action==='sneeze'?<ellipse cx={headX+15} cy={headY+21} rx={action==='shout'?12:6} ry="14" fill={ink}/>:<path d={`M${headX-8} ${headY+21}H${headX+16}`} stroke={ink} strokeWidth="4" strokeLinecap="round"/>}
 {['focus','tether','untie'].includes(action)?<path d={`M${headX+45} ${headY+20}L${headX+155} ${headY-35}V${headY+75}Z`} fill="#fffaf0" stroke={ink} strokeWidth="4"/>:null}
 {['discover','shout','whisper','focus','tether','catch','sneeze'].includes(action)?Array.from({length:4},(_,i)=>{const q=(time*.8+i*.22)%1,r=35+q*(action==='shout'||action==='sneeze'?300:160);return <path key={i} d={`M${headX+60+r*.75} ${headY-r*.6}Q${headX+110+r} ${headY+15} ${headX+60+r*.75} ${headY+r*.6}`} fill="none" stroke={coral} strokeWidth={action==='shout'||action==='sneeze'?7:3} opacity={(1-q)*.8*(action==='sneeze'?late:1)}/>;}):null}
 <g style={{translate:`${key[0]}px ${key[1]}px`,rotate:action==='catch'?`${act*30}deg`:'-12deg'}}><circle r="16" fill="#dfb44f" stroke={ink} strokeWidth="4"/><circle r="6" fill={paper}/><path d="M14 0H61V11H49V23H36V10H14Z" fill="#dfb44f" stroke={ink} strokeWidth="3"/></g>
 {action==='tether'?<path d="M820 930L870 940M824 920L870 920" stroke={coral} strokeWidth="5"/>:null}
 {action==='discover'?<text x="525" y="865" fill={coral} fontSize="78" fontFamily="Arabic">؟</text>:null}
 <text x="540" y="1450" textAnchor="middle" fill="#777064" fontSize="26" fontFamily="Arabic" direction="rtl">فرضية خيالية</text>
 </svg>;
};
