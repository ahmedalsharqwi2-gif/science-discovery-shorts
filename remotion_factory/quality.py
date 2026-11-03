"""Inspect actual complete media and eight rendered scenes before scheduling."""
import hashlib,json,subprocess
from pathlib import Path
from PIL import Image,ImageStat
from .audio_delivery import probe
def verify(movie,report,profile):
 if report.get('review_sample') or not report.get('fully_decoded') or report.get('profile')!=profile:raise ValueError('Not a complete film for this channel')
 if report['video_sha256']!=hashlib.sha256(movie.read_bytes()).hexdigest():raise ValueError('Film fingerprint changed')
 if not report.get('audio_tail',{}).get('audio_tail_checked') or report['audio_tail']['last_speech_window_correlation']<.85:raise ValueError('Original speech tail missing')
 meta=probe(movie);duration=float(meta['format']['duration']);video=next(s for s in meta['streams'] if s['codec_type']=='video')
 if (video['width'],video['height'])!=(1080,1920) or not (60 if profile=='news' else 90)<duration<180:raise ValueError('Permanent geometry/duration rule failed')
 if profile in ('horror','history') and (report.get('fiction') or not report.get('source',{}).get('url')):raise ValueError('True story evidence required')
 shots=sorted(movie.parent.glob('remotion-shot-*.png'))
 if len(shots)!=8:raise ValueError('Eight actual-timing visual inspections required')
 from .packaging import verify as verify_publication
 verify_publication(movie.parent,report)
 hashes=set()
 for shot in shots:
  im=Image.open(shot).convert('RGB');im.thumbnail((270,480))
  if max(ImageStat.Stat(im).stddev)<6:raise ValueError('Blank or nearly uniform rendered scene')
  hashes.add(hashlib.sha256(im.tobytes()).hexdigest())
 if len(hashes)<6:raise ValueError('Too many identical scenes')
 subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(movie),'-f','null','-'],check=True)
 (movie.parent/'daily-quality.json').write_text(json.dumps({'passed':True,'actual_scene_images':8,'unique_scenes':len(hashes),'full_decode':True,'video_sha256':report['video_sha256'],'human_review_claimed':False},indent=2))
