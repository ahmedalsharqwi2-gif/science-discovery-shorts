import test from 'node:test';import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {validatePlan,drawFrame} from '../engine.mjs';
const {createCanvas,GlobalFonts}=createRequire(import.meta.url)('@napi-rs/canvas');
const sample=(channel='science',kind='cells')=>({channel,title:'عنوان عربي',duration:4,scenes:[{kind,start:0,end:4}],captions:[{start:0,end:3,text:'نص متزامن مع الصوت'}]});
test('refuses changed narration length and non-finite duration',()=>{assert.throws(()=>validatePlan(sample(),4.4),/mismatch/);assert.throws(()=>validatePlan({...sample(),duration:NaN}),/Duration/);assert.throws(()=>validatePlan({...sample(),duration:181}),/Duration/);});
test('refuses gaps, overlaps and cross-channel scenes',()=>{for(const scenes of [[{kind:'cells',start:1,end:4}],[{kind:'cells',start:0,end:3},{kind:'cells',start:2,end:4}],[{kind:'corridor',start:0,end:4}]])assert.throws(()=>validatePlan({...sample(),scenes}));});
test('refuses captions outside audio and overlapping captions',()=>{assert.throws(()=>validatePlan({...sample(),captions:[{start:0,end:5,text:'كلام'}]}));assert.throws(()=>validatePlan({...sample(),captions:[{start:0,end:2,text:'أ'},{start:1,end:3,text:'ب'}]}));});
test('historical routes require explicit data and schematic label',()=>{assert.throws(()=>validatePlan(sample('history','route')),/coordinates/);const p=sample('history','route');p.scenes[0].points=[[0,.5],[1,.5]];assert.throws(()=>validatePlan(p),/schematic/);p.scenes[0].schematic=true;assert.equal(validatePlan(p),p);});
test('each channel renders different content and changes over time',()=>{
 const cases=[sample(),sample('history','artifact'),sample('horror','reveal'),sample('science','octopus'),sample('science','concept')],hashes=[];
 for(const p of cases){validatePlan(p,4);const c=createCanvas(360,640),x=c.getContext('2d');drawFrame(x,p,.5,{width:360,height:640});const a=c.toBuffer('image/png');drawFrame(x,p,2,{width:360,height:640});const b=c.toBuffer('image/png');assert.notDeepEqual(a,b);hashes.push(a);}
 assert.notDeepEqual(hashes[0],hashes[1]);assert.notDeepEqual(hashes[1],hashes[2]);
});
test('Arabic wrapping keeps long labels within renderable layout',()=>{const p=sample();p.captions[0].text='هذه جملة عربية طويلة لاختبار التفاف الكلمات والحفاظ على تشكيلها داخل المساحة الآمنة';const c=createCanvas(720,1280);assert.doesNotThrow(()=>drawFrame(c.getContext('2d'),p,1,{width:720,height:1280}));assert.throws(()=>drawFrame(c.getContext('2d'),p,4),/outside/);});
