"""Measured ASR anchors with explicit exact and pronunciation-normalized coverage."""
from difflib import SequenceMatcher
import re


def norm(s):
    return re.sub(r'[^a-z0-9\u0621-\u064a]','',s.lower()).translate(str.maketrans({'أ':'ا','إ':'ا','آ':'ا','ة':'ه','ى':'ي'}))


# Known English loanword spellings recognized by multilingual ASR. This is not
# fuzzy matching or translation of arbitrary words; original ASR files stay raw.
SPOKEN_NAMES={'any':'اني','speech':'سبوتش','recognizer':'ريكوغنايزر','decision':'ديسيشن','model':'موديل','paracate':'باراكيت','parakeet':'باراكيت','nvidia':'انفيديا','alibaba':'اليبابا','streaming':'ستريمنج','sortformer':'سورتفورمر','emoji':'ايموجي','magnet':'ماجنت','studio':'استوديو'}

def recognized_key(text):
    token=re.sub(r'[^a-zA-Z\u0621-\u064a]','',text).lower();prefix=''
    if len(token)>1 and token[0] in 'وف' and re.search('[a-z]',token):prefix,token=token[0],token[1:]
    value=prefix+SPOKEN_NAMES.get(token,token)
    if re.search('[a-z]',value):return 'latin:'+value
    # Egyptian speech commonly realizes ذ as ز; retain the original token too.
    return norm(value).replace('ذ','ز')

def join_recognized_clitics(actual):
    output=[];i=0
    while i<len(actual):
        word=dict(actual[i])
        if word['text'].strip() in ('و','ف') and i+1<len(actual) and 0<=actual[i+1]['start']-word['end']<.3:
            following=actual[i+1];word.update(text=word['text']+following['text'],end=following['end'],source_tokens=[dict(actual[i]),dict(following)]);i+=1
        output.append(word);i+=1
    return output

def anchor_chain(expected,duration,transcripts,key,join=False):
    models=[];candidates={}
    for model,raw in transcripts:
        if any(a['start']>b['start'] for a,b in zip(raw,raw[1:])):continue
        actual=join_recognized_clitics(raw) if join else raw
        models.append(model)
        matcher=SequenceMatcher(None,[key(w) for w in expected],[key(w['text']) for w in actual],autojunk=False)
        for block in matcher.get_matching_blocks():
            for i in range(block.size):
                word=actual[block.b+i]
                if 0<=word['start']<=word['end']<=duration+.1:candidates.setdefault(block.a+i,[]).append(word)
    if not models:raise ValueError('Conflicting measured ASR anchors within every transcript')
    nodes=[(i,w) for i in sorted(candidates) for w in candidates[i]]
    scores=[1]*len(nodes);parents=[-1]*len(nodes)
    for j,(idx,word) in enumerate(nodes):
        for k,(prev_idx,prev_word) in enumerate(nodes[:j]):
            if prev_idx<idx and prev_word['end']<=word['start']+.03 and scores[k]+1>scores[j]:scores[j]=scores[k]+1;parents[j]=k
    anchors={}
    if nodes:
        k=max(range(len(nodes)),key=lambda x:scores[x])
        while k>=0:
            idx,word=nodes[k];anchors[idx]=word;k=parents[k]
    return anchors,models

def measured_timing(story, duration, transcripts, *, allow_low_coverage=False):
    expected=' '.join(s['narration'] for s in story['scenes']).split()
    if not expected:raise ValueError('No narration to align')
    anchors,models=anchor_chain(expected,duration,transcripts,norm)
    exact_coverage=len(anchors)/len(expected);normalized=False
    if exact_coverage<.9:
        for join in (False,True):
            candidate,candidate_models=anchor_chain(expected,duration,transcripts,recognized_key,join=join)
            if len(candidate)>len(anchors):
                anchors,models=candidate,candidate_models;normalized=True
    coverage=len(anchors)/len(expected)
    if coverage<.85 and not allow_low_coverage:raise ValueError('Insufficient measured speech; retained audio requires recovery, never invented timing')
    diagnostic_only=coverage<.85
    cursor=0;scenes=[]
    for i,s in enumerate(story['scenes']):
        candidates=[anchors[k]['start'] for k in range(cursor,min(cursor+8,cursor+len(s['narration'].split()),len(expected))) if k in anchors]
        if not candidates:
            if not allow_low_coverage:raise ValueError('Insufficient measured speech at scene opening')
            diagnostic_only=True
        fallback=(i/len(story['scenes']))*duration
        scenes.append({**s,'start':0 if i==0 else (min(candidates) if candidates else fallback)})
        cursor+=len(s['narration'].split())
    for i,s in enumerate(scenes):s['end']=scenes[i+1]['start'] if i+1<len(scenes) else duration
    # Graphic reveals and jokes use measured speech anchors, never guessed beats.
    offset=0
    for scene in scenes:
        words=scene['narration'].split();tokens=[norm(w) for w in words]
        for key,prefix in [('punchline','meme'),('scare_phrase','scare')]:
            phrase=scene.get(key,'').strip()
            if not phrase:continue
            target=[norm(w) for w in phrase.split()]
            matches=[i for i in range(len(tokens)-len(target)+1) if tokens[i:i+len(target)]==target]
            if not matches:
                scene.setdefault('editorial_warnings',[]).append('Optional '+prefix+' effect omitted: phrase is absent from the scene')
                continue
            first=offset+matches[0];points=[anchors[k] for k in range(first,first+len(target)) if k in anchors]
            if len(points)<2:
                scene.setdefault('editorial_warnings',[]).append('Optional '+prefix+' effect omitted: fewer than two measured anchors')
                continue
            scene[prefix+'_beat']=min(w['start'] for w in points);scene[prefix+'_end']=max(w['end'] for w in points)
        offset+=len(words)
    captions=[]
    for start in range(0,len(expected),6):
        stop=min(start+6,len(expected));matches=[anchors[k] for k in range(start,stop) if k in anchors]
        if not matches:
            if not allow_low_coverage:raise ValueError('Insufficient measured speech for caption')
            diagnostic_only=True
        fallback_start=(start/len(expected))*duration; fallback_end=(stop/len(expected))*duration
        captions.append({'text':' '.join(expected[start:stop]),'start':0 if start==0 else (matches[0]['start'] if matches else fallback_start),'end':matches[-1]['end'] if matches else fallback_end})
    return {'duration':duration,'scenes':scenes,'words':transcripts[0][1],'caption_groups':captions,
            'coverage':coverage,'diagnostic_only':diagnostic_only,'exact_token_coverage':exact_coverage,'known_name_and_egyptian_normalization_applied':normalized,'asr_model':'+'.join(models),'unmatched_script_words':[w for i,w in enumerate(expected) if i not in anchors],
            'timing_method':('Known-name and Egyptian-pronunciation normalized measured anchors' if normalized else 'Exact-token ensemble anchors')+'; supplied-script phrase captions; no active-word precision claim'}
