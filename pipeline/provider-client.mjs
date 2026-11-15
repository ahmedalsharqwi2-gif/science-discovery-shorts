import {readFile} from 'node:fs/promises';import {GeminiClient} from './gemini.mjs';
let singleton;
export async function provider(){if(!singleton){const config=JSON.parse(await readFile('config/gemini.json','utf8'));singleton=new GeminiClient({config,keyFor:kind=>kind==='voice'?(process.env.GEMINI_TTS_API_KEY||process.env.GEMINI_API_KEY):kind==='image'?(process.env.GEMINI_IMAGE_API_KEY||process.env.GEMINI_API_KEY||process.env.GEMINI_TEXT_API_KEY):(process.env.GEMINI_TEXT_API_KEY||process.env.GEMINI_API_KEY)});}return singleton;}
export function providerDiagnostics(){return singleton?{events:singleton.events,resolvedModels:Object.fromEntries(singleton.resolved)}:{events:[],resolvedModels:{}};}
