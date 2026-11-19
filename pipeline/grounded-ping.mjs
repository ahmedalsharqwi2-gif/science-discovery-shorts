// One-shot grounding capability check: asserts the project key pool returns
// Google Search grounding chunks. Run before the first staging run that
// relies on the grounded topics fallback: node pipeline/grounded-ping.mjs
import {provider} from './provider-client.mjs';
import {assertGrounding} from './grounded-topics.mjs';
const chunks=await assertGrounding(await provider());
console.log('GROUNDING_PING_OK chunks='+chunks);
