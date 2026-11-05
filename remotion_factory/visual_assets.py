"""Bounded, licensed Commons images with actual metadata; never invented URLs."""
import hashlib,html,io,json,re
from pathlib import Path
from urllib.parse import urlparse
import requests
from PIL import Image
LICENSES=('Public domain','CC0','CC BY-SA 4.0','CC BY-SA 3.0','CC BY 4.0','CC BY 3.0')
HOSTS={'upload.wikimedia.org','commons.wikimedia.org','thumb.wikimedia.org'}
HEADERS={'User-Agent':'ArabicDocumentaryFactory/2.0 (licensed educational video; source credits retained)'}
def clean(value):return re.sub(r'<[^>]*>',' ',html.unescape(value or '')).strip()
def tokens(value):return {w for w in re.findall('[a-z0-9]+',value.lower()) if len(w)>2 and w not in {'the','and','file','jpg','png','jpeg','history','mystery','ancient','with','from','its'}}
def choose(query,pages):
 required=tokens(query);ranked=[]
 for page in pages:
  info=(page.get('imageinfo') or [{}])[0];m=info.get('extmetadata',{});license=clean(m.get('LicenseShortName',{}).get('value',''));text=page.get('title','')+' '+clean(m.get('ImageDescription',{}).get('value',''))
  matched=len(required&tokens(text));minimum=1 if len(required)==1 else min(2,len(required))
  if not required or matched<minimum or license not in LICENSES:continue
  url=info.get('thumburl') or info.get('url','')
  if urlparse(url).scheme!='https' or urlparse(url).hostname not in HOSTS or info.get('mime','').lower() not in ('image/jpeg','image/png','image/webp','image/svg+xml'):continue
  ranked.append((matched,page,info,m,license,url))
 if not ranked:return None
 _,page,info,m,license,url=max(ranked,key=lambda r:r[0]);return {'query':query,'title':page['title'],'url':url,'page':info.get('descriptionurl'),'artist':clean(m.get('Artist',{}).get('value',''))[:400],'description':clean(m.get('ImageDescription',{}).get('value',''))[:1400],'license':license,'license_url':m.get('LicenseUrl',{}).get('value'),'representation':'archival subject image; may show a different date, never claimed as footage of the narrated event'}
def resolve(query,cache):
 key=hashlib.sha256(query.casefold().encode()).hexdigest()[:20];proof=cache/(key+'.json');image=cache/(key+'.jpg')
 if proof.exists():
  saved=json.loads(proof.read_text())
  if saved.get('available') and image.exists() and hashlib.sha256(image.read_bytes()).hexdigest()==saved['sha256']:return saved,image
  if not saved.get('available'):return saved,None
 try:
  response=requests.get('https://commons.wikimedia.org/w/api.php',params={'action':'query','format':'json','generator':'search','gsrsearch':query,'gsrnamespace':6,'gsrlimit':8,'prop':'imageinfo','iiprop':'url|extmetadata|mime','iiurlwidth':1800},headers=HEADERS,timeout=25);response.raise_for_status();selected=choose(query,list(response.json().get('query',{}).get('pages',{}).values()))
  if not selected:raise ValueError('No related, clearly licensed image returned')
  with requests.get(selected['url'],headers=HEADERS,timeout=35,stream=True) as r:
   r.raise_for_status()
   if urlparse(r.url).hostname not in HOSTS:raise ValueError('Unexpected media redirect')
   parts=[];size=0
   for part in r.iter_content(65536):
    size+=len(part)
    if size>12_000_000:raise ValueError('Image exceeds bounded size')
    parts.append(part)
  raw=b''.join(parts)
  with Image.open(io.BytesIO(raw)) as im:
   if min(im.size)<600 or max(im.size)>12000:raise ValueError('Image resolution outside bounds')
   im=im.convert('RGB');im.thumbnail((2200,2200));im.save(image,quality=94)
  saved={**selected,'available':True,'sha256':hashlib.sha256(image.read_bytes()).hexdigest(),'original_download_sha256':hashlib.sha256(raw).hexdigest(),'alterations':'JPEG conversion, crop, camera movement and color treatment; no fabricated event imagery'}
 except (requests.RequestException,ValueError,OSError) as e:saved={'query':query,'available':False,'reason':type(e).__name__+': '+str(e)[:180]}
 proof.write_text(json.dumps(saved,ensure_ascii=False,indent=2)+'\n');return saved,image if saved['available'] else None
def enrich(story,plan,public,delivery):
 cache=delivery/'visual-assets';cache.mkdir(exist_ok=True,parents=True);evidence=[];queries={};profile=story['profile']
 for i,scene in enumerate(plan['scenes']):
  if scene.get('asset') or not scene.get('image_query') or profile=='stickman':continue
  if scene.get('legacy_kind')=='map' or scene['shot_type'] in ('reconstruction','chronology','macro','process','comparison','takeaway','workflow'):continue
  # Three bounded lookups per episode; a repeated query reuses the same bytes.
  query=scene['image_query'].strip()
  if query not in queries and len(queries)>=3:continue
  if query not in queries:queries[query]=resolve(query,cache)
  proof,image=queries[query];evidence.append({'scene':scene['id'],**proof})
  if image:
   name='identity-media/'+image.name;target=public/name;target.parent.mkdir(exist_ok=True,parents=True);target.write_bytes(image.read_bytes());scene.update(asset=name,asset_label='صورة للموضوع • '+proof['license'],asset_representation=proof['representation'],asset_sha256=proof['sha256'])
  else:scene['asset_unavailable']=proof['reason'];scene['representation']='تصوّر توضيحي للموضوع • ليس توثيقًا مصورًا للحدث'
 return evidence
