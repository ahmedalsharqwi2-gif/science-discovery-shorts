export function drawOctopus(ctx,time,accent){
const x=ctx;const C={ink:"#0A0A0B",bone:"#EEE9DF",orange:"#FF4D12",ember:"#FF8A3D",teal:"#58C9B8",blue:"#68A9D2",purple:"#B68AE6"};
function tentacle(cx,cy,idx,t,pal){const ang=-Math.PI/2+idx*Math.PI/4+Math.sin(t*.7+idx)*.11;const len=390+(idx%3)*40;const ex=cx+Math.cos(ang)*len,ey=cy+Math.sin(ang)*len;const bend=idx%2?1:-1;const cp1x=cx+Math.cos(ang+.48*bend)*len*.48,cp1y=cy+Math.sin(ang+.48*bend)*len*.48;const cp2x=cx+Math.cos(ang-.36*bend)*len*.8,cp2y=cy+Math.sin(ang-.36*bend)*len*.8;x.beginPath();x.moveTo(cx,cy);x.bezierCurveTo(cp1x,cp1y,cp2x,cp2y,ex,ey);x.lineCap='round';x.lineJoin='round';x.strokeStyle='#28292b';x.lineWidth=70-(idx%3)*7;x.stroke();x.beginPath();x.moveTo(cx,cy);x.bezierCurveTo(cp1x,cp1y,cp2x,cp2y,ex,ey);x.strokeStyle=pal;x.globalAlpha=.72;x.lineWidth=36-(idx%3)*3;x.stroke();x.globalAlpha=1;for(let j=1;j<8;j++){const q=j/9,px=(1-q)**3*cx+3*(1-q)**2*q*cp1x+3*(1-q)*q*q*cp2x+q**3*ex,py=(1-q)**3*cy+3*(1-q)**2*q*cp1y+3*(1-q)*q*q*cp2y+q**3*ey;for(let k=0;k<3;k++){const side=k-1,ox=Math.cos(ang+Math.PI/2)*side*18,oy=Math.sin(ang+Math.PI/2)*side*18;x.beginPath();x.arc(px+ox,py+oy,7+(1-q)*2,0,Math.PI*2);x.fillStyle=k===1?C.bone:'#151517';x.globalAlpha=.68;x.fill();x.globalAlpha=1}}}
function octopus(t,mode){const cx=540,cy=790,primary=mode===0?C.orange:mode===1?C.teal:mode===2?C.purple:C.ember;const palette=[primary,mode===0?C.ember:mode===1?C.blue:C.teal];x.save();x.translate(0,Math.sin(t*1.3)*10);x.shadowColor=primary;x.shadowBlur=42;for(let i=0;i<8;i++)tentacle(cx,cy+80,i,t,palette[i%2]);x.shadowBlur=0;
// mantle
x.beginPath();x.ellipse(cx,cy-95,194,234,0,Math.PI,Math.PI*2);x.quadraticCurveTo(cx+190,cy+100,cx,cy+120);x.quadraticCurveTo(cx-190,cy+100,cx-194,cy-95);x.fillStyle='#343638';x.fill();x.strokeStyle=primary;x.lineWidth=5;x.stroke();
// chromatophore spots animate open/close
for(let i=0;i<34;i++){const a=i*2.399,rad=30+(i%7)*22,px=cx+Math.cos(a)*rad,py=cy-110+Math.sin(a)*rad*.88;const pulse=.5+.5*Math.sin(t*3+i*1.7);const r=5+pulse*(i%4===0?14:7);x.beginPath();x.ellipse(px,py,r*1.2,r*.78,Math.sin(a),0,Math.PI*2);x.fillStyle=i%3===0?C.orange:i%3===1?C.teal:C.purple;x.globalAlpha=.28+pulse*.55;x.fill();x.globalAlpha=1}
// eyes
for(const dx of [-62,62]){x.beginPath();x.ellipse(cx+dx,cy-20,31,38,0,0,Math.PI*2);x.fillStyle=C.bone;x.fill();x.beginPath();x.ellipse(cx+dx+(dx<0?3:-3),cy-17,11,23,0,0,Math.PI*2);x.fillStyle=C.ink;x.fill();x.beginPath();x.arc(cx+dx+(dx<0?6:-6),cy-25,4,0,Math.PI*2);x.fillStyle='#fff';x.fill()}
x.restore();return primary}

octopus(time,Math.floor(time/5)%3);
}
