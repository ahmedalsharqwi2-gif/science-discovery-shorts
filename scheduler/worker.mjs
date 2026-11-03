import {DurableObject} from 'cloudflare:workers';
import {handleGate, handleRequest, scheduledTick} from './core.mjs';
export class DailyGate extends DurableObject {
  async fetch(request) { return handleGate(request, this.ctx.storage, this.env); }
}
export default {
  scheduled(controller, env, ctx) { ctx.waitUntil(scheduledTick(controller, env)); },
  fetch: handleRequest
};
