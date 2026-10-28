"""Combine exact-token ASR anchors; retain phrase-level timing honesty."""
from difflib import SequenceMatcher
import re


def norm(s):
    return re.sub(r'[^\u0621-\u064a]','',s).translate(str.maketrans({'أ':'ا','إ':'ا','آ':'ا','ة':'ه','ى':'ي'}))


def measured_timing(story, duration, transcripts):
    expected=' '.join(s['narration'] for s in story['scenes']).split();anchors={};models=[]
    for model,actual in transcripts:
        models.append(model)
        matcher=SequenceMatcher(None,[norm(w) for w in expected],[norm(w['text']) for w in actual],autojunk=False)
        for block in matcher.get_matching_blocks():
            for i in range(block.size):anchors.setdefault(block.a+i,actual[block.b+i])
    coverage=len(anchors)/len(expected)
    if coverage<.85:raise ValueError('Insufficient exact-token evidence for phrase timing')
    previous=-1
    for i in sorted(anchors):
        if anchors[i]['start']<previous:raise ValueError('Conflicting measured ASR anchors')
        previous=anchors[i]['start']
    cursor=0;scenes=[]
    for i,s in enumerate(story['scenes']):
        candidates=[anchors[k]['start'] for k in range(cursor,min(cursor+4,len(expected))) if k in anchors]
        if not candidates:raise ValueError('Scene has no measured opening speech anchors')
        scenes.append({**s,'start':0 if i==0 else min(candidates)})
        cursor+=len(s['narration'].split())
    for i,s in enumerate(scenes):s['end']=scenes[i+1]['start'] if i+1<len(scenes) else duration
    captions=[]
    for start in range(0,len(expected),6):
        stop=min(start+6,len(expected));matches=[anchors[k] for k in range(start,stop) if k in anchors]
        if not matches:raise ValueError('Caption has no measured speech anchors')
        captions.append({'text':' '.join(expected[start:stop]),'start':0 if start==0 else matches[0]['start'],'end':matches[-1]['end']})
    return {'duration':duration,'scenes':scenes,'words':transcripts[0][1],'caption_groups':captions,
            'coverage':coverage,'asr_model':'+'.join(models),'unmatched_script_words':[w for i,w in enumerate(expected) if i not in anchors],
            'timing_method':'Exact-token ensemble anchors; supplied-script phrase captions; no active-word precision claim'}
