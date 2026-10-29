"""Fresh, consequential AI news with clearly separated Egyptian meme commentary."""
import copy,json,re
from .style_warnings import note
from datetime import datetime,timedelta,timezone
REACTIONS={'shock','suspicious','loading','smug'}
RANK={'type':'OBJECT','properties':{'selected':{'type':'ARRAY','maxItems':6,'items':{'type':'OBJECT','properties':{'index':{'type':'INTEGER'},'importance':{'type':'INTEGER'},'reason':{'type':'STRING'}},'required':['index','importance','reason']}}},'required':['selected']}

def published_at(row):
    value=datetime.fromisoformat(str(row.get('published','')).replace('Z','+00:00'))
    if value.tzinfo is None:raise ValueError('News publication date must include a timezone')
    return value.astimezone(timezone.utc)

def require_fresh(row,now=None):
    now=now or datetime.now(timezone.utc);published=published_at(row)
    if now.tzinfo is None:raise ValueError('News review clock must include a timezone')
    if not now-timedelta(hours=48)<=published<=now+timedelta(minutes=5):raise ValueError('AI news must have a verified publication date within the last 48 hours')
    return published

def choose(rows,ask,now=None):
    now=now or datetime.now(timezone.utc);fresh=[];urls=set()
    for row in rows:
        try:published=require_fresh(row,now)
        except (ValueError,TypeError):continue
        # Twelve hours of freshness headroom cover 09:00 preparation, 17:00 Cairo publication and processing.
        if published<now-timedelta(hours=36):continue
        if not row.get('url') or row['url'] in urls:continue
        urls.add(row['url'])
        fresh.append(row)
    if not fresh:return []
    data=[{'index':i,'title':r['title'],'publisher':r['publisher'],'published':r['published'],'summary':r.get('summary','')[:650]} for i,r in enumerate(fresh)]
    result=ask('Select up to SIX genuinely consequential fresh AI news developments for a broad Egyptian audience. Prefer major model/tool releases, meaningful new capabilities, access or pricing changes, substantial new research or reproducible benchmarks, important hardware or safety developments. Reject generic explainers, event reminders, marketing roundups, minor promo posts, customer success stories without an actual new development, and rehashed old announcements. importance is an editorial relevance score from 1 to 5, NOT a benchmark; select only 4 or 5. Return only real supplied indices; no invented news. Empty selected is correct if no substantial news. DATA:\n'+json.dumps(data,ensure_ascii=False),RANK)
    selected=[];seen=set()
    for pick in result.get('selected',[]):
        if not isinstance(pick,dict):continue
        index=pick.get('index');score=pick.get('importance')
        if isinstance(index,bool) or not isinstance(index,int) or not 0<=index<len(fresh) or not isinstance(score,int) or isinstance(score,bool) or score not in (4,5) or index in seen or not isinstance(pick.get('reason'),str) or not pick['reason'].strip():continue
        seen.add(index);selected.append({**fresh[index],'news_selection':{'importance':score,'reason':pick['reason']}})
    return sorted(selected,key=lambda r:(r['news_selection']['importance'],r['published']),reverse=True)

def schema(base):
    s=copy.deepcopy(base);scene=s['properties']['scenes']['items'];scene['properties'].update(punchline={'type':'STRING'},reaction={'type':'STRING','enum':['none',*sorted(REACTIONS)]});scene['required']+=['punchline','reaction'];return s

def validate_memes(story):
    jokes=[]
    for scene in story['scenes']:
        joke=scene.get('punchline','').strip();reaction=scene.get('reaction','none')
        if not joke:
            if reaction!='none':note(story,'A reaction without a spoken punchline was omitted');scene['reaction']='none'
            continue
        if not 2<=len(joke.split())<=7:note(story,'Prefer concise spoken meme punchlines')
        if joke not in scene['narration']:
            note(story,'An optional meme phrase absent from the narration was omitted');scene['punchline']='';scene['reaction']='none';continue
        # A substring inside an Arabic prefixed word cannot be timed as a
        # separately spoken word. Recover the exact spoken span instead.
        from .alignment import norm
        wanted=[norm(w) for w in joke.split()];spoken=scene['narration'].split();span=None
        for start in range(len(spoken)-len(wanted)+1):
            actual=[norm(w) for w in spoken[start:start+len(wanted)]]
            if actual[1:]==wanted[1:] and actual[0] in (wanted[0],'و'+wanted[0],'ف'+wanted[0]):
                span=' '.join(spoken[start:start+len(wanted)]);break
        if span is None:
            note(story,'An optional meme effect without complete spoken word anchors was omitted');scene['punchline']='';scene['reaction']='none';continue
        scene['punchline']=span;joke=span
        if reaction not in REACTIONS:note(story,'An unsupported optional reaction was omitted');scene['reaction']='none'
        key=' '.join(norm(w) for w in joke.split())
        key=re.sub(r'^[وف](?=ال|ده\b|دي\b|مش\b|ايه\b)','',key)
        jokes.append(key)
    if len(set(jokes))<4:note(story,'Editorial suggestion: add more distinct topic-specific Egyptian punchlines')

PROMPT=('For NEWS ONLY: make this a fresh factual AI NEWS + EGYPTIAN MEMES video, not a solemn generic tech explainer. Every scene adds a concrete source-backed part of THIS news. Include a short topical spoken punchline in at least FOUR scenes, copied verbatim to punchline; reaction is shock/suspicious/loading/smug, or none with an empty punchline in a serious scene. '
        'Prefer punchlines of four to seven simple spoken words so at least two words can be independently recognized and timed. Copy complete script words, including a leading و or ف when spoken. Use original Egyptian jokes about the specific capability, price, access or limitation discussed; no recycled laptop jokes, no generic motivational hype. Aim for 260–330 spoken words total, eight naturally varied paragraphs of 24–48 words, for a two-minute story. The jokes are clearly narrator commentary, never fabricated facts, quotes, prices, benchmarks, victims or product guarantees. A funny exaggeration must be obviously humorous. Never call an old announcement new or say today unless its supplied dated source is actually today. ')
