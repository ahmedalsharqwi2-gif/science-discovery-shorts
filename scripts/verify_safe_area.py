"""Encoded-video and shaped-text pixel audit; no declared text-box trust.

The mask is a separate rendering of the SAME shaped glyphs/pill at the SAME
sample time. Manifest boxes cannot make an out-of-zone mask pass. Real phone
checks remain separate: these overlays are not screenshots of platform apps.
"""
import argparse,hashlib,json,math,subprocess,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from visual_contract import load_template,assert_in_safe_zone,validate_scene_boxes,overlaps

def pixel_boxes(mask,template):
 a=np.asarray(mask.convert('RGB')).astype(int);result={}
 for name,color in template['layout']['mask_colors'].items():
  rgb=np.array([int(color[i:i+2],16) for i in (1,3,5)])
  ys,xs=np.where(np.max(np.abs(a-rgb),axis=2)<24)
  if len(xs):result[name]=(int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1)
 return result

def platform_rects(platform):
 if platform=='shorts':return [(0,0,1080,288),(0,1248,1080,1920),(0,0,48,1920),(888,0,1080,1920),(0,908,171,1700),(909,908,1080,1700),(510,1256,1011,1420)]
 if platform=='tiktok':return [(0,0,1080,240),(0,1260,1080,1920),(0,0,120,1920),(960,0,1080,1920),(780,840,1080,1920)]
 if platform=='reels':return [(0,0,1080,269),(0,1248,1080,1920),(0,0,65,1920),(1015,0,1080,1920)]
 raise ValueError('Unknown platform')

def validate_platform_boxes(boxes):
 for name,box in boxes.items():
  if name in ('brand','review'):continue
  for platform in ('shorts','tiktok','reels'):
   if any(overlaps(box,rect) for rect in platform_rects(platform)):raise ValueError(name+' intersects '+platform+' interface')
 return True

def verify(video,manifest,output,*,stills_only=False):
 t=load_template();data=json.loads(Path(manifest).read_text());base=Path(manifest).parent;out=Path(output);out.mkdir(parents=True,exist_ok=True)
 if video is not None:
  if hashlib.sha256(Path(video).read_bytes()).hexdigest()!=data['video_sha256']:raise ValueError('Audit is not bound to this MP4')
 elif not stills_only:raise ValueError('Encoded video required for final audit')
 required={0,*range(0,math.ceil(data['duration']*30),60),*(math.ceil(c['start']*30) for c in data['caption_groups'])};required={f for f in required if f<math.ceil(data['duration']*30)}
 if set(s['frame'] for s in data['samples'])!=required:raise ValueError('Missing samples: every two seconds plus each caption start required')
 rows=[]
 for sample in data['samples']:
  frame=sample['frame'];mask=Image.open(base/sample['mask']);normal=Image.open(base/sample['image']).convert('RGB')
  if normal.size!=(1080,1920) or mask.size!=normal.size:raise ValueError('Full-resolution audit required')
  boxes=pixel_boxes(mask,t)
  if not sample.get('focal_bbox'):raise ValueError('Missing measured focal subject')
  for name,box in boxes.items():assert_in_safe_zone(name,box,kind='chrome' if name in ('brand','review') else 'text',template=t)
  validate_platform_boxes(boxes)
  if not boxes.get('title'):raise ValueError('Title pixels are missing')
  active=any(c['start']<=frame/30<c['end'] for c in data['caption_groups'])
  if active and not boxes.get('caption'):raise ValueError('Caption pixels are missing')
  if boxes.get('caption') and boxes['caption'][3]-boxes['caption'][1]>t['safe_zone']['caption_max_height']:raise ValueError('Caption exceeds two-line budget')
  if boxes['title'][3]>t['layout']['title_bottom']:raise ValueError('Title pixel band overflow')
  validate_scene_boxes(boxes['title'],boxes.get('caption'),sample['focal_bbox'],scale=sample['focal_scale_vs_reference'],template=t)
  if video is not None:
   raw=subprocess.check_output(['ffmpeg','-v','error','-ss',str(frame/30),'-i',str(video),'-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-'])
   if len(raw)!=1080*1920*3:raise ValueError('Cannot decode sampled video frame')
   encoded=np.frombuffer(raw,dtype=np.uint8).reshape(1920,1080,3).astype(float)
   difference=np.abs(encoded-np.asarray(normal).astype(float))
   if difference.mean()>8:raise ValueError('Video differs from the audited pixel render')
   for name,box in boxes.items():
    x,y,r,b=box
    if difference[y:b,x:r].mean()>14:raise ValueError('Encoded text differs from the audited rendering')
  rows.append({'frame':frame,'pixel_boxes':boxes,'focal_bbox':sample['focal_bbox'],'scale':sample['focal_scale_vs_reference']})
 first=data['samples'][0];image=Image.open(base/first['image']).convert('RGBA')
 previews=[]
 for platform in ('shorts','tiktok','reels'):
  target=out/(platform+'.png')
  if target.exists():raise FileExistsError(target)
  layer=Image.new('RGBA',image.size);d=ImageDraw.Draw(layer)
  for rect in platform_rects(platform):d.rectangle(rect,fill=(220,40,70,60),outline=(220,40,70,150),width=3)
  Image.alpha_composite(image,layer).save(target);previews.append(str(target))
 result={'passed':True,'scope':'stills-only' if stills_only else 'encoded-video','samples':len(rows),'measurements':rows,'previews':previews,'real_phone_validation':'not performed; overlays are not device screenshots'}
 with (out/'safe-area-report.json').open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2)
 return result
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--video',type=Path);a.add_argument('--manifest',type=Path,required=True);a.add_argument('--output',type=Path,required=True);a.add_argument('--stills-only',action='store_true');args=a.parse_args();r=verify(args.video,args.manifest,args.output,stills_only=args.stills_only);print(json.dumps({k:v for k,v in r.items() if k!='measurements'},ensure_ascii=False))
