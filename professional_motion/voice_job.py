"""Run inside Actions; publish only generated review media, never credentials."""
import json
from pathlib import Path
from difflib import SequenceMatcher
import re
import subprocess
from film_factory.voice import generate


def norm(s):
    return re.sub(r'[^\u0621-\u064a]','',s).translate(str.maketrans({'أ':'ا','إ':'ا','آ':'ا','ة':'ه','ى':'ي'}))


def main():
    story=json.loads(Path('professional_motion/story.json').read_text())
    out=Path('professional_motion/delivery');out.mkdir(exist_ok=True)
    full=' '.join(s['narration'] for s in story['scenes'])
    wav=str(out/'narration.wav')
    if not Path(wav).exists():
        wav=generate(full,str(out/'narration.wav'),
       'Read this complete Egyptian Arabic science explanation, warm engaging Charon voice. '
       'Start with curiosity, build momentum, thoughtful final payoff. No music or sound effects. '
       'Read only the supplied words. Finish the last sentence. Clear natural pace.')
    from faster_whisper import WhisperModel
    model=WhisperModel('small',device='cpu',compute_type='int8',cpu_threads=2)
    segments,_=model.transcribe(str(wav),language='ar',word_timestamps=True,beam_size=5,vad_filter=False)
    actual=[{'text':w.word.strip(),'start':float(w.start),'end':float(w.end)} for s in segments for w in s.words or []]
    expected=full.split();matcher=SequenceMatcher(None,[norm(w) for w in expected],[norm(w['text']) for w in actual],autojunk=False)
    anchors={}
    for block in matcher.get_matching_blocks():
        for i in range(block.size):anchors[block.a+i]=actual[block.b+i]
    coverage=len(anchors)/len(expected)
    (out/'alignment-debug.json').write_text(json.dumps({'coverage':coverage,'recognized_words':actual},ensure_ascii=False,indent=2))
    if coverage<.8:raise RuntimeError('Narration alignment coverage below review threshold')
    duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(wav)]))
    cursor=0;scenes=[]
    for i,s in enumerate(story['scenes']):
        candidates=[anchors[k]['start'] for k in range(cursor,min(cursor+4,len(expected))) if k in anchors]
        if not candidates:raise RuntimeError('Scene start lacks a measured speech anchor')
        scenes.append({**s,'start':0 if i==0 else min(candidates)})
        cursor+=len(s['narration'].split())
    for i,s in enumerate(scenes):s['end']=scenes[i+1]['start'] if i+1<len(scenes) else duration
    (out/'timing.json').write_text(json.dumps({'duration':duration,'scenes':scenes,'words':actual,'coverage':coverage,'timing_method':'ASR scene anchors; captions use measured recognized words'},ensure_ascii=False,indent=2))
    print('Generated original Charon narration; aligned coverage',round(coverage,3))


if __name__=='__main__':
    try:main()
    except Exception as error:
        out=Path('professional_motion/delivery');out.mkdir(exist_ok=True)
        (out/'error.json').write_text(json.dumps({'error_class':type(error).__name__,'stage':'voice-or-alignment'}))
        raise
