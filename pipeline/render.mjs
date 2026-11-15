import path from 'node:path';import {mkdir,writeFile} from 'node:fs/promises';
import {bundle} from '@remotion/bundler';import {selectComposition,renderMedia,renderStill} from '@remotion/renderer';
import {layoutQA} from './layout-qa.mjs';
import {run,save,probe} from './io.mjs';import {verifyBrand} from './brand.mjs';
export async function renderEpisode(props,out,{filename='review.mp4'}={}){
 await mkdir(out,{recursive:true});await verifyBrand();
 const serveUrl=await bundle({entryPoint:path.resolve('src/index.tsx'),publicDir:path.resolve('public')});
 const browserExecutable=process.env.CHROME_PATH||undefined,chromiumOptions={gl:'swangle'};
 const composition=await selectComposition({serveUrl,id:'Episode',inputProps:props,browserExecutable,chromiumOptions});
 await renderMedia({serveUrl,composition,inputProps:props,codec:'h264',outputLocation:path.join(out,filename),concurrency:Number(process.env.RENDER_CONCURRENCY||2),x264Preset:'veryfast',browserExecutable,chromiumOptions});
 await renderStill({serveUrl,composition,inputProps:props,frame:45,output:path.join(out,'thumbnail.png'),browserExecutable,chromiumOptions});
 await run('ffmpeg',['-y','-v','error','-i',path.join(out,filename),'-vf','fps=1/3,scale=180:320,tile=6x10','-frames:v','1',path.join(out,'contact-sheet.jpg')],{timeout:180000});
 return {file:path.join(out,filename),thumbnail:path.join(out,'thumbnail.png'),contactSheet:path.join(out,'contact-sheet.jpg')};
}
export async function visualQA(out,filename,{incomplete=false}={}){
 const logo=await verifyBrand(),media=await probe(path.join(out,filename)),v=media.streams.find(s=>s.codec_type==='video');
 const geometry=Boolean(v&&v.width===1080&&v.height===1920&&v.r_frame_rate==='30/1'&&Number(media.format.duration)>=90&&Number(media.format.duration)<=180);
 if(!geometry)throw Error('VISUAL_REVIEW_MEDIA_CONTRACT_FAILED');
 await run(process.env.PYTHON||'python',['pipeline/visual_qa.py',path.resolve(out,'thumbnail.png'),path.resolve('brand/logo'),path.resolve('config/logo.json'),path.resolve(out,'logo-render-qa.json')],{timeout:30000});
 const ocr=await run('tesseract',[path.join(out,'thumbnail.png'),'stdout','-l','eng'],{timeout:30000}).then(r=>r.stdout).catch(()=>null);
 const banned=ocr!==null&&/made\s*with\s*manus|shutterstock|alamy|istock|storyblocks/i.test(ocr);if(banned)throw Error('FOREIGN_WATERMARK_TEXT_DETECTED');
 const result={width:v.width,height:v.height,fps:30,duration:Number(media.format.duration),geometryPassed:geometry,logo:{...logo,renderedPixelsChecked:true},watermark:{knownTextScan:ocr===null?'unavailable':'no_known_foreign_watermark_detected',assetPolicy:'Only original vectors, owner-supplied immutable logos and documented generated backgrounds; listening/visual approval remains separate.'},audioRequired:!incomplete,complete:!incomplete,approved:false};
 await save(path.resolve(out,'visual-qa.json'),result);return result;
}
export async function partialReview(out,config,{episode,reason='PROVIDER_UNAVAILABLE'}={}){
 const templates=['phenomenon','comparison','steps','journey','map','chart','cause','phenomenon'];
 const safeScenes=templates.map((template,i)=>({title:['نبدأ بسؤال واضح','نقارن الفكرة ببساطة','خطوة ورا خطوة','كل مشهد بيكمل اللي قبله','نرتب التفاصيل بصريًا','نوضح العلاقة بين العناصر','نفهم السبب والنتيجة','نرجع للسؤال الأول'][i],text:'',summary:'معاينة بصرية غير مكتملة — بدون صوت',keyword:'معاينة',template,labels:['البداية','الفكرة','النتيجة'],values:[],kind:'illustration',expression:i,action:['walk','run','jump','fall','point','turn','hang','sleep'][i]}));
 const actual=episode?.scenes?.length?episode.scenes:safeScenes;
 const scenes=actual.map(s=>({...s,duration:96/actual.length,words:[],background:undefined}));
 const props={title:episode?.title||config.name+' — معاينة بصرية',editorialLabel:episode?.editorialLabel||null,scenes,durationInFrames:2880,preview:true,incomplete:true};
 await save(path.resolve(out,'visual-preview-props.json'),props);await layoutQA(props,out);const result=await renderEpisode(props,out,{filename:'visual-preview-incomplete.mp4'});const qa=await visualQA(out,'visual-preview-incomplete.mp4',{incomplete:true});
 await save(path.resolve(out,'INCOMPLETE.json'),{incomplete:true,published:false,reason,narration:false,wordAlignment:false,storySource:episode?'actual authored script from failed review attempt':'original template demonstration, not an editorial episode',qa});
 await writeFile(path.join(out,'README-INCOMPLETE.md'),'# معاينة بصرية غير مكتملة\n\nفيديو بدون صوت أو محاذاة كلمات، ولا يُعد حلقة جاهزة للنشر. سبب تعذر المراجعة الكاملة: `'+reason+'`. الشعار من الملف الأصلي ببصمته المسجّلة.\n');return {...result,incomplete:true};
}
