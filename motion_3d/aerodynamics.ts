import type * as THREE from 'three';
import {Scene, type Frame} from '../engine/scene';
import {FSPass} from '../engine/gl';

// Fully procedural aerodynamic cutaway. All movement is evaluated at absolute time.
const frag=`
uniform float uTime;
float seg(vec2 p,vec2 a,vec2 b){vec2 v=b-a;return length(p-a-v*clamp(dot(p-a,v)/dot(v,v),0.,1.));}
vec3 glow(vec3 col,float d,float w){return col*(w/(d*d+0.0006));}
void main(){
 vec2 uv=vUv, p=(uv-.5)*vec2(1.77778,1.); float t=uTime;
 vec3 col=mix(vec3(.011,.018,.037),vec3(.006,.043,.069),uv.y);
 // deep technical grid, kept in perspective
 float grid=min(abs(fract((p.x+.03)*20.)-.5),abs(fract(p.y*20.)-.5));
 col+=vec3(.012,.032,.042)*(1.-smoothstep(.01,.035,grid));
 // velocity stream ribbons bend over upper cambered surface
 for(int i=0;i<22;i++){
  float yy=(float(i)-10.5)*.058;
  float x=p.x; float bump=exp(-pow((x-.02)/.42,2.));
  float y=yy+.20*bump*exp(-max(0.,yy)*1.1)+.06*bump*min(0.,yy);
  float d=abs(p.y-y);
  float a=smoothstep(-.96,-.72,x)*(1.-smoothstep(.78,1.03,x));
  float stripe=pow(.5+.5*sin((x-t*.45)*30.+float(i)*2.5),10.);
  col+=a*vec3(.05,.35,.48)*exp(-d*160.)*(.16+.72*stripe);
 }
 // cross section of cambered airfoil, smoothly shaded metal rather than line icon
 float x=p.x/.60; float inside=step(-1.,x)*step(x,1.);
 float chord=(x+1.)*.5;
 float thick=.22*(.2969*sqrt(max(chord,.0001))-.126*chord-.352*pow(chord,2.)+.284*pow(chord,3.)-.1015*pow(chord,4.));
 thick=max(.005,thick)*2.1;
 float camber=.045*(1.-x*x);
 float signedD=abs(p.y-camber)-thick;
 float body=(1.-smoothstep(-.009,.01,signedD))*inside;
 float rim=exp(-abs(signedD)*260.)*inside;
 vec3 metal=mix(vec3(.16,.29,.34),vec3(.78,.85,.81),smoothstep(-.06,.12,p.y+cos(x*2.)*.09));
 col=mix(col,metal,body);
 col+=vec3(.42,.81,.88)*rim*.38;
 // pressure / flow tracer spheres
 for(int j=0;j<30;j++){
   float id=float(j);
   float xx=mod(t*.31+id*.091,2.4)-1.2;
   float lane=(mod(id*7.,13.)-6.)*.075;
   float yy=lane+.20*exp(-pow((xx-.02)/.42,2.))*exp(-max(0.,lane));
   float d=length((p-vec2(xx,yy))*vec2(1.,1.25));
   col+=vec3(.01,.31,.42)*exp(-d*185.)*.75;
 }
 // air pressure glow over upper surface
 col+=vec3(.0,.09,.17)*exp(-pow((p.y-.29)/.12,2.))*exp(-pow(p.x/.59,2.));
 // corner vignetting and filmic contrast
 col*=1.-.47*dot(uv-.5,uv-.5);
 col=col/(1.+col);
 fragColor=vec4(col,1.);
}`;
export default class Aerodynamics extends Scene {
 pass = new FSPass(frag,{uTime:{value:0}});
 override render(f:Frame,out:THREE.WebGLRenderTarget){this.pass.mat.uniforms.uTime.value=f.t;this.pass.render(this.ctx.renderer,out);return {};}
 override dispose(){this.pass.mat.dispose();}
}
