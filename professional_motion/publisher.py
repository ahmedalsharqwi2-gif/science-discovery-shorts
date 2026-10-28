"""Conditional, receipt-backed publication at an absolute 17:00 Cairo slot."""
import hashlib,json,os,shutil
from datetime import datetime,timezone
from pathlib import Path
from scripts.daily_schedule import next_slot,validate_slot
from film_factory.publish import channels,query,norm
from film_factory.metadata import BRANDS
from film_factory.buffer import ContentPublisher
from scripts.publication_state import require_services,accepted_receipt,confirm_stock
from .editorial import registry,save
ROOT=Path(__file__).resolve().parent
POLICY=Path('config/professional_release.json')


def approved():
    p=json.loads(POLICY.read_text()) if POLICY.exists() else {}
    return p.get('publication_approved') is True and p.get('style_approved') is True and bool(p.get('approved_sample_sha256'))


def verified_mapping(profile,rows):
    services={'tiktok','youtube','facebook','instagram'}
    by_id={r['id']:r for r in rows}
    explicit={s:os.getenv('BUFFER_'+s.upper()+'_CHANNEL_ID','').strip() for s in services}
    explicit={k:v for k,v in explicit.items() if v}
    raw=os.getenv('BUFFER_CHANNEL_IDS','').strip();legacy=[]
    if raw:
        try:parsed=json.loads(raw)
        except ValueError:parsed=raw.split(',')
        if isinstance(parsed,dict):explicit.update({str(k).lower():str(v) for k,v in parsed.items()})
        else:
            for value in parsed:
                value=str(value).strip()
                if ':' in value and value.split(':',1)[0].lower() in services:
                    service,identifier=value.split(':',1);explicit[service.lower()]=identifier
                elif value:legacy.append(value)
    selected={}
    def accept(row,service=None):
        actual=row.get('service','').lower()
        if actual not in services or (service and actual!=service) or row.get('isQueuePaused') or not any(norm(BRANDS[profile]) in norm(row.get(k,'')) for k in ('name','displayName')):
            raise ValueError('Connected destination does not match this repository brand/service')
        if actual in selected and selected[actual]!=row['id']:raise ValueError('Ambiguous destination; configure an explicit channel ID')
        selected[actual]=row['id']
    for service,identifier in explicit.items():
        if identifier not in by_id:raise ValueError('Configured channel is not connected')
        accept(by_id[identifier],service)
    for identifier in legacy:
        if identifier not in by_id:raise ValueError('Configured channel is not connected')
        accept(by_id[identifier])
    if not explicit and not legacy:
        for row in rows:
            if any(norm(BRANDS[profile]) in norm(row.get(k,'')) for k in ('name','displayName')):accept(row)
    return selected


