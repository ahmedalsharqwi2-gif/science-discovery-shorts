import {verifyBrand} from './brand.mjs';
export function requireGeminiBindings(env=process.env,{needText=true,needVoice=true}={}){
 const missing=[];if(needText&&!env.GEMINI_API_KEY&&!env.GEMINI_TEXT_API_KEY)missing.push('GEMINI_API_KEY');if(needVoice&&!env.GEMINI_API_KEY&&!env.GEMINI_TTS_API_KEY)missing.push('GEMINI_TTS_API_KEY');
 if(missing.length){const e=Error('MISSING_REPOSITORY_SECRET_'+missing[0]);e.missingBindings=[...new Set(missing)];e.recommendedBinding='GEMINI_API_KEY';throw e;}
 return {configured:true,textRequired:needText,voiceRequired:needVoice};
}
export async function preflight({root=process.cwd(),env=process.env,needText=true,needVoice=true}={}){const logo=await verifyBrand(root);const bindings=requireGeminiBindings(env,{needText,needVoice});return {logo,bindings};}
