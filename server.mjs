import express from 'express';import {timingSafeEqual} from 'node:crypto';import {review} from './pipeline/run.mjs';
export function app(){
 const a=express();a.disable('x-powered-by');a.use(express.json({limit:'100kb'}));a.get('/health',(_,r)=>r.json({ok:true,publish_enabled:false}));
 a.use('/api',(req,res,next)=>{const key=process.env.API_TOKEN||'';const actual=Buffer.from(req.headers.authorization||''),expected=Buffer.from('Bearer '+key);if(key.length<32||actual.length!==expected.length||!timingSafeEqual(actual,expected))return res.status(401).json({error:'UNAUTHORIZED'});next();});
 a.post('/api/youtube/upload',(_,res)=>res.status(403).json({error:'PUBLICATION_DISABLED',privacy:'private',manualApprovalRequired:true}));
 let busy=false;a.post('/api/render',async(_,res)=>{if(busy)return res.status(409).json({error:'RENDER_BUSY'});busy=true;try{res.json(await review());}catch{res.status(422).json({error:'REVIEW_FAILED',diagnostics:'out/*/report.json'});}finally{busy=false;}});
 a.use((_,r)=>r.status(404).json({error:'NOT_FOUND'}));return a;
}
if(process.argv[1]?.endsWith('/server.mjs'))app().listen(Number(process.env.PORT||8080),'0.0.0.0');
