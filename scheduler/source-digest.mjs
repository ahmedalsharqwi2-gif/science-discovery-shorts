import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
export async function sourceDigest(base = new URL('.', import.meta.url)) {
  const digest = createHash('sha256');
  for (const name of ['worker.mjs','core.mjs','schedule-policy.mjs','deploy.mjs','source-digest.mjs','wrangler.json','package-lock.json','../config/remotion_daily_release.json']) digest.update(name + '\0').update(await readFile(new URL(name, base)));
  return digest.digest('hex');
}
