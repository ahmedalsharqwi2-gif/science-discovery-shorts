// Shared 1080x1920 subtitle area: clear of bottom account UI and right controls.
export const CAPTION_SAFE={left:70,right:890,bottom:1572,baseline:1530,font:46};
export function captionLayout(context,text){
 const words=String(text).trim().split(/\s+/).filter(Boolean);
 let size=CAPTION_SAFE.font,rows=[];
 do{
  context.font=`700 ${size}px Noto`;rows=[''];
  for(const word of words){const last=rows.length-1,test=(rows[last]+' '+word).trim();if(rows[last]&&context.measureText(test).width>CAPTION_SAFE.right-CAPTION_SAFE.left)rows.push(word);else rows[last]=test;}
  if(rows.length<=3||size<=32)break;size-=2;
 }while(true);
 const lineHeight=Math.ceil(size*1.39),firstBaseline=CAPTION_SAFE.baseline-(rows.length-1)*lineHeight;
 return {rows,size,lineHeight,firstBaseline,centerX:(CAPTION_SAFE.left+CAPTION_SAFE.right)/2,panel:{x:CAPTION_SAFE.left-14,y:firstBaseline-size*.9,width:CAPTION_SAFE.right-CAPTION_SAFE.left+28,height:(rows.length-1)*lineHeight+size*1.8}};
}
export function drawCaption(context,text,color='#f1f0df'){
 if(!String(text).trim())return;
 const box=captionLayout(context,text);context.save();
 context.fillStyle='rgba(2,10,18,.88)';context.beginPath();context.roundRect(box.panel.x,box.panel.y,box.panel.width,box.panel.height,18);context.fill();
 context.font=`700 ${box.size}px Noto`;context.textAlign='center';context.direction='rtl';context.textBaseline='middle';context.lineJoin='round';context.lineWidth=5;context.strokeStyle='rgba(0,0,0,.9)';context.fillStyle=color;
 box.rows.forEach((row,i)=>{const y=box.firstBaseline+i*box.lineHeight;context.strokeText(row,box.centerX,y);context.fillText(row,box.centerX,y);});context.restore();
}
