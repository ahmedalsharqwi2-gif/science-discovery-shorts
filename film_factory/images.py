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

MODEL = os.getenv('FILM_IMAGE_MODEL','@cf/black-forest-labs/flux-2-klein-4b')
REVISION = 'portrait-photography-review-v3'
PORTRAIT_MODEL='@cf/black-forest-labs/flux-2-klein-4b'
if MODEL not in (PORTRAIT_MODEL,'@cf/black-forest-labs/flux-1-schnell'):raise ValueError('Image model has not been configured for this pipeline')

class CloudflareUnavailable(RuntimeError):pass

def decoded_image(response):
    if response.status_code != 200:
        try:errors=response.json().get('errors',[])
        except ValueError:errors=[]
        codes=','.join(str(e.get('code','unknown')) for e in errors if isinstance(e,dict))
        quota=any(re.search(r'neuron|daily|allocation|quota',str(e.get('message','')),re.I) for e in errors if isinstance(e,dict))
        Path('output').mkdir(exist_ok=True)
        Path('output/image-provider-status.json').write_text(json.dumps({'http_status':response.status_code,'error_codes':codes,'quota_message':quota,'paid_fallback_used':False}))
        raise CloudflareUnavailable(f'Cloudflare image HTTP {response.status_code}; codes={codes}; quota_message={quota}. No paid fallback.')
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
        if MODEL==PORTRAIT_MODEL and (im.width<1080 or im.height<1900 or im.width>=im.height):raise ValueError('Portrait provider returned the wrong resolution or orientation')
        return im.convert('RGB')

def photo_prompts(plan,cache):
    world=plan['visual_world']
    prompts=[world+' '+s['image_prompt']+' Full-scale lifelike location photography, not a miniature set or a video-game render. Natural exposure, weathered real materials, plausible anatomy, restrained color. One clear focal subject and foreground-to-background depth. Compose directly for a vertical 9:16 frame. No text, diagrams, logos, plastic-looking surfaces or fake evidence.' for s in plan['scenes']]
    if any(len(p)>2048 for p in prompts):raise ValueError('Photographic direction exceeds provider prompt limit; shorten the scene description explicitly')
    return prompts

def request_image(account,token,prompt):
    kwargs={'files':{k:(None,str(v)) for k,v in {'prompt':prompt,'width':1088,'height':1920}.items()}} if MODEL==PORTRAIT_MODEL else {'json':{'prompt':prompt,'steps':8}}
    return requests.post(f'https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{MODEL}',headers={'Authorization':'Bearer '+token},timeout=180,**kwargs)

def prepare_images(plan):
    if plan.get('visual_mode')=='reviewed_public_domain_archive' and plan.get('topic_id')=='nyos-cameroon-1986-documented':
        from film_factory.nyos_archive import prepare_archive
        return prepare_archive(plan)
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
            response=request_image(account,token,prompt)
            im=decoded_image(response)
            temporary=target.with_suffix('.tmp');im.save(temporary,format='JPEG',quality=95);temporary.replace(target)
        with Image.open(target) as im:dimensions=list(im.size)
        public=Path('output/images')/f'scene-{index+1:02}.jpg';public.parent.mkdir(exist_ok=True);shutil.copyfile(target,public)
        paths.append(public)
        records.append({'scene':index,'file':str(public),'prompt':prompt,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'dimensions':dimensions,'cache_hit':hit,'provider':'Cloudflare Workers AI','model':MODEL,'steps':4 if MODEL==PORTRAIT_MODEL else 8,'source_url':plan['source']['url'],'illustration_not_evidence':True})
        print(f'Cloudflare scene {index+1}/{len(prompts)} ready; cached={hit}',flush=True)
        Path('output/image_manifest.json').write_text(json.dumps({'revision':REVISION,'images':records,'completed':len(records)==len(prompts)},ensure_ascii=False,indent=2))
    return paths
