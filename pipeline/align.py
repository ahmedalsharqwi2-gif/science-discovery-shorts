"""Measured ASR timestamps mapped to the original script; never silently fabricate alignment."""
import json,sys,re,unicodedata,difflib
from faster_whisper import WhisperModel
def norm(s):
    s=unicodedata.normalize('NFKC',s)
    s=re.sub('[\u064b-\u065f\u0670\u0640]','',s)
    return re.sub(r'[^\w]','',s.replace('أ','ا').replace('إ','ا').replace('آ','ا').replace('ى','ي')).lower()
def align(original,spoken):
    words=original.split()
    a=[norm(w) for w in words];b=[norm(w['word']) for w in spoken]
    matcher=difflib.SequenceMatcher(None,a,b,autojunk=False)
    result=[]
    for tag,i,j,k,l in matcher.get_opcodes():
        if tag!='equal':raise ValueError('ALIGNMENT_REQUIRES_REVIEW: unmatched original/recognized words')
        for offset in range(j-i):
            w=spoken[k+offset];result.append({'text':words[i+offset],'start':w['start'],'end':w['end']})
    return result
if __name__=='__main__':
    inp=json.load(open(sys.argv[1]));model=WhisperModel('small',device='cpu',compute_type='int8');out=[]
    for scene in inp:
        segments,_=model.transcribe(scene['file'],language='ar',word_timestamps=True,beam_size=5,initial_prompt=scene['text'],vad_filter=True)
        words=[{'word':w.word,'start':w.start,'end':w.end} for s in segments for w in s.words]
        out.append(align(scene['text'],words))
    json.dump(out,open(sys.argv[2],'w'),ensure_ascii=False)
