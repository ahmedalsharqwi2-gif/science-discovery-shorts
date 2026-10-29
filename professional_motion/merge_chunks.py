"""Join exact frame partitions; reject gaps, duplicate frames or mismatched stories."""
import hashlib,json,math,subprocess
from pathlib import Path
ROOT=Path('professional_motion')

def check_intervals(rows,total):
    cursor=0
    for row in rows:
        if row['start_frame']!=cursor or not cursor<row['end_frame']<=total:raise ValueError('Rendered frame partitions have a gap, overlap or invalid boundary')
        cursor=row['end_frame']
    if cursor!=total:raise ValueError('Rendered frame partitions do not cover the complete narration')

def main():
    timing=json.loads((ROOT/'delivery/timing.json').read_text());duration=timing['duration'];total=math.ceil(duration*30)
    digest=hashlib.sha256((ROOT/'delivery/story.json').read_bytes()).hexdigest()
    if timing.get('story_sha256')!=digest:raise ValueError('Story changed after narration timing')
    chunks=[]
    for p in (ROOT/'chunks').glob('chunk-*.mp4.json'):
        d=json.loads(p.read_text());video=p.with_suffix('')
        if d.get('story_sha256')!=digest or d.get('total_frames')!=total or d.get('errors') or not d.get('originalVoice'):raise ValueError('Inconsistent rendered partition')
        if (d.get('width'),d.get('height'),d.get('fps'))!=(1080,1920,30):raise ValueError('Unexpected partition geometry or frame rate')
        count=int(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-count_frames','-show_entries','stream=nb_read_frames','-of','csv=p=0',str(video)]))
        if count!=d['end_frame']-d['start_frame']:raise ValueError('Encoded partition lost or duplicated a frame')
        chunks.append({**d,'video':video})
    chunks.sort(key=lambda d:d['start_frame']);check_intervals(chunks,total)
    out=ROOT/'output';out.mkdir(exist_ok=True)
    listing=out/'chunks.ffconcat';listing.write_text(''.join("file '"+str(c['video'].resolve()).replace("'","'\\''")+"'\n" for c in chunks))
    subprocess.run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',str(listing),'-map','0:v:0','-an','-c:v','copy','-movflags','+faststart',str(out/'visuals.mp4')],check=True)
    count=int(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-count_frames','-show_entries','stream=nb_read_frames','-of','csv=p=0',str(out/'visuals.mp4')]))
    if count!=total:raise ValueError('Joined film has missing or repeated frames')
    (out/'render.json').write_text(json.dumps({'duration':duration,'from':0,'to':duration,'start_frame':0,'end_frame':total,'total_frames':total,'fps':30,'width':1080,'height':1920,'originalVoice':True,'story_sha256':digest,'errors':[],'partitions':len(chunks)},indent=2))
    print('Joined',len(chunks),'partitions with exactly',total,'frames')

if __name__=='__main__':main()
