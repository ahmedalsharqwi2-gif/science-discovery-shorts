"""Free, rights-filtered image fallback for the four vertical factories.

Stock imagery is never described as AI-generated. Fail closed on no match.
Pexels requires optional PEXELS_API_KEY; Wikimedia uses Commons API.
"""
import hashlib
import io
import os
import re
from pathlib import Path
from urllib.parse import urlparse
import requests
from PIL import Image, ImageOps

def search_terms(prompt):
    # Remove provider style directions to prioritize the actual subject.
    clean=re.split(r'Full-scale lifelike|Compose directly|No text,|Cinematic lighting|photorealistic',prompt,flags=re.I)[0]
    clean=re.sub(r'[^a-zA-Z0-9 ,.-]',' ',clean)
    return ' '.join(clean.split())[:110] or 'science'

def _get_image(url):
    host=urlparse(url).hostname or ''
    if not (host=='images.pexels.com' or host=='upload.wikimedia.org'):
        raise ValueError('Untrusted image CDN host')
    resp=requests.get(url,timeout=35,stream=True)
    resp.raise_for_status()
    if int(resp.headers.get('Content-Length') or 0)>18_000_000:
        raise ValueError('Image too large')
    content=resp.content
    if len(content)>18_000_000:raise ValueError('Image too large')
    with Image.open(io.BytesIO(content)) as im:
        im.load()
        if min(im.size)<500:raise ValueError('Image too small')
        return ImageOps.fit(im.convert('RGB'),(1080,1920),centering=(.5,.5))

def pexels(prompt,cache):
    key=os.getenv('PEXELS_API_KEY','').strip()
    if not key:return None
    q=search_terms(prompt)
    data=requests.get('https://api.pexels.com/v1/search',headers={'Authorization':key},params={'query':q,'per_page':8,'orientation':'portrait'},timeout=25)
    data.raise_for_status()
    for item in data.json().get('photos',[]):
        if not item.get('id') or item.get('width',0)<750 or item.get('height',0)<1100:continue
        src=item.get('src',{}).get('original') or item.get('src',{}).get('large2x')
        if not src:continue
        try:im=_get_image(src)
        except (ValueError,requests.RequestException,OSError):continue
        return im,{'provider':'Pexels','license':'Pexels License','license_url':'https://www.pexels.com/license/',
                   'source_url':item.get('url',''),'creator':item.get('photographer',''),'query':q}
    return None

def commons(prompt,cache):
    q=search_terms(prompt)
    endpoint='https://commons.wikimedia.org/w/api.php'
    params={'action':'query','format':'json','generator':'search','gsrsearch':'filetype:bitmap '+q,
            'gsrnamespace':6,'gsrlimit':12,'prop':'imageinfo','iiprop':'url|extmetadata',
            'iiurlwidth':1400}
    data=requests.get(endpoint,params=params,headers={'User-Agent':'NeurofusionVideoFactory/1.0 (public-domain artwork research)'},timeout=25)
    data.raise_for_status()
    pages=data.json().get('query',{}).get('pages',{})
    for page in pages.values():
        info=(page.get('imageinfo') or [{}])[0]
        meta=info.get('extmetadata',{})
        license_name=re.sub(r'<[^>]+>','',meta.get('LicenseShortName',{}).get('value','')).strip().lower()
        if license_name not in ('public domain','cc0','cc0 1.0'):continue
        source=info.get('thumburl') or info.get('url')
        if not source:continue
        try:im=_get_image(source)
        except (ValueError,requests.RequestException,OSError):continue
        return im,{'provider':'Wikimedia Commons','license':license_name,
                   'license_url':meta.get('LicenseUrl',{}).get('value',''),
                   'source_url':info.get('descriptionurl',''),'creator':'various','query':q}
    return None

def fallback(prompt,cache):
    if os.getenv('FILM_ALLOW_STOCK_FALLBACK','1').lower() not in ('1','true','yes'):return None
    for provider in (pexels,commons):
        try:
            result=provider(prompt,cache)
            if result:return result
        except (requests.RequestException,ValueError,OSError,KeyError) as e:
            print('Fallback provider unavailable: '+provider.__name__+' '+type(e).__name__,flush=True)
    return None
