"""Bind channel direction and licensed scene assets to the exact retained story."""
import hashlib,json
from pathlib import Path
from .identity import scene_plan
from .visual_assets import enrich
def prepare(story,evidence):
 delivery=Path('professional_motion/delivery');public=Path('remotion_motion/public');plan=scene_plan(story)
 plan['story_sha256']=hashlib.sha256((delivery/'story.json').read_bytes()).hexdigest();plan['audio_sha256']=hashlib.sha256((delivery/'narration.wav').read_bytes()).hexdigest()
 assets=enrich(story,plan,public,delivery)
 if story['profile'] in ('history','horror'):
  from .photo_backgrounds import render
  timing=json.loads((delivery/'timing.json').read_text());render(story,timing,plan,public)
 plan['licensed_asset_evidence']=assets;plan['external_image_failure_is_not_a_claim_of_source_footage']=True
 raw=json.dumps(plan,ensure_ascii=False,indent=2)+'\n';(public/'identity-plan.json').write_text(raw);(delivery/'identity-plan.json').write_text(raw)
 evidence.extend(a for a in assets if a.get('available'));return plan
