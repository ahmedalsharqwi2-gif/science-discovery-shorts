"""ASS audit sidecar for the exact React-rendered caption events, not an audio alignment."""
from pathlib import Path
from .locked_episode import validate_timing

def timestamp(seconds):
 centis=round(seconds*100);h,centis=divmod(centis,360000);m,centis=divmod(centis,6000);s,c=divmod(centis,100);return f'{h}:{m:02}:{s:02}.{c:02}'
def write(story,timing,path):
 validate_timing(story,timing)
 rows=['[Script Info]','ScriptType: v4.00+','PlayResX: 1080','PlayResY: 1920','[Events]','Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text']
 for c in timing['caption_groups']:
  if any(x in c['text'] for x in ('\n','\r','{','}')):raise ValueError('Caption contains ASS control characters')
  rows.append('Dialogue: 0,'+timestamp(c['start'])+','+timestamp(c['end'])+',Default,,0,0,0,,'+c['text'])
 with Path(path).open('x',encoding='utf8') as f:f.write('\n'.join(rows)+'\n')
 return path
