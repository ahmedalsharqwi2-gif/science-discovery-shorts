// @ts-nocheck — experimental @remotion/three composition is not used by the daily renderer.
import React from 'react';
import {AbsoluteFill,useCurrentFrame,useVideoConfig,interpolate,spring} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import type {Scene} from './types';

const C = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const M = (f: number, a: number, b: number, x = 0, y = 1) => interpolate(f, [a, b], [x, y], C);

/* The science channel's scenes arrive as experiment / process / comparison / macro.
   None of those had a visual component, so the frame was an empty background.
   This engine renders the *subject* in 3D: the camera orbits continuously, the
   elements assemble per phrase, and the formation follows the scene kind. */

type Pos = [number, number, number];

const layout = (kind: string, n: number): Pos[] => {
  const out: Pos[] = [];
  for (let i = 0; i < n; i++) {
    const a = (i / n) * Math.PI * 2;
    switch (kind) {
      case 'comparison':
        out.push([i % 2 === 0 ? -2.4 : 2.4, (Math.floor(i / 2) - n / 4) * 0.92, (i % 3) * 0.3 - 0.3]);
        break;
      case 'process':
        out.push([-4.2 + (8.4 * i) / Math.max(1, n - 1), Math.sin(i * 1.1) * 0.75, Math.cos(i * 0.9) * 0.7]);
        break;
      case 'macro':
        out.push([Math.cos(a * 2.2) * 1.55, Math.sin(a * 1.7) * 1.45, Math.cos(a) * 1.5]);
        break;
      case 'experiment':
        out.push([Math.cos(a) * (2.15 + (i % 3) * 0.3), (i / n - 0.5) * 2.7, Math.sin(a) * 2.15]);
        break;
      default:
        out.push([((i % 3) - 1) * 2.05, (Math.floor(i / 3) - 1) * 1.75, ((i % 2) - 0.5) * 2.1]);
    }
  }
  return out;
};

const Node: React.FC<{p: Pos; f: number; delay: number; color: string; r: number}> = ({p, f, delay, color, r}) => {
  const pop = spring({ frame: f - delay, fps: 30, config: { damping: 15, stiffness: 110 } });
  const s = Math.max(0.001, pop * (1 + Math.sin(f / 18 + delay) * 0.06));
  return (
    <group position={p} scale={s} rotation={[f / 130 + delay, f / 170, 0]}>
      <mesh>
        <sphereGeometry args={[r, 22, 22]} />
        <meshPhysicalMaterial color={color} roughness={0.16} metalness={0.22} clearcoat={1} />
      </mesh>
      <mesh scale={1.45}>
        <sphereGeometry args={[r, 14, 14]} />
        <meshBasicMaterial color={color} transparent opacity={0.09} />
      </mesh>
    </group>
  );
};

export const Science3D: React.FC<{scene: Scene; accent: string}> = ({ scene, accent }) => {
  const f = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const kind = scene.kicker || 'process';
  const p = M(f, 0, durationInFrames);
  const nodes = layout(kind, kind === 'comparison' ? 8 : kind === 'process' ? 7 : 6);

  const camZ = 10.4 - p * 3.1;
  const camX = Math.sin(p * Math.PI * 2.4) * 3.4;
  const camY = 0.5 + Math.cos(p * Math.PI * 1.9) * 1.15;

  const labels = scene.labels || [];
  return (
    <AbsoluteFill style={{ background: '#06171f', fontFamily: 'Cairo' }}>
      <ThreeCanvas width={1080} height={1920} camera={{ position: [camX, camY, camZ], fov: 44 }} style={{ position: 'absolute', inset: 0 }}>
        <color attach="background" args={['#071b24']} />
        <fog attach="fog" args={['#04121a', 9, 24]} />
        <ambientLight intensity={0.7} />
        <directionalLight position={[5, 8, 6]} intensity={2.4} color="#ffffff" />
        <pointLight position={[-4, -2, 4]} intensity={28} color={accent} />
        <pointLight position={[4, 3, -3]} intensity={16} color="#7fb2ff" />
        {Array.from({ length: 54 }).map((_, i) => (
          <mesh key={`d${i}`} position={[((i * 2.7 + f * 0.07) % 15) - 7.5, ((i * 4.1 + f * 0.04) % 11) - 5.5, -7 + ((i * 1.6) % 5)]}>
            <sphereGeometry args={[0.032 + (i % 3) * 0.012, 6, 6]} />
            <meshBasicMaterial color={accent} transparent opacity={0.45} />
          </mesh>
        ))}
        {nodes.map((n, i) => (
          <Node key={i} p={n} f={f} delay={Math.round((i * durationInFrames) / (nodes.length + 3))} color={i % 4 === 0 ? '#f5e6c8' : accent} r={0.5 + (i % 3) * 0.1} />
        ))}
        <mesh position={[0, 0, 0]} rotation={[f / 90, f / 140, 0]}>
          <sphereGeometry args={[1.05, 32, 32]} />
          <meshPhysicalMaterial color="#0e3d4a" roughness={0.08} metalness={0.45} clearcoat={1} transmission={0.35} />
        </mesh>
        {[0, 1, 2].map((k) => (
          <mesh key={`r${k}`} rotation={[Math.PI / 2.4 + k * 0.55, f * 0.013 * (k + 1), 0]} position={[0, -0.1, 0]}>
            <torusGeometry args={[2.9 + k * 1.2, 0.026, 10, 128]} />
            <meshBasicMaterial color={k === 0 ? accent : k === 1 ? '#c9a86a' : '#7fb2ff'} transparent opacity={0.5} />
          </mesh>
        ))}
      </ThreeCanvas>
      <AbsoluteFill style={{ background: 'radial-gradient(ellipse at 50% 42%,transparent 40%,#04121acc 100%)' }} />
      {labels.slice(0, 3).map((t, i) => {
        const at = Math.round(fps * (1.1 + i * 1.4));
        return (
          <div key={i} style={{ position: 'absolute', bottom: 330 - i * 86, right: 76, left: 300,
            display: 'flex', justifyContent: 'flex-start', opacity: M(f, at, at + 14),
            translate: `${M(f, at, at + 18, 52, 0)}px 0` }}>
            <span style={{ fontSize: 34, lineHeight: 1.5, color: '#eef7f5', fontWeight: 700,
              background: '#04121ae8', borderRight: `4px solid ${accent}`, padding: '10px 18px' }}>{t}</span>
          </div>);
      })}
      <div style={{ position: 'absolute', bottom: 96, left: 76, right: 76, display: 'flex', justifyContent: 'space-between',
        fontSize: 20, color: '#8fb0b4', opacity: M(f, 20, 40) }}>
        <span>نموذج ثلاثي الأبعاد للمبدأ</span>
        <span style={{ color: accent }}>ليس قياسًا حقيقيًا</span>
      </div>
    </AbsoluteFill>);
};
