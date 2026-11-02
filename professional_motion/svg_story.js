/** Authored SVG diagrams complement the Three.js worlds; never infer facts or dates. */
export function validateDiagram(scene){
 const d=scene.diagram;if(d==null)return null;
 if(!['flow','timeline','comparison'].includes(d.kind)||!Array.isArray(d.nodes)||d.nodes.length<2||d.nodes.length>5)throw Error('SVG diagram needs a supported kind and two to five authored nodes');
 for(const node of d.nodes){if(typeof node.label!=='string'||node.label.length>42||!scene.narration.includes(node.label))throw Error('SVG node labels must be short exact phrases from this narration');}
 return d;
}
const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[c]));
export function diagramSvg(diagram,progress){
 const n=diagram.nodes.length,active=Math.min(n-1,Math.floor(Math.max(0,Math.min(.999,progress))*n));
 const comparison=diagram.kind==='comparison';const w=900,h=1040;
 const gap=comparison?440:Math.min(190,820/(n-1));
 const positions=diagram.nodes.map((_,i)=>comparison?{x:i%2?675:225,y:180+Math.floor(i/2)*285}:{x:450,y:110+i*gap});
 let content=`<rect x="2" y="2" width="896" height="1036" rx="38" fill="#102936" stroke="#43616d" stroke-width="3"/>`;
 if(!comparison)for(let i=0;i<n-1;i++){const a=positions[i],b=positions[i+1];content+=`<path d="M${a.x} ${a.y+55} L${b.x} ${b.y-55}" stroke="${i<active?'#65d6bd':'#59717a'}" stroke-width="8" marker-end="url(#arrow)"/>`;}
 diagram.nodes.forEach((node,i)=>{const p=positions[i],width=comparison?390:760;content+=`<g><rect x="${p.x-width/2}" y="${p.y-53}" width="${width}" height="106" rx="22" fill="${i===active?'#256c70':'#193e4b'}" stroke="${i===active?'#a2f4d5':'#44616c'}" stroke-width="${i===active?5:2}"/><text x="${p.x}" y="${p.y+12}" text-anchor="middle" direction="rtl" unicode-bidi="plaintext" font-family="sans-serif" font-weight="700" font-size="${comparison?29:34}" fill="#eef8ef">${escape(node.label)}</text></g>`;});
 return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0L8 4L0 8Z" fill="#65d6bd"/></marker></defs>${content}</svg>`;
}
export async function createSvgScenes(story){
 const frames=await Promise.all(story.scenes.map(async scene=>{
  const d=validateDiagram(scene);if(!d)return null;
  return Promise.all(d.nodes.map((_,i)=>new Promise((resolve,reject)=>{
   const url=URL.createObjectURL(new Blob([diagramSvg(d,(i+.5)/d.nodes.length)],{type:'image/svg+xml'}));
   const image=new Image();image.onload=()=>{URL.revokeObjectURL(url);resolve(image);};image.onerror=()=>{URL.revokeObjectURL(url);reject(Error('SVG diagram rasterization failed'));};image.src=url;
  })));
 }));
 return {count:frames.filter(Boolean).length,draw(ctx,index,progress){const list=frames[index];if(!list)return;const active=Math.min(list.length-1,Math.floor(Math.max(0,Math.min(.999,progress))*list.length));ctx.drawImage(list[active],90,420,900,1040);}};
}
