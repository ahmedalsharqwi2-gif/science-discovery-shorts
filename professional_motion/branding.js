// Per-channel original logo, loaded before any frame is captured.
export async function loadBranding(profile){
 const response=await fetch('./branding.json');if(!response.ok)return null;
 const config=await response.json();if(config.profile!==profile)throw Error('Brand logo belongs to another channel');
 if(!config.enabled)return null;
 if(!/^\.\/assets\/brand\/[a-zA-Z0-9_.-]+\.(png|jpe?g|webp)$/.test(config.image))throw Error('Invalid local channel logo path');
 const image=new Image();image.src=config.image;
 try{await image.decode();}catch{if(config.required)throw Error('Required channel logo is unavailable');return null;}
 return image;
}
export function drawBranding(ctx,image){
 if(!image)return;
 const x=72,y=42,size=140,padding=5;
 ctx.save();ctx.beginPath();ctx.roundRect(x,y,size,size,20);ctx.clip();
 ctx.fillStyle='rgba(2,10,19,.92)';ctx.fillRect(x,y,size,size);
 const scale=Math.min((size-padding*2)/image.naturalWidth,(size-padding*2)/image.naturalHeight);
 const w=image.naturalWidth*scale,h=image.naturalHeight*scale;
 ctx.imageSmoothingEnabled=true;ctx.imageSmoothingQuality='high';ctx.drawImage(image,x+(size-w)/2,y+(size-h)/2,w,h);ctx.restore();
}
