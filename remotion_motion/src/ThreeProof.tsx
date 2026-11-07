import React from 'react';
import {AbsoluteFill,useCurrentFrame,useVideoConfig,interpolate,spring} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import * as THREE from 'three';

const INK='#153e40',ACCENT='#179ca6',CREAM='#f4faf7';
const clamp={extrapolateLeft:'clamp',extrapolateRight:'clamp'} as const;
const mix=(f:number,a:number,b:number,x=0,y=1)=>interpolate(f,[a,b],[x,y],clamp);

// Topic: why the sky is blue — molecules scatter short wavelengths.
// Every element appears on the phrase that explains it.
const Molecule:React.FC<{p:[number,number,number];r:number;f:number;delay:number}>=
  ({p,r,f,delay})=>{
  const pop=spring({frame:f-delay,fps:30,config:{damping:14,stiffness:120}});
  const s=Math.max(0.001,pop*(1+Math.sin(f/22+delay)*0.045)); // breathing
  return <group position={p} scale={s} rotation={[f/95+delay,f/120,0]}>
    <mesh><sphereGeometry args={[r,20,20]}/>
      <meshPhysicalMaterial color="#9ad7cf" roughness={0.18} metalness={0.1} clearcoat={0.9}/></mesh>
    <mesh position={[r*0.75,0,0]}><sphereGeometry args={[r*0.42,16,16]}/>
      <meshPhysicalMaterial color="#d8f2ee" roughness={0.3}/></mesh>
    <mesh position={[-r*0.75,0,0]}><sphereGeometry args={[r*0.42,16,16]}/>
      <meshPhysicalMaterial color="#d8f2ee" roughness={0.3}/></mesh>
  </group>};

const Ray:React.FC<{f:number;delay:number;color:string;bend:[number,number,number];op:number}>=
  ({f,delay,color,bend,op})=>{
  const t=spring({frame:f-delay,fps:30,config:{damping:200,stiffness:60}});
  const end=new THREE.Vector3(...bend).multiplyScalar(t);
  return <group>
    <line>
      <bufferGeometry attach="geometry" onUpdate={g=>g.setFromPoints([new THREE.Vector3(-6,1.6,0),end])}/>
      <lineBasicMaterial attach="material" color={color} transparent opacity={op} linewidth={2}/>
    </line>
    <mesh position={end.toArray() as [number,number,number]}>
      <sphereGeometry args={[0.075,12,12]}/>
      <meshBasicMaterial color={color}/>
    </mesh>
  </group>};

export const ThreeProof:React.FC=()=>{
  const f=useCurrentFrame(); const {durationInFrames}=useVideoConfig();
  const p=mix(f,0,durationInFrames); // 0..1 across the shot
  // camera: continuous push-in + orbit, never still
  const camZ=9.6-p*2.6;
  const camX=Math.sin(p*Math.PI*2.6)*3.1;
  const camY=0.6+Math.cos(p*Math.PI*2.1)*0.95;

  const mols:Array<[number,number,number,number]>=[
    [-2.1,0.55,-0.7,0],[-0.7,-0.95,0.4,9],[0.9,0.5,-0.9,18],[2.35,-0.5,0.7,26],[-1.3,-0.4,1.2,33],[1.6,1.15,0.2,41],
  ];
  return <AbsoluteFill style={{background:`linear-gradient(180deg,#eaf6f2 0%,#d5ece7 55%,#bfe0da 100%)`,fontFamily:'Cairo'}}>
    <ThreeCanvas width={1080} height={1920} camera={{position:[camX,camY,camZ],fov:42}} style={{position:'absolute',inset:0}}>
      <color attach="background" args={['#e8f5f1']}/>
      <fog attach="fog" args={['#cfe7e1',10,22]}/>
      <ambientLight intensity={0.75}/>
      <directionalLight position={[4,7,6]} intensity={2.3} color="#ffffff"/>
      <pointLight position={[-4,-2,3]} intensity={26} color="#6fd6c9"/>
      <pointLight position={[3,3,-2]} intensity={14} color="#9ec9f0"/>
      {/* depth layer 1: far drifting dust */}
      {Array.from({length:46}).map((_,i)=>{
        const z=-7+((i*1.7)%5);
        return <mesh key={'d'+i} position={[((i*2.9+f*0.055)%14)-7,((i*4.3+f*0.032)%10)-5,z]}>
          <sphereGeometry args={[0.035+(i%3)*0.014,8,8]}/>
          <meshBasicMaterial color="#8fd0c6" transparent opacity={0.5}/>
        </mesh>})}
      {/* depth layer 2: molecules revealed per phrase */}
      {mols.map((m,i)=><Molecule key={'m'+i} p={[m[0],m[1],m[2]]} r={0.62} f={f} delay={Math.round(m[3])}/>)}
      {/* white light entering, then splitting into short (blue) and long (red) paths */}
      <Ray f={f} delay={0} color="#ffffff" bend={[-2.1,0.55,-0.7]} op={0.95}/>
      <Ray f={f} delay={26} color="#45bce6" bend={[0.9,0.5,-0.9]} op={0.9}/>
      <Ray f={f} delay={38} color="#eb7666" bend={[2.35,-0.5,0.7]} op={0.85}/>
      {/* orbiting field rings: continuous large-area movement */}
      {[0,1,2].map(k=><mesh key={'r'+k} rotation={[Math.PI/2.3+k*0.5,f*0.012*(k+1),0]} position={[0,-0.1,0]}>
        <torusGeometry args={[2.4+k*1.15,0.028,10,120]}/>
        <meshBasicMaterial color={k===0?'#45bce6':k===1?'#ae7ff0':'#179ca6'} transparent opacity={0.55}/>
      </mesh>)}
      {/* scattered short-wave halo around the struck molecule */}
      <mesh position={[0.9,0.5,-0.9]} scale={1+mix(f,26,120,0,1.9)}>
        <sphereGeometry args={[0.75,20,20]}/>
        <meshBasicMaterial color="#45bce6" transparent opacity={mix(f,26,50)*0.22*(1-mix(f,60,120))}/>
      </mesh>
    </ThreeCanvas>
    {/* text slot: the same top-slot rule as the layout contract */}
    <div style={{position:'absolute',top:190,left:110,right:110,textAlign:'center'}}>
      <div style={{display:'inline-block',padding:'26px 34px',borderRadius:22,background:'#153e40f2',
        color:CREAM,fontSize:52,fontWeight:800,lineHeight:1.45}}>
        الضوء الأزرق بيتشتّت أكتر — عشان كده السما زرقا
      </div>
    </div>
    <div style={{position:'absolute',bottom:150,left:0,right:0,textAlign:'center',color:INK,fontSize:30,fontWeight:600,opacity:0.72}}>
      نموذج ثلاثي الأبعاد · الحركة مربوطة بكل جملة
    </div>
  </AbsoluteFill>};
