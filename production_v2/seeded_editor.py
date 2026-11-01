"""Use the retained owner-task draft once, without a writing-provider request."""
from contextlib import contextmanager
from copy import deepcopy
import json
from pathlib import Path
@contextmanager
def seeded_editor(profile,path):
    from professional_motion import editorial
    from production_v2 import general_editorial
    draft=json.loads(Path(path).read_text())
    if not draft.get('suitable') or len(draft.get('scenes',[]))!=8:raise ValueError('Complete retained draft required')
    count=sum(len(s['narration'].split()) for s in draft['scenes'])
    if not 280<=count<=360:raise ValueError('Retained full-film narration length required')
    original=editorial.ask;used=False;categories=list(general_editorial.CATEGORIES[profile])
    category=draft.get('knowledge_category')
    if category in categories:general_editorial.CATEGORIES[profile]=[category]+[c for c in categories if c!=category]
    def ask(*args,**kwargs):
        nonlocal used
        if used:raise RuntimeError('Writing-provider calls are prohibited for the retained manually edited draft')
        used=True;return deepcopy(draft)
    editorial.ask=ask
    try:yield
    finally:editorial.ask=original;general_editorial.CATEGORIES[profile]=categories
