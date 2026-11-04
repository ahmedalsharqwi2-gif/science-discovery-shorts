"""Bind the exact complete mix to the baked picture without re-rendering images."""
import json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def main():
 for profile in ['science','history']:
  movie=ROOT/'output'/(profile+'-hybrid-review.mp4');mix=ROOT/'studio/public'/profile/'mix.wav';final=movie.with_name(profile+'-bound-audio.mp4')
  subprocess.run(['ffmpeg','-y','-v','error','-i',str(movie),'-i',str(mix),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-ar','48000','-movflags','+faststart',str(final)],check=True)
  expected=json.loads((ROOT/'studio/public'/(profile+'.json')).read_text())['duration']
  data=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(final)]));audio=next(s for s in data['streams'] if s['codec_type']=='audio')
  if abs(float(audio['duration'])-expected)>.001:raise ValueError('The full exact-duration authored mix is required')
  final.replace(movie)
  print(profile,'same picture frames, complete exact-duration audio',expected,flush=True)
if __name__=='__main__':main()
