"""Pre-dispatch editorial contract, not a replacement for independent review."""
from visual_contract import load_template,validate_hook,validate_accent,require_source_support

def validate_episode(story, source_text=None):
 t=load_template();profile=t['channel']
 if story.get('profile',profile)!=profile:raise ValueError('Cross-channel episode')
 if 'palette' in story or 'visual_template' in story:raise ValueError('Per-episode visual overrides forbidden')
 hook=validate_hook(story.get('hook_line'),max_words=t['hook']['max_words'],profile=profile,source_terms=story.get('hook_source_terms',()))
 validate_accent(story['title'],story.get('title_accent_word'),prefix=t.get('public_title_prefix',t.get('title_prefix','')))
 if not story.get('scenes') or not story['scenes'][0]['narration'].startswith(hook):raise ValueError('Narration must start with the exact retained hook')
 for scene in story['scenes']:validate_accent(scene['label'],scene.get('title_accent_word'))
 if source_text is not None and profile!='stickman':require_source_support(hook,story.get('hook_evidence_quote'),source_text,story.get('hook_review',{}))
 return t

def validate_timing(story,timing):
 t=validate_episode(story)
 groups=timing.get('caption_groups',[])
 if not groups or groups[0]['text']!=story['hook_line'] or groups[0]['start']!=0:raise ValueError('First caption must be the exact hook at frame zero')
 if groups[0]['end']>t['hook']['max_seconds']:raise ValueError('Measured hook exceeds duration cap; rewrite before new synthesis')
 if any(len(c['text'].split())>4 for c in groups[1:]):raise ValueError('Caption exceeds four-word budget')
 return [{'index':i,'duration':c['end']-c['start'],'reason':'measured alignment shorter than 0.9 seconds; not retimed'} for i,c in enumerate(groups) if c['end']-c['start']<.9]


def validate_first_audio_frame(path):
 import subprocess,array
 raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-t',str(1/30),'-f','s16le','-ar','48000','-ac','1','-'])
 samples=array.array('h');samples.frombytes(raw)
 if not samples or max(abs(v) for v in samples)<33:raise ValueError('First video frame contains no audible speech; preserve the raw voice and correct onset with provenance before acceptance')
 return True
