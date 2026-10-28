"""Technical checks for sparse explanatory diagrams, not photographic motion.

Measure changing pixels inside the diagram, separately within every scene.
Header/caption/progress animation and scene cuts cannot disguise a frozen diagram.
"""
import io
import json
import subprocess
from pathlib import Path
from PIL import Image, ImageChops, ImageStat


def audit(path, scenes, report='output/visual_quality.json'):
    meta=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]))
    video=next(s for s in meta['streams'] if s['codec_type']=='video')
    if (video['width'],video['height'])!=(1080,1920):
        raise ValueError('Expected vertical 1080x1920 motion graphics')
    duration=float(meta['format']['duration'])
    if duration<8 or not scenes:raise ValueError('Missing complete scene coverage')
    if abs(scenes[0]['start'])>.1 or abs(scenes[-1]['end']-duration)>.1:
        raise ValueError('Scene timing does not cover the video')
    rows=[]
    for index,scene in enumerate(scenes):
        start,end=float(scene['start']),float(scene['end'])
        if end<=start or (index and abs(start-scenes[index-1]['end'])>.1):
            raise ValueError('Invalid or discontinuous scene timing')
        frames=[];spatial=[]
        for ratio in (.21,.49,.83):
            at=start+(end-start)*ratio
            raw=subprocess.check_output(['ffmpeg','-v','error','-ss',str(at),'-i',str(path),
                '-frames:v','1','-f','image2pipe','-vcodec','png','-'])
            im=Image.open(io.BytesIO(raw)).convert('RGB')
            # Excludes titles, captions, source footer and progress bar.
            diagram=im.crop((90,500,990,1540)).resize((270,312),Image.Resampling.LANCZOS)
            spatial.append(max(ImageStat.Stat(diagram).stddev))
            frames.append(diagram)
        changes=[]
        for a,b in zip(frames,frames[1:]):
            diff=ImageChops.difference(a,b)
            changed=sum(max(pixel)>12 for pixel in diff.getdata())
            changes.append(changed/(a.width*a.height))
        rows.append({'scene':index+1,'diagram_spatial_std':spatial,'changed_pixel_ratios':changes,
                     'passed':min(spatial)>=6 and max(changes)>=.001})
    result={'passed':all(r['passed'] for r in rows),'duration':duration,'resolution':[1080,1920],
            'method':'within-scene diagram-region pixel changes','scenes':rows,
            'note':'Technical blank/freeze detection only; not a judgement of artistic or factual quality.'}
    Path(report).parent.mkdir(parents=True,exist_ok=True)
    Path(report).write_text(json.dumps(result,indent=2))
    if not result['passed']:raise ValueError('Blank or frozen explanatory diagram in one or more scenes')
    return result
