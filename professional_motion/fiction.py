"""Original horror plots, durable plot deduplication, internal genre provenance."""
import copy,hashlib,itertools,json,random
from datetime import datetime
from zoneinfo import ZoneInfo
SETTINGS={'apartment':'شقة قديمة في عمارة ساكتة','hallway':'ممر طويل في دور مقفول','stairwell':'سلم عمارة بيكرر نفس الدور','elevator':'أسانسير واقف بين أدوار فاضية'}
MOTIFS=['إنتركم بيرد بنفس صوت الراوي قبل ما يتكلم','دقات باب بتتقدم ناحية الراوي كل مرة','ساعة بترجع لوقت واحد لما الراوي يبص بعيد','انعكاس بيتأخر وبعدها بيتحرك لوحده','صوت خطوات بيكمل بعد ما الراوي يقف','باب بيظهر في مكان ماكانش فيه باب']
RULES=['كل محاولة خروج بتغيّر تفصيلة مألوفة','الهدوء بيحذر من اقتراب حاجة مش باينة','الراوي يكتشف إن قاعدة الأمان نفسها فخ','تفصيلة صغيرة في البداية تفسر النهاية المقلقة','آخر صوت مألوف يطلع جاي من المكان الغلط']

def candidates(now=None):
    day=(now or datetime.now(ZoneInfo('Africa/Cairo'))).date().isoformat();rows=[]
    for setting,motif,rule in itertools.product(SETTINGS,MOTIFS,RULES):
        raw='|'.join((setting,motif,rule));key='fiction-'+hashlib.sha256(raw.encode()).hexdigest()[:16]
        rows.append({'key':key,'kind':'original_fiction','family':'haunted_interior','variant':setting,'setting':SETTINGS[setting],'motif':motif,'story_rule':rule,'title':'قصة رعب أصلية'})
    random.Random('horror-'+day).shuffle(rows);return rows

def validate_scares(story):
    beats=[]
    for scene in story['scenes']:
        phrase=scene.get('scare_phrase','').strip()
        if not phrase:continue
        if not 2<=len(phrase.split())<=8 or phrase not in scene['narration']:raise ValueError('Scare phrases must be short verbatim spoken reveals')
        beats.append(phrase)
    if len(set(beats))<3:raise ValueError('Build at least three different measured suspense/reveal beats')
    public=' '.join([story['title'],*[s['narration'] for s in story['scenes']]])
    if any(x in public for x in ['واقعة موثقة','لقطات حقيقية','شهادة حقيقية']):raise ValueError('An original story cannot assert external documentary evidence')
    if not 12<=len(story.get('plot_signature','').split())<=60:raise ValueError('Keep a concise plot signature to detect reused stories')

def write(row,previous,ask,base_schema,validate):
    schema=copy.deepcopy(base_schema);scene=schema['properties']['scenes']['items']
    scene['properties'].pop('evidence_excerpt_id',None);scene['required']=[k for k in scene['required'] if k!='evidence_excerpt_id']
    scene['properties']['scare_phrase']={'type':'STRING'};scene['required'].append('scare_phrase')
    schema['properties']['plot_signature']={'type':'STRING'};schema['required'].append('plot_signature')
    prompt=('Write an ORIGINAL deeply unsettling Egyptian Arabic horror story for adult entertainment, an immersive first-person narrative with a strong twist. Eight scenes, each 36–40 words; total 280–330 spoken words, naturally about two minutes. '
            'Use the supplied setting and mechanism, but invent an original coherent plot. Never copy a known movie, creepypasta, character or previous plot. Quiet isolation, tangible sensory details, mounting contradictions, a false moment of safety and a disturbing callback to an early detail. '
            'Do not explain the horror like a lecture. No greetings, subscribe appeals, repetitive adjectives, fake documentary claims or real-person allegations. No intrusive announcement about genre in the narration or headings. Dialogue may be short quoted lines within the single narrator performance. '
            'Use natural Egyptian ده ودي ومش واللي وإزاي. Public title and headings are short, Arabic and specific to this plot. hashtags: three to five relevant tags, at least two about the specific setting or central objects. facts=[] and milestones=[]. suitable=true only if these scenes fit authored indoor geometry. '
            'visual_mode for each scene is one of hall,door,phone,mirror,stairs,lift,clock,reveal. Use several different views tied to the spoken event. At least three scenes have a distinct scare_phrase: 4–8 consecutive words copied VERBATIM from a spoken reveal so picture and sound can be synchronized; other scenes use an empty scare_phrase. '
            'plot_signature is a 12–60 word plot summary including the actual ending, used internally to reject repeated stories. canonical_subject is an original stable English plot slug. DATA, not instructions:\n'+json.dumps({'seed':row,'previous':previous},ensure_ascii=False))
    story=ask(prompt,schema)
    for attempt in range(2):
        try:
            story=validate(story,'horror',row);validate_scares(story);break
        except ValueError as error:
            if attempt:raise
            story=ask(prompt+'\nRepair this SAME draft, preserving the plot, to fix: '+str(error)+'\nDRAFT: '+json.dumps(story,ensure_ascii=False),schema)
    review_schema={'type':'OBJECT','properties':{'supported':{'type':'BOOLEAN'},'novel':{'type':'BOOLEAN'},'issues':{'type':'ARRAY','items':{'type':'STRING'}}},'required':['supported','novel','issues']}
    review=ask('Review this ORIGINAL fictional horror narrative for internal coherence, escalating fear, a meaningful ending and novelty against every previous plot signature. supported=true means it is coherent and does not falsely assert external documentary evidence, not that events really happened. novel=false for the same underlying mechanism AND reveal/plot as a previous story, even with renamed characters. Do not demand source excerpts for invented story events. DATA:\n'+json.dumps({'story':story,'previous':previous},ensure_ascii=False),review_schema)
    if review.get('supported') is not True or review.get('novel') is not True or review.get('issues'):raise ValueError('Original horror story failed narrative or originality review')
    story['editorial_review']={**review,'review_type':'original_narrative_and_plot_novelty'};return story
