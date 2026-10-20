"""Validate real media and approvals before any rendering or publication."""
from pathlib import Path
import hashlib, json, math, subprocess
from PIL import Image, features
ROOT = Path(__file__).resolve().parent

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def media_info(path):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]))

def number(value, label):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        raise ValueError(f'Invalid numeric value: {label}')
    return float(value)

def validate(manifest_path):
    lock=json.loads((ROOT/'style-lock.json').read_text())
    for name,expected in lock.items():
        if digest(ROOT/name)!=expected:raise ValueError(f'Approved style changed: {name}')
    path = Path(manifest_path).resolve()
    data = json.loads(path.read_text(encoding='utf8'))
    base = path.parent
    if data.get('schema_version') != 1:
        raise ValueError('Unsupported episode schema')
    profile_name=data.get('profile')
    if profile_name not in ('history','science','horror'):
        raise ValueError('Choose history, science, or horror profile')
    profile=json.loads((ROOT/'profiles'/f'{profile_name}.json').read_text())
    if not features.check('raqm'):
        raise ValueError('Arabic shaping requires Pillow with libraqm')
    reviews=data.get('review',{})
    for key in ('script','voice','images','caption_timing'):
        if reviews.get(key,{}).get('approved') is not True or not reviews[key].get('by'):
            raise ValueError(f'Missing explicit review: {key}; no lower-quality fallback is allowed')
    # The renderer never fetches remote URLs, invokes TTS, or chooses replacement media.
    def asset(value):
        if not isinstance(value,str) or not value or '://' in value:
            raise ValueError('Media must be a checked-in local relative path')
        p=(base/value).resolve()
        if not p.is_relative_to(base):
            raise ValueError('Asset escapes episode folder')
        if not p.is_file():
            raise ValueError(f'Missing media: {value}')
        expected=data.get('asset_sha256',{}).get(value)
        if not expected or digest(p)!=expected:
            raise ValueError(f'Asset is not the reviewed version: {value}')
        return p
    audio=data.get('audio',{})
    audio_path=asset(audio.get('path'))
    if audio.get('speed',1)!=1 or audio.get('pitch_semitones',0)!=0:
        raise ValueError('Approved voice must retain its speed and pitch')
    if not audio.get('provenance'):
        raise ValueError('Record audio provenance; an MP4 does not reveal a TTS voice ID')
    meta=media_info(audio_path)
    if not any(s['codec_type']=='audio' for s in meta['streams']):
        raise ValueError('Narration has no audio stream')
    duration=number(float(meta['format']['duration']),'audio duration')
    if duration<=0 or duration>180:
        raise ValueError('Episode audio must be within 0–180 seconds')
    declared=number(data.get('duration'),'episode duration')
    if abs(declared-duration)>.04:
        raise ValueError('Timeline must cover the entire provided narration; trimming is forbidden')
    scenes=data.get('scenes',[])
    if not scenes:raise ValueError('Storyboard is empty')
    cursor=0
    paths={audio['path']:audio_path}
    distinct=set()
    for i,scene in enumerate(scenes):
        start=number(scene.get('start'),f'scene {i} start');end=number(scene.get('end'),f'scene {i} end')
        if abs(start-cursor)>.002 or end<=start or end-start>profile['max_scene_seconds']:
            raise ValueError(f'Scene {i}: timeline gaps, overlaps, or overly long shot')
        cursor=end
        if not scene.get('subject') or not scene.get('visual_rationale'):
            raise ValueError(f'Scene {i}: state what the image depicts and why it matches the narration')
        background=scene.get('background');p=asset(background);paths[background]=p;distinct.add(background)
        with Image.open(p) as im:
            if min(im.size)<900 or im.mode not in ('RGB','RGBA'):
                raise ValueError(f'Low resolution background: {background}')
        for layer in scene.get('layers',[]):
            p=asset(layer.get('path'));paths[layer['path']]=p
            with Image.open(p) as im:
                if im.mode!='RGBA' or im.getextrema()[3][0]==255:
                    raise ValueError('Parallax foreground must have real transparency')
        if scene.get('overlay'):
            paths[scene['overlay']]=asset(scene['overlay'])
        for route in scene.get('routes',[]):
            if not route.get('interpretation') or len(route.get('points',[]))<2:
                raise ValueError('Routes require geometry and an explicit historical interpretation')
        for point in scene.get('locators',[]):
            if not point.get('label') or len(point.get('position',[]))!=2:
                raise ValueError('Map locators need a label and position')
        for camera in (scene.get('camera_start',[1.04,0,0]),scene.get('camera_end',[1.10,0,0])):
            if len(camera)!=3 or not 1<=number(camera[0],'zoom')<=1.35 or any(abs(number(v,'pan'))>150 for v in camera[1:]):
                raise ValueError('Camera motion exceeds the approved restrained-motion range')
    if abs(cursor-duration)>.04:raise ValueError('Storyboard does not cover the whole narration')
    if duration>=25 and len(distinct)<3:raise ValueError('Long episode needs at least three reviewed backgrounds')
    captions=data.get('captions',[])
    if not captions:raise ValueError('Timed Arabic captions are required')
    cursor=0
    for i,c in enumerate(captions):
        a=number(c.get('start'),f'caption {i} start');b=number(c.get('end'),f'caption {i} end')
        if a<cursor-.002 or a<0 or b<=a or b>duration+.04 or a-cursor>1.5:
            raise ValueError(f'Invalid, overlapping, or missing caption timing at {i}')
        if not c.get('text','').strip():raise ValueError('Empty caption')
        cursor=b
    if duration-cursor>1.5:raise ValueError('Caption timeline ends before the narration')
    # This is declared human review, not an automated claim about historical/scientific truth.
    return data,profile,paths,meta
