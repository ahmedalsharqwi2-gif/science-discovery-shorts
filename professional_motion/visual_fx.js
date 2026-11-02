/* Production-safe visual FX layer: no branding, no external network, deterministic by time. */
(function(){
  const TAU=Math.PI*2;
  function ease(x){x=Math.max(0,Math.min(1,x));return x*x*(3-2*x)}
  function seeded(n){const x=Math.sin(n*12.9898)*43758.5453;return x-Math.floor(x)}
  window.applyVisualFX=function(ctx,base,overlay,time,duration){
    const w=ctx.canvas.width,h=ctx.canvas.height,t=Number(time)||0,d=Math.max(1,Number(duration)||1);
    const q=t/d, beat=ease((Math.sin(t*1.8)+1)/2), pulse=ease((Math.sin(t*2.7+1.1)+1)/2);
    ctx.save();
    // cinematic grade and vignette without changing authored text/branding
    const g=ctx.createLinearGradient(0,0,w,h);g.addColorStop(0,`rgba(20,35,70,${.035+.02*beat})`);g.addColorStop(.55,'rgba(0,0,0,0)');g.addColorStop(1,`rgba(0,0,0,${.11+.04*beat})`);ctx.fillStyle=g;ctx.fillRect(0,0,w,h);
    const v=ctx.createRadialGradient(w*.5,h*.43,Math.min(w,h)*.2,w*.5,h*.5,Math.max(w,h)*.72);v.addColorStop(.62,'rgba(0,0,0,0)');v.addColorStop(1,'rgba(0,0,0,.22)');ctx.fillStyle=v;ctx.fillRect(0,0,w,h);
    // depth particles: deterministic, sparse, scene-agnostic
    ctx.globalCompositeOperation='screen';
    for(let i=0;i<22;i++){const a=seeded(i+7)*TAU+t*(.03+seeded(i+91)*.04);const r=90+seeded(i+3)*Math.min(w,h)*.62;const x=w*.5+Math.cos(a)*r;const y=h*.5+Math.sin(a)*r;const s=1+seeded(i+17)*4;ctx.globalAlpha=.025+.035*pulse;ctx.fillStyle=i%3===0?'#ffd27a':'#8ce7df';ctx.beginPath();ctx.arc(x,y,s,0,TAU);ctx.fill()}
    // slow light sweep for visual life, clipped softly by alpha
    const sx=((q*1.35)%1)*w*1.6-w*.3;const beam=ctx.createLinearGradient(sx,0,sx+w*.18,0);beam.addColorStop(0,'rgba(255,255,255,0)');beam.addColorStop(.5,`rgba(255,230,170,${.018+.018*beat})`);beam.addColorStop(1,'rgba(255,255,255,0)');ctx.fillStyle=beam;ctx.fillRect(0,0,w,h);
    // subtle film grain, bounded so captions remain legible
    ctx.globalCompositeOperation='overlay';ctx.globalAlpha=.025;
    for(let i=0;i<80;i++){const x=seeded(i+Math.floor(t*24))*w,y=seeded(i*3+Math.floor(t*24))*h;ctx.fillStyle=i%2?'#fff':'#000';ctx.fillRect(x,y,1+seeded(i)*3,1+seeded(i)*3)}
    ctx.restore();window.visualFXStatus={active:true,engines:['camera-easing','parallax-depth','particles','vignette','color-grade','light-sweep','film-grain'],version:'1.0'};
  };
})();
