"""1080x1920 native motion cards; Arabic shaping, mobile safe area, measured captions."""
import json, math, re, subprocess, hashlib
from pathlib import Path
from functools import lru_cache
from difflib import SequenceMatcher
import numpy as np
from PIL import Image,ImageDraw,ImageFont
W,H,FPS=1080,1920,30
BG=(7,14,31);CYAN=(65,223,233);GOLD=(255,185,82);INK=(237,244,255);MUTED=(148,168,195)
FONT=Path(__file__).resolve().parent.parent/'photo_motion/assets/NotoSansArabic-Bold.ttf'
REG=FONT.with_name('NotoSansArabic-Regular.ttf')
@lru_cache(maxsize=128)
def font(size,bold=True):return ImageFont.truetype(str(FONT if bold else REG),size)
@lru_cache(maxsize=512)
def textfont(text,size,bold=True):
    if re.search(r'[A-Za-z/•]',str(text)):
        path='/usr/share/fonts/truetype/dejavu/DejaVuSans'+('-Bold' if bold else '')+'.ttf'
        return ImageFont.truetype(path,size)
    return font(size,bold)
def txt(im,text,xy,size=42,fill=INK,anchor='mm',bold=True):
    ImageDraw.Draw(im).text(xy,str(text),font=textfont(text,size,bold),fill=fill,anchor=anchor,direction='rtl')
def lines(text,size,width):
    d=ImageDraw.Draw(Image.new('RGB',(2,2)));out=[];line=''
    for word in str(text).split():
        test=(line+' '+word).strip()
        if d.textlength(test,font=textfont(test,size),direction='rtl')>width and line:out.append(line);line=word
        else:line=test
    if line:out.append(line)
    return out

def para(im,text,cx,y,size=44,width=880,fill=INK,maxlines=3):
    rows=lines(text,size,width)
    if len(rows)>maxlines:
        size=max(27,size-7);rows=lines(text,size,width)
    if len(rows)>maxlines:raise ValueError('Arabic text exceeds mobile card bounds')
    for i,row in enumerate(rows):txt(im,row,(cx,y+i*(size*1.6)),size,fill)

def norm(w):return re.sub(r'[^\u0621-\u064a0-9]','',re.sub(r'[\u064b-\u065fـ]','',w)).translate(str.maketrans({'أ':'ا','إ':'ا','آ':'ا','ى':'ي','ة':'ه'}))

def align(plan,wav):
    from faster_whisper import WhisperModel
    model=WhisperModel('small',device='cpu',compute_type='int8',cpu_threads=4)
    segs,_=model.transcribe(str(wav),language='ar',word_timestamps=True,beam_size=5,vad_filter=False)
    actual=[{'text':w.word.strip(),'start':float(w.start),'end':float(w.end)} for s in segs for w in s.words or [] if norm(w.word)]
    expected=plan['narration'].split();matcher=SequenceMatcher(None,[norm(w) for w in expected],[norm(w['text']) for w in actual],autojunk=False);anchors={}
    for b in matcher.get_matching_blocks():
        for k in range(b.size):anchors[b.a+k]=actual[b.b+k]
    # Recover exact token splits/merges from actual ASR timestamps first.
    from scripts.asr_token_boundaries import recover_token_boundaries
    recovered=[anchors.get(i) and {'text':expected[i],'offset':anchors[i]['start'],'duration':anchors[i]['end']-anchors[i]['start']} for i in range(len(expected))]
    recover_token_boundaries([norm(w) for w in expected],[norm(w['text']) for w in actual],[(w['text'],w['start'],w['end']) for w in actual],expected,recovered)
    for i,event in enumerate(recovered):
        if event is not None:anchors[i]={'text':expected[i],'start':event['offset'],'end':event['offset']+event['duration']}
    coverage=len(anchors)/max(1,len(expected))
    if coverage<.85:
        if coverage<.50:raise ValueError(f'The recorded narration differs substantially from the script ({coverage:.1%})')
        from scripts.forced_caption_alignment import forced_word_alignment
        measured=forced_word_alignment(Path(wav),expected)
        anchors={i:{'text':w['text'],'start':w['offset'],'end':w['offset']+w['duration']} for i,w in enumerate(measured)}
        coverage=1.0
    duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(wav)]))
    def at(index):
        if index in anchors:return anchors[index]['start']
        left=max([i for i in anchors if i<index],default=None);right=min([i for i in anchors if i>index],default=None)
        if left is None:return 0.
        if right is None:return anchors[left]['end']
        return anchors[left]['start']+(anchors[right]['start']-anchors[left]['start'])*(index-left)/(right-left)
    words=[{'text':w,'start':at(i),'end':at(i+1) if i+1<len(expected) else duration,'measured':i in anchors} for i,w in enumerate(expected)]
    cursor=0;scenes=[]
    for scene in plan['scenes']:
        count=len(scene['narration'].split());start=at(cursor) if cursor else 0;cursor+=count
        end=at(cursor) if cursor<len(expected) else duration
        if end-start<2:raise ValueError('A scene has insufficient actual speech time')
        scene_words=scene['narration'].split();punch=scene['punchline'].split()
        positions=[i for i in range(len(scene_words)-len(punch)+1) if scene_words[i:i+len(punch)]==punch]
        if not positions:raise ValueError('Punchline not found in actual script')
        beat=at(cursor-count+positions[0])
        label_beats=[]
        for label in scene['labels']:
            keys=[norm(w) for w in label.split() if len(norm(w))>=3]
            position=next((i for i,w in enumerate(scene_words) if norm(w) in keys),None)
            label_beats.append(at(cursor-count+position) if position is not None else end)
        scenes.append({**scene,'start':start,'end':end,'beat':beat,'label_beats':label_beats})
    if actual and duration-actual[-1]['end']>2.5:raise ValueError('Unexpected long trailing silence; review final spoken sentence')
    result={'narration_sha256':hashlib.sha256(plan['narration'].encode()).hexdigest(),'coverage':coverage,'duration':duration,'words':words,'scenes':scenes,'asr_words':actual,'interpolated_words':[i for i in range(len(words)) if i not in anchors]}
    Path('output/timing.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    return result

class Renderer:
    def encode(self,path):
        frames=math.ceil(self.duration*FPS)
        p=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-an','-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(path)],stdin=subprocess.PIPE)
        try:
            for i in range(frames):
                p.stdin.write(self.frame(i/FPS).tobytes())
                if i%(FPS*10)==0:print(f'Rendering {i/FPS:.0f}/{self.duration:.0f} seconds',flush=True)
            p.stdin.close()
            if p.wait()!=0:raise RuntimeError('FFmpeg visual render failed')
        except BaseException:
            p.kill();raise
