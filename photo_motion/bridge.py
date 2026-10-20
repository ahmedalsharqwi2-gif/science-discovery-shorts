"""Explicit opt-in bridge: reject mismatched script/audio instead of falling back."""
import json,os,re
from pathlib import Path
from .contract import validate,digest
from .engine import render

def words(text):
    text=re.sub('[\u0610-\u061a\u064b-\u065f\u0670]','',text)
    return re.findall(r'[\w\u0600-\u06ff]+',text)

def render_if_requested(audio_path,narration,output_path,profile):
    manifest=os.getenv('PHOTO_MOTION_MANIFEST','').strip()
    if not manifest:return False
    data,_,paths,_=validate(manifest)
    if data['profile']!=profile:raise ValueError('Approved storyboard belongs to another channel profile')
    if digest(audio_path)!=digest(paths[data['audio']['path']]):
        raise ValueError('Generated voice is not the reviewed recording. Review it and update the storyboard before rendering.')
    if words(narration)!=words(data.get('narration_text','')):
        raise ValueError('Current episode script does not match the approved storyboard')
    render(manifest,output_path)
    return True

def render_state_if_requested(root,profile):
    if not os.getenv('PHOTO_MOTION_MANIFEST','').strip():return False
    root=Path(root);episode=json.loads((root/'state/current_episode.json').read_text())
    voice=episode.get('final_audio') or next(iter(episode.get('parts',[])),{}).get('final_audio') or 'downloaded_clips/narration.mp3'
    path=Path(voice)
    if not path.is_absolute():path=root/path
    return render_if_requested(path,str(episode.get('narration','')),root/'output/final_video_full.mp4',profile)
