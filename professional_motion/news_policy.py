"""Fresh, consequential AI news with clearly separated Egyptian meme commentary."""
import copy,json,re
from datetime import datetime,timedelta,timezone
REACTIONS={'shock','suspicious','loading','smug'}
RANK={'type':'OBJECT','properties':{'selected':{'type':'ARRAY','maxItems':6,'items':{'type':'OBJECT','properties':{'index':{'type':'INTEGER'},'importance':{'type':'INTEGER'},'reason':{'type':'STRING'}},'required':['index','importance','reason']}}},'required':['selected']}

def published_at(row):
    value=datetime.fromisoformat(str(row.get('published','')).replace('Z','+00:00'))
    if value.tzinfo is None:raise ValueError('News publication date must include a timezone')
    return value.astimezone(timezone.utc)

def require_fresh(row,now=None):
    now=now or datetime.now(timezone.utc);published=published_at(row)
    if not now-timedelta(hours=48)<=published<=now+timedelta(minutes=5):raise ValueError('AI news must have a verified publication date within the last 48 hours')
    return published

def choose(rows,ask,now=None):
    now=now or datetime.now(timezone.utc);fresh=[]
    for row in rows:
        try:published=require_fresh(row,now)
        except (ValueError,TypeError):continue
        # Six hours of freshness headroom for rendering and the 17:00 slot.
        if published<now-timedelta(hours=42):continue
        fresh.append(row)
    if not fresh:return []
    data=[{'index':i,'title':r['title'],'publisher':r['publisher'],'published':r['published'],'summary':r.get('summary','')[:650]} for i,r in enumerate(fresh)]
    result=ask('Select up to SIX genuinely consequential fresh AI news developments for a broad Egyptian audience. Prefer major model/tool releases, meaningful new capabilities, access or pricing changes, important hardware or safety developments. Reject generic explainers, event reminders, marketing roundups, minor promo posts and rehashed old announcements. importance is an editorial relevance score from 1 to 5, NOT a benchmark; select only 4 or 5. Return only real supplied indices; no invented news. Empty selected is correct if no substantial news. DATA:\n'+json.dumps(data,ensure_ascii=False),RANK)
    selected=[];seen=set()
    for pick in result.get('selected',[]):
        index=pick.get('index');score=pick.get('importance')
        if isinstance(index,bool) or not isinstance(index,int) or not 0<=index<len(fresh) or score not in (4,5) or index in seen:continue
        seen.add(index);selected.append({**fresh[index],'news_selection':{'importance':score,'reason':pick['reason']}})
    return sorted(selected,key=lambda r:(r['news_selection']['importance'],r['published']),reverse=True)

def schema(base):
    s=copy.deepcopy(base);scene=s['properties']['scenes']['items'];scene['properties'].update(punchline={'type':'STRING'},reaction={'type':'STRING','enum':['none',*sorted(REACTIONS)]});scene['required']+=['punchline','reaction'];return s

def validate_memes(story):
    jokes=[]
    for scene in story['scenes']:
        joke=scene.get('punchline','').strip();reaction=scene.get('reaction','none')
        if not joke:
            if reaction!='none':raise ValueError('A meme reaction needs an actual spoken punchline')
            continue
        if not 2<=len(joke.split())<=7 or joke not in scene['narration']:raise ValueError('Meme punchlines must be 2–7 words copied verbatim from the spoken narration')
        if reaction not in REACTIONS:raise ValueError('Use a supported original meme reaction')
        jokes.append(re.sub(r'[^\u0621-\u064a ]','',joke))
    if len(set(jokes))<4:raise ValueError('AI news needs at least four distinct, topic-specific Egyptian punchlines')

PROMPT=('For NEWS ONLY: make this a fresh factual AI NEWS + EGYPTIAN MEMES video, not a solemn generic tech explainer. Every scene adds a concrete source-backed part of THIS news. Include a short topical spoken punchline in at least FOUR scenes, copied verbatim to punchline; reaction is shock/suspicious/loading/smug, or none with an empty punchline in a serious scene. '
        'Use original Egyptian jokes about the specific capability, price, access or limitation discussed; no recycled laptop jokes, no generic motivational hype. Aim for 260–330 spoken words total, eight naturally varied paragraphs of 24–48 words, for a two-minute story. The jokes are clearly narrator commentary, never fabricated facts, quotes, prices, benchmarks, victims or product guarantees. A funny exaggeration must be obviously humorous. Never call an old announcement new or say today unless its supplied dated source is actually today. ')
