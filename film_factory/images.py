"""Bounded Cloudflare FLUX generation. Credentials never enter files or logs."""
import base64
import hashlib
import io
import json
import os
import re
import shutil
from pathlib import Path
import requests
from PIL import Image
from api_budget import reserve

MODEL = '@cf/black-forest-labs/flux-1-schnell'
REVISION = 'documented-cinema-scenes-v2'

def decoded_image(response):
    if response.status_code != 200:
        raise RuntimeError(f'Cloudflare image HTTP {response.status_code}; check Workers AI token permissions, Account ID and quota. No paid fallback.')
    if 'image/' in response.headers.get('Content-Type',''):
        raw = response.content
    else:
        data = response.json()
        if data.get('success') is False:
            codes = [str(x.get('code','unknown')) for x in data.get('errors',[]) if isinstance(x,dict)]
            raise RuntimeError('Cloudflare rejected image request; codes=' + ','.join(codes))
        result = data.get('result',data)
        if not isinstance(result,dict) or not isinstance(result.get('image'),str):
            raise ValueError('Cloudflare returned no image bytes')
        raw = base64.b64decode(result['image'].split(',')[-1],validate=True)
    with Image.open(io.BytesIO(raw)) as im:
        im.load()
        if min(im.size)<512:raise ValueError('Generated image below minimum resolution')
        return im.convert('RGB')

def photo_prompts(plan,cache):
    world=plan['visual_world']
    return [world+' '+s['image_prompt']+' Cinematic editorial reconstruction, dramatic but realistic practical lighting, 35mm or 85mm lens, layered foreground depth, tactile materials, clear silhouette and strong visual focal point, restrained film grain. Each shot must illustrate the actual narrated action. No generic filler, no fake evidence, no writing or logos, no anachronistic landmarks, plausible geometry and anatomy. Main subject within center 60 percent for vertical crop.' for s in plan['scenes']]

def prepare_images(plan):
    token=os.getenv('CLOUDFLARE_API_TOKEN','').strip();account=os.getenv('CLOUDFLARE_ACCOUNT_ID','').strip()
    if not token or not re.fullmatch(r'[a-fA-F0-9]{32}',account):
        raise RuntimeError('Set CLOUDFLARE_API_TOKEN and the 32-character CLOUDFLARE_ACCOUNT_ID in repository Actions secrets')
    cache=Path('.image_cache');cache.mkdir(exist_ok=True);Path('output').mkdir(exist_ok=True)
    prompts=photo_prompts(plan,cache);records=[];paths=[]
    if not 1<=len(prompts)<=8:raise ValueError('At most eight image requests per episode')
    for index,prompt in enumerate(prompts):
        identity=hashlib.sha256((REVISION+MODEL+prompt).encode()).hexdigest();target=cache/(identity+'.jpg');hit=False
        if target.exists():
            try:
                with Image.open(target) as im:im.verify()
                hit=True
            except (OSError,ValueError):target.unlink()
        if not hit:
            response=requests.post(f'https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{MODEL}',headers={'Authorization':'Bearer '+token},json={'prompt':prompt,'steps':8},timeout=120)
            im=decoded_image(response);temporary=target.with_suffix('.tmp');im.save(temporary,format='JPEG',quality=95);temporary.replace(target)
        with Image.open(target) as im:dimensions=list(im.size)
        public=Path('output/images')/f'scene-{index+1:02}.jpg';public.parent.mkdir(exist_ok=True);shutil.copyfile(target,public)
        paths.append(public)
        records.append({'scene':index,'file':str(public),'prompt':prompt,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'dimensions':dimensions,'cache_hit':hit,'provider':'Cloudflare Workers AI','model':MODEL,'steps':8,'source_url':plan['source']['url'],'illustration_not_evidence':True})
        print(f'Cloudflare scene {index+1}/{len(prompts)} ready; cached={hit}',flush=True)
        Path('output/image_manifest.json').write_text(json.dumps({'revision':REVISION,'images':records,'completed':len(records)==len(prompts)},ensure_ascii=False,indent=2))
    return paths
