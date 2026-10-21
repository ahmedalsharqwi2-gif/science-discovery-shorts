"""Approved Charon narration: one full transcript, verified formats, no voice fallback."""
import base64, hashlib, io, json, os, shutil, subprocess, tempfile, time, wave
import urllib.request, urllib.error
from pathlib import Path
from api_budget import reserve
ROOT = Path(__file__).resolve().parent.parent

def config():
    c=json.loads((ROOT/'config/accepted_voice.json').read_text(encoding='utf-8'))
    if (c.get('provider'), c.get('model'), c.get('speaker'), c.get('fallback_allowed')) != ('gemini', 'gemini-3.8-flash-tts', 'Charon', False):
        raise ValueError('Accepted Gemini Charon profile changed; explicit voice approval is required')
    return c

def _wave_info(data):
    with wave.open(io.BytesIO(data)) as w:
        if w.getcomptype()!='NONE' or w.getsampwidth()!=2:
            raise ValueError('Expected PCM16 WAV from Gemini')
        frames=w.getnframes(); rate=w.getframerate(); channels=w.getnchannels()
        if rate<=0 or channels not in (1,2) or frames/rate<.25:
            raise ValueError('Invalid Gemini audio duration or channels')
        if len(w.readframes(frames))!=frames*channels*2:
            raise ValueError('Truncated Gemini WAV data')
        return {'duration':frames/rate, 'sample_rate':rate, 'channels':channels}

def _synthesize(text,c,key):
    payload={'model':c['model'], 'input':[{'type':'user_input','content':[{'type':'text','text':text,'annotations':[{'type':'speech_metadata','style':c['style']}]}]}], 'response_format':{'type':'audio'}, 'generation_config':{'speech_config':[{'voice':c['speaker']}]}}
    for attempt in range(2):
        reserve('tts',c['model'],key)
        req=urllib.request.Request('https://generativelanguage.googleapis.com/v1beta/interactions', data=json.dumps(payload).encode(),headers={'x-goog-api-key':key,'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req,timeout=240) as response:
                raw=json.load(response)
            blocks=[b for s in raw.get('steps',[]) if s.get('type')=='model_output' for b in s.get('content',[]) if b.get('type')=='audio' and b.get('data')]
            if not blocks:
                raise RuntimeError('Gemini returned no audio; no substitute recording or voice is allowed')
            data=base64.b64decode(blocks[-1]['data'],validate=True)
            return data,raw.get('id'),_wave_info(data)
        except urllib.error.HTTPError as exc:
            # Provider bodies may contain credential metadata. Never print them.
            body=exc.read().decode('utf-8','replace').lower()
            daily=any(x in body for x in ('per_day','perday','per day','daily'))
            try: delay=float(exc.headers.get('Retry-After','21'))
            except (TypeError,ValueError): delay=21
            if daily or exc.code not in (429,500,502,503,504) or attempt or delay>45:
                raise RuntimeError(f'Gemini TTS HTTP {exc.code}; task waiting, no replacement voice used') from None
            time.sleep(max(1,delay))
        except (urllib.error.URLError,TimeoutError):
            raise RuntimeError('Gemini TTS connection failed; task retained for retry without changing voice') from None

def generate(text,output_path,performance=None):
    text=' '.join(str(text).split())
    if not text: raise ValueError('Narration is empty')
    output=Path(output_path).resolve()
    if output.suffix.lower() not in ('.wav','.mp3'): raise ValueError('Narration output must be WAV or MP3')
    c=config()
    if performance:c={**c,"style":c["style"]+"\n"+performance}
    key=(os.getenv('GEMINI_TTS_API_KEY') or os.getenv('GEMINI_API_KEY') or '').strip()
    if not key: raise RuntimeError('GEMINI_TTS_API_KEY or GEMINI_API_KEY is required. No replacement voice will be used.')
    cache=Path(os.getenv('VOICE_CACHE_DIR','.voice_cache'));cache.mkdir(parents=True,exist_ok=True)
    ident=hashlib.sha256((hashlib.sha256(key.encode()).hexdigest()+json.dumps(c,sort_keys=True)+text).encode()).hexdigest()
    cached=cache/(ident+'.wav');meta=cached.with_suffix('.json');hit=False
    if cached.exists() and meta.exists():
        data=cached.read_bytes();info=_wave_info(data);report=json.loads(meta.read_text());hit=True
        if report.get('sha256')!=hashlib.sha256(data).hexdigest(): raise ValueError('Voice cache integrity check failed')
    else:
        data,interaction,info=_synthesize(text,c,key)
        report={'provider':'Gemini TTS','model':c['model'],'voice':c['speaker'],'style':c['style'],'text':text,'interaction_id':interaction,**info,'sha256':hashlib.sha256(data).hexdigest(),'newly_synthesized':True,'original_video_audio_used':False,'fallback_used':False}
        with tempfile.NamedTemporaryFile(dir=cache,delete=False) as f:f.write(data);tmp=Path(f.name)
        tmp.replace(cached)
        meta.write_text(json.dumps(report,ensure_ascii=False,indent=2))
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as td:
        target=Path(td)/output.name
        if output.suffix.lower()=='.wav':target.write_bytes(data)
        else:
            subprocess.run(['ffmpeg','-v','error','-y','-i',str(cached),'-c:a','libmp3lame','-b:a','192k',str(target)],check=True)
            length=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(target)]))
            if abs(length-info['duration'])>.15: raise ValueError('Narration encoding lost audio duration')
        target.replace(output)
    output.with_suffix('.source.json').write_text(json.dumps({**report,'cache_hit':hit,'output_sha256':hashlib.sha256(output.read_bytes()).hexdigest()},ensure_ascii=False,indent=2))
    return output
