export function science(c,s,t,{accent,text}){
 const seed=s.seed??0;
 for(let i=0;i<16;i++){
  const a=i*2.399+seed*.13,r=65+(i%5)*65,x=540+Math.cos(a)*r,y=880+Math.sin(a)*r;
  const pulse=.5+.5*Math.sin(t*1.6+i),radius=22+pulse*18;
  c.beginPath();c.arc(x,y,radius+14,0,Math.PI*2);c.strokeStyle=accent+'55';c.lineWidth=2;c.stroke();c.beginPath();c.arc(x,y,radius,0,Math.PI*2);c.fillStyle=i%3===0?'#ec8457':accent;c.globalAlpha=.45+pulse*.4;c.fill();c.globalAlpha=1;
  if(s.kind==='signal'){c.beginPath();c.moveTo(540,880);c.lineTo(x,y);c.strokeStyle='#8ec8e266';c.stroke();const q=(t*.35+i*.1)%1;c.beginPath();c.arc(540+(x-540)*q,880+(y-880)*q,7,0,7);c.fillStyle='#e9debd';c.fill();}
 }
 if(s.kind==='layers')for(let j=0;j<7;j++){c.beginPath();for(let x=180;x<=900;x+=10){const y=1170+j*24+Math.sin(x/100+t+j)*15;if(x===180)c.moveTo(x,y);else c.lineTo(x,y);}c.strokeStyle=['#5acbbb','#86afe2','#cf94d1'][j%3];c.lineWidth=4;c.stroke();}
 text(s.visual_label??'رسم توضيحي',540,1380,28,'#a5bdc2',400);
}
