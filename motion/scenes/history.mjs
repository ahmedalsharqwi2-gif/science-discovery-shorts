export function history(c,s,t,{accent,text}){
 const q=Math.min(1,t/Math.min(3,s.end-s.start));c.strokeStyle=accent;c.lineWidth=4;
 if(s.kind==='timeline'){
  c.beginPath();c.moveTo(230,600);c.lineTo(230,600+700*q);c.stroke();
  s.events.forEach((e,i)=>{const y=650+i*600/Math.max(1,s.events.length-1);if(y>600+700*q)return;c.beginPath();c.arc(230,y,12,0,7);c.fillStyle=accent;c.fill();text(e.date,400,y-30,38,accent);text(e.label,655,y+30,36,'#eee9df',500,560);});
 }else if(s.kind==='artifact'){
  c.save();c.translate(540,950);c.rotate(Math.sin(t*.25)*.025);c.fillStyle='#302b23';c.fillRect(-260,-340,520,650);c.strokeStyle='#ad8b58';c.strokeRect(-260,-340,520,650);
  for(let j=0;j<7;j++){c.beginPath();c.moveTo(-200,-230+j*70);c.lineTo(100+(j%3)*30,-230+j*70);c.strokeStyle='#917b5866';c.lineWidth=3;c.stroke();}c.restore();text(s.artifact_label??'وثيقة توضيحية',540,1370,32,accent);
 }else{
  c.strokeStyle='#766f59';c.lineWidth=1;for(let i=0;i<8;i++){c.beginPath();c.moveTo(160+i*110,570);c.lineTo(160+i*110,1300);c.stroke();c.beginPath();c.moveTo(150,580+i*100);c.lineTo(930,580+i*100);c.stroke();}
  const pts=s.points.map(([x,y])=>[170+x*740,600+y*640]);c.beginPath();pts.forEach(([x,y],i)=>i?c.lineTo(x,y):c.moveTo(x,y));c.setLineDash([12,9]);c.strokeStyle=accent;c.lineWidth=4;c.stroke();c.setLineDash([]);const j=Math.min(pts.length-2,Math.floor(q*(pts.length-1))),f=q*(pts.length-1)-j;const a=pts[j],b=pts[j+1];c.beginPath();c.arc(a[0]+(b[0]-a[0])*f,a[1]+(b[1]-a[1])*f,12,0,7);c.fillStyle=accent;c.fill();text('مسار تخطيطي؛ ليس خريطة جغرافية',540,1390,26,'#b9aa8b');
 }
}
