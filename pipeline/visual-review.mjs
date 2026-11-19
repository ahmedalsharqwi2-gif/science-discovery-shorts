import path from 'node:path';import {partialReview} from './render.mjs';import {json} from './io.mjs';
const out=path.resolve('out/visual-followup');const result=await partialReview(out,await json('config/channel.json'),{reason:'NARRATION_PROVIDER_NOT_AVAILABLE_FOR_LOCAL_REVIEW'});console.log(JSON.stringify(result));