def preflight(profile,strict=False):
    result={'buffer':{},'direct_youtube':False,'problems':[],'credential_presence':{n:bool(os.getenv(n)) for n in ('BUFFER_API_KEY','YT_CLIENT_ID','YT_CLIENT_SECRET','YT_REFRESH_TOKEN','YT_REFRESH_TOKEN_FALLBACK')}}
    if os.getenv('BUFFER_API_KEY'):
        try:
            rows=[]
            for org in query('query { account { organizations { id name } } }')['account']['organizations']:
                rows+=query('query { channels(input: {organizationId: '+json.dumps(org['id'])+'}) { id name displayName service isQueuePaused } }')['channels']
            result['available_channels']=[{'name':r.get('displayName') or r.get('name'),'service':r.get('service'),'id':r.get('id'),'paused':r.get('isQueuePaused')} for r in rows]
            selected=verified_mapping(profile,rows)
            result['buffer']=selected
            result['matched_channels']=[{'name':r.get('displayName') or r.get('name'),'service':r['service'],'id':r['id']} for r in rows if r['id'] in selected.values()]
        except Exception as e:result['problems'].append({'provider':'buffer','error_class':type(e).__name__})
    direct=all(os.getenv(k) for k in ('YT_CLIENT_ID','YT_CLIENT_SECRET')) and bool(os.getenv('YT_REFRESH_TOKEN') or os.getenv('YT_REFRESH_TOKEN_FALLBACK'))
    if direct:
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            valid=None
            for token in dict.fromkeys([os.getenv('YT_REFRESH_TOKEN'),os.getenv('YT_REFRESH_TOKEN_FALLBACK')]):
                if not token:continue
                try:
                    c=Credentials(None,refresh_token=token,token_uri='https://oauth2.googleapis.com/token',client_id=os.environ['YT_CLIENT_ID'],client_secret=os.environ['YT_CLIENT_SECRET']);c.refresh(Request())
                    rows=build('youtube','v3',credentials=c).channels().list(part='snippet',mine=True).execute().get('items',[])
                    if len(rows)!=1 or norm(BRANDS[profile]) not in norm(rows[0]['snippet']['title']):raise ValueError('YouTube channel does not match repository brand')
                    valid=rows[0];break
                except Exception:continue
            if not valid:raise ValueError('Direct YouTube credentials could not verify the intended channel')
            result.update(direct_youtube=True,youtube_channel={'id':valid['id'],'title':valid['snippet']['title']});result['buffer'].pop('youtube',None)
        except Exception as e:result['problems'].append({'provider':'youtube','error_class':type(e).__name__})
    if not result['buffer'] and not result['direct_youtube']:result['problems'].append({'provider':'destinations','error_class':'NoVerifiedDestination'})
    (ROOT/'delivery').mkdir(exist_ok=True);(ROOT/'delivery/publishing-preflight.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    if strict and result['problems']:raise RuntimeError('Publishing destinations are not verified; see safe preflight report')
    return result


def publish(profile,slot,due):
    if not approved():raise PermissionError('Publication awaits the user’s review of this channel sample')
    validate_slot(due)
    data=registry();episode=next(r for r in data['episodes'] if r['slot']==slot)
    story=episode['story'];video=ROOT/'output/professional-review.mp4';report=json.loads((ROOT/'output/verification.json').read_text())
    if episode.get('status') not in ('rendered','publishing','scheduled'):raise ValueError('Only a rendered episode can be scheduled')
    if story['topic_key']!=report.get('topic_key') or report['audio_tail'].get('audio_tail_checked') is not True:raise ValueError('Final topic or speech verification missing')
    if hashlib.sha256(video.read_bytes()).hexdigest()!=episode.get('video_sha256'):raise ValueError('Rendered video changed after validation')
    destinations=preflight(profile,True)
    os.environ.update(PUBLISH_DUE_AT=due,PUBLISH_IMMEDIATE='false',PUBLICATION_RECEIPTS_ENABLED='true',BUFFER_SCHEDULE_MODE='customScheduled',PRODUCTION_MEDIA_ID=slot)
    out=Path('output');out.mkdir(exist_ok=True);Path('state').mkdir(exist_ok=True)
    title=(BRANDS[profile]+' | '+story['title'])[:100]
    tags={'science':['علوم','اكتشافات'],'history':['تاريخ','هندسة'],'horror':['غموض','وقائع_موثقة'],'news':['ذكاء_اصطناعي','اخبار_التقنية']}[profile]
    caption=title+'\nرسوم ثلاثية الأبعاد لإعادة الشرح؛ ليست تسجيلًا للأحداث.\nالمصدر: '+story['source']['publisher']+'\n'+story['source']['url']+'\n'+' '.join('#'+x for x in tags)
    metadata={**story,'title':title,'caption':caption,'tags':tags};Path('state/current_episode.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2));shutil.copy2(video,out/'final_video_full.mp4')
    mapping=destinations['buffer'];required=set(mapping)|({'youtube'} if destinations['direct_youtube'] else set());require_services(required)
    episode['status']='publishing';save(data)
    errors=[]
    if mapping:
        os.environ.update(BUFFER_CHANNEL_IDS=','.join(k+':'+v for k,v in mapping.items()),PUBLISH_CHANNELS=','.join(mapping))
        if not ContentPublisher().publish_to_buffer(out/'final_video_full.mp4',title,caption,[]):errors.append('Buffer did not confirm every destination')
    if destinations['direct_youtube']:
        from scripts.publish_youtube_direct import main as upload
        if upload()!=0:errors.append('YouTube did not confirm acceptance')
    if errors:raise RuntimeError('; '.join(errors))
    os.environ['BUFFER_OUTCOME']='success'
    if destinations['direct_youtube']:os.environ['YOUTUBE_OUTCOME']='success'
    confirm_stock();episode.update(status='scheduled',due_at=due,receipts={s:accepted_receipt(s) for s in required});save(data)
    (ROOT/'output/publication-result.json').write_text(json.dumps({'due_at':due,'scheduled':True,'receipts':episode['receipts']},indent=2))
