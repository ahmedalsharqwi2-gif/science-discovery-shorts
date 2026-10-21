"""Measured phrase intervals for whole-phrase captions; no active-word claims."""
import math,json,subprocess
from pathlib import Path

def phrase_intervals(events,words,duration,width=5):
    from film_factory.render import norm
    if len(events)!=len(words):raise RuntimeError('Phrase aligner must retain every transcript token')
    for event,word in zip(events,words):
        if norm(event['text'])!=norm(word):raise RuntimeError('Phrase aligner changed the narration')
        if not all(math.isfinite(float(event[k])) for k in ('start','end')):raise RuntimeError('Non-finite speech interval')
        if event['start']<0 or event['end']<event['start'] or event['end']>duration+.1:raise RuntimeError('Speech interval outside recording')
    groups=[];previous=0.
    for lo in range(0,len(words),width):
        chunk=events[lo:lo+width];valid=[x for x in chunk if x['end']>x['start']]
        if not valid:raise RuntimeError('No measured speech in caption phrase')
        start=min(x['start'] for x in valid);end=max(x['end'] for x in valid)
        if end-start<.10 or end-start>12 or start<previous-.10:raise RuntimeError('Missing or overlapping spoken phrase')
        groups.append({'text':' '.join(words[lo:lo+width]),'start':start,'end':end,'measured_phrase':True});previous=end
    return groups

def force_phrase_alignment(wav,words,duration,asr_anchors=None):
    import stable_whisper
    import torch
    torch.set_num_threads(2)
    model=stable_whisper.load_faster_whisper('medium',device='cpu',compute_type='int8')
    result=model.align(str(wav),' '.join(words),language='ar',failure_threshold=0.0,max_word_dur=3.0,fast_mode=False)
    if result is None:raise RuntimeError('No waveform phrase alignment returned')
    events=[{'text':w.word.strip(),'start':float(w.start),'end':float(w.end)} for s in result.segments for w in (s.words or [])]
    asr_anchors=asr_anchors or {}
    for i,event in enumerate(events):
        if event['end']<=event['start'] and i in asr_anchors:
            other=asr_anchors[i]
            if other['end']>other['start']:events[i]={'text':words[i],'start':other['start'],'end':other['end']}
    unresolved=[i for i,event in enumerate(events) if event['end']<=event['start']]
    if unresolved:
        # One bounded re-alignment on the real audio tail/window, never silence padding.
        lo=max(0,min(unresolved)-7);hi=min(len(words),max(unresolved)+5)
        start=max(0,events[lo]['start']-.4);end=min(duration,max(events[hi-1]['end']+.4,duration if hi==len(words) else 0))
        if 0<end-start<=18 and hi-lo<=24:
            crop=Path('output/whisper-realign.wav')
            subprocess.run(['ffmpeg','-v','error','-y','-ss',str(start),'-i',str(wav),'-t',str(end-start),'-ar','16000','-ac','1',str(crop)],check=True)
            local=model.align(str(crop),' '.join(words[lo:hi]),language='ar',failure_threshold=0.0,max_word_dur=3.0,fast_mode=False)
            measured=[{'text':w.word.strip(),'start':float(w.start)+start,'end':float(w.end)+start} for seg in (local.segments if local else []) for w in (seg.words or [])]
            if len(measured)==hi-lo:
                for j,event in enumerate(measured):
                    if event['end']>event['start']:events[lo+j]=event
    Path('output/phrase-alignment-diagnostics.json').write_text(json.dumps({'events':events,'independent_asr_anchors':asr_anchors,'expected':words,'duration':duration},ensure_ascii=False,indent=2))
    groups=phrase_intervals(events,words,duration)
    return events,groups
