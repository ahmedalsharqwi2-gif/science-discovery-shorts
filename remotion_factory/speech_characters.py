"""Recover measured phrase timing across ASR word-splitting differences."""
from difflib import SequenceMatcher

def character_timing(story,duration,transcripts,key,exact_coverage=0):
    expected=' '.join(s['narration'] for s in story['scenes']).split()
    pieces=[key(w) for w in expected];script=''.join(pieces)
    if not script:raise ValueError('No normalized script characters')
    ranges=[];offset=0
    for token in pieces:ranges.append((offset,offset+len(token)));offset+=len(token)
    best=None;candidates={};matched_characters=set();retained=[]
    for model,raw in transcripts:
        if not raw or any(a['start']>b['start'] for a,b in zip(raw,raw[1:])):continue
        if any(not 0<=w['start']<w['end']<=duration+.1 for w in raw):continue
        actual=[];owners=[]
        for index,word in enumerate(raw):
            token=key(word['text']);actual.append(token);owners.extend([index]*len(token))
        recognized=''.join(actual)
        mapping={}
        for block in SequenceMatcher(None,script,recognized,autojunk=False).get_matching_blocks():
            if block.size<4:continue
            for i in range(block.size):mapping[block.a+i]=owners[block.b+i]
        anchors={}
        for i,(start,end) in enumerate(ranges):
            if end<=start:continue
            positions=[p for p in range(start,end) if p in mapping]
            threshold=1 if end-start<=3 else .85
            if len(positions)/(end-start)<threshold:continue
            indices=sorted({mapping[p] for p in positions})
            if not indices or indices[-1]-indices[0]>5:continue
            first,last=raw[indices[0]],raw[indices[-1]]
            if last['end']-first['start']>3:continue
            anchors[i]={'start':first['start'],'end':last['end'],'recognized_token_indices':indices}
        retained.append((model,raw));matched_characters.update(mapping)
        for i,anchor in anchors.items():candidates.setdefault(i,[]).append({**anchor,'asr_model':model})
        word_coverage=len(anchors)/len(expected);char_coverage=len(mapping)/len(script)
        score=min(word_coverage,char_coverage)
        if best is None or score>best[0]:best=(score,model,raw,anchors,word_coverage,char_coverage)
    if best is None:raise ValueError('No valid independently recognized speech')
    nodes=[(i,a) for i in sorted(candidates) for a in candidates[i]]
    scores=[1]*len(nodes);parents=[-1]*len(nodes)
    for j,(idx,anchor) in enumerate(nodes):
        for k,(previous_idx,previous) in enumerate(nodes[:j]):
            # A single recognized token may contain two adjacent script words.
            if previous_idx<idx and previous['start']<=anchor['start'] and previous['end']<=anchor['end']+.03 and scores[k]+1>scores[j]:
                scores[j]=scores[k]+1;parents[j]=k
    anchors={}
    if nodes:
        k=max(range(len(nodes)),key=lambda n:scores[n])
        while k>=0:
            idx,anchor=nodes[k];anchors[idx]=anchor;k=parents[k]
    word_coverage=len(anchors)/len(expected);char_coverage=len(matched_characters)/len(script)
    if min(word_coverage,char_coverage)<.9:raise ValueError('Insufficient independently recognized speech after word-splitting normalization')
    model='+'.join(sorted({a['asr_model'] for a in anchors.values()}));raw=retained[0][1]
    scenes=[];cursor=0
    for i,scene in enumerate(story['scenes']):
        size=len(scene['narration'].split())
        points=[anchors[k]['start'] for k in range(cursor,min(cursor+8,cursor+size)) if k in anchors]
        if not points:raise ValueError('Scene opening has no recognized speech')
        scenes.append({**scene,'start':0 if i==0 else min(points)});cursor+=size
    if any(a['start']>=b['start'] for a,b in zip(scenes,scenes[1:])):raise ValueError('Scene opening anchors are not monotonic')
    for i,scene in enumerate(scenes):scene['end']=scenes[i+1]['start'] if i+1<len(scenes) else duration
    captions=[]
    boundaries=list(range(0,len(expected),6))
    if len(boundaries)>1 and len(expected)-boundaries[-1]<=2:boundaries.pop()
    for group_index,start in enumerate(boundaries):
        stop=boundaries[group_index+1] if group_index+1<len(boundaries) else len(expected);points=[anchors[k] for k in range(start,stop) if k in anchors]
        if not points:raise ValueError('Caption lacks independently recognized speech')
        entry={'text':' '.join(expected[start:stop]),'start':0 if start==0 else min(w['start'] for w in points),'end':max(w['end'] for w in points)}
        if captions and entry['start']<captions[-1]['end']:
            if entry['start']>captions[-1]['start']+.05:
                # Alternative ASR models can overlap at a phrase boundary.
                # Switch at the next independently recognized phrase start.
                captions[-1]['end']=entry['start'];captions.append(entry)
            else:
                captions[-1]['text']+=' '+entry['text'];captions[-1]['end']=max(captions[-1]['end'],entry['end'])
        else:captions.append(entry)
    if captions:captions[-1]['end']=duration  # Keep the last phrase visible; never invent a word anchor.
    if any(len(c['text'].split())>18 for c in captions):raise ValueError('Shared ASR token spans exceed the readable phrase budget')
    return {'duration':duration,'scenes':scenes,'words':raw,'caption_groups':captions,
       'coverage':word_coverage,'exact_token_coverage':exact_coverage,'normalized_character_coverage':char_coverage,
       'known_name_and_egyptian_normalization_applied':True,'asr_model':model,
       'unmatched_script_words':[word for i,word in enumerate(expected) if i not in anchors],
       'asr_transcripts':[{'model':m,'recognized_words':w} for m,w in retained],
       'caption_boundary_method':'Clip an overlapping phrase at the next independently recognized phrase start; retain raw ASR timestamps',
       'timing_method':'Monotonic ensemble of normalized script-character anchors against independently recognized speech; ASR word-splitting differences allowed; supplied-script phrase captions; no active-word precision claim'}

