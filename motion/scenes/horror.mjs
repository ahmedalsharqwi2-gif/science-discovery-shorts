export function horror(c,s,t,{accent,text}){
 const flicker=Math.sin(t*21)+Math.sin(t*37)>1.85?.55:1;c.save();c.globalAlpha=flicker;
 c.fillStyle='#17252b';c.beginPath();c.moveTo(70,500);c.lineTo(365,650);c.lineTo(365,1260);c.lineTo(70,1500);c.fill();c.fillStyle='#122027';c.beginPath();c.moveTo(1010,500);c.lineTo(715,650);c.lineTo(715,1260);c.lineTo(1010,1500);c.fill();
 c.fillStyle='#11191d';c.fillRect(370,650,340,610);c.strokeStyle='#625549';c.lineWidth=4;c.strokeRect(370,650,340,610);c.fillStyle='#d6ddbb';c.fillRect(450,530,180,9);
 const reveal=s.kind==='reveal'?Math.min(1,t/5):s.kind==='shadow'?.5+.2*Math.sin(t*.8):0;
 if(reveal){c.fillStyle='#020305';c.fillRect(710-130*reveal,655,130*reveal,600);c.save();c.translate(610,1050);c.scale(.5+reveal,.5+reveal);c.beginPath();c.ellipse(0,-200,30,45,0,0,7);c.fill();c.beginPath();c.moveTo(-35,-155);c.lineTo(35,-155);c.lineTo(70,80);c.lineTo(-65,80);c.fill();c.restore();}
 c.strokeStyle='#465052';c.lineWidth=1;for(let i=0;i<7;i++){c.beginPath();c.moveTo(540,1250);c.lineTo(-500+i*350,1600);c.stroke();}
 c.restore();for(let i=0;i<22;i++){const x=(i*113+Math.sin(t*.2+i)*15)%1080,y=520+(i*157-t*(6+i%7))%950;c.fillStyle='#a5c5bf35';c.fillRect(x,y,2,2);}
 if(s.number)text(s.number,540,730,38,accent);
}
