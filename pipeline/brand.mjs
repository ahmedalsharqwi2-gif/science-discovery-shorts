import {readFile,realpath} from 'node:fs/promises';import {createHash} from 'node:crypto';import path from 'node:path';
export const sha256=b=>createHash('sha256').update(b).digest('hex');
export async function verifyBrand(root=process.cwd()){
 const cfg=JSON.parse(await readFile(path.join(root,'config/logo.json'),'utf8'));
 if(!/^brand\/logo\/logo\.(png|jpe?g)$/.test(cfg.path)||!/^[a-f0-9]{64}$/.test(cfg.sha256))throw Error('INVALID_LOGO_MANIFEST');
 const original=path.join(root,cfg.path),bytes=await readFile(original);if(sha256(bytes)!==cfg.sha256)throw Error('LOGO_HASH_MISMATCH');
 const publicAlias=path.join(root,'public',cfg.path);if(await realpath(publicAlias)!==await realpath(original))throw Error('LOGO_MUST_USE_CANONICAL_SOURCE');
 return {path:cfg.path,sha256:cfg.sha256,bytes:bytes.length,original:true};
}
