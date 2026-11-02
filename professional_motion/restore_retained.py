"""Restore a prior attempt's immutable delivery artifact before requesting providers."""
import hashlib,io,json,os,zipfile
from pathlib import Path
import requests
from . import editorial

def main():
    request_path=Path(os.environ['FACTORY_REQUEST_PATH']);request=json.loads(request_path.read_text())
    attempt=editorial.registry().get('requested_production',{}).get(request['slot'],{})
    run=attempt.get('source_run')
    if not run:return
    repo=os.environ['GITHUB_REPOSITORY'];headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Accept':'application/vnd.github+json'}
    response=requests.get(f'https://api.github.com/repos/{repo}/actions/runs/{int(run)}/artifacts',headers=headers,timeout=30);response.raise_for_status()
    artifacts=[a for a in response.json()['artifacts'] if not a['expired'] and a['name'].startswith(f'original-voice-{run}')]
    if not artifacts:return
    artifact=max(artifacts,key=lambda a:a['id'])
    response=requests.get(f'https://api.github.com/repos/{repo}/actions/artifacts/{artifact["id"]}/zip',headers=headers,timeout=90);response.raise_for_status()
    if len(response.content)>100_000_000:raise ValueError('Retained delivery artifact exceeds bounded size')
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        files={}
        for info in archive.infolist():
            p=Path(info.filename)
            if p.is_absolute() or '..' in p.parts or info.file_size>100_000_000:raise ValueError('Unsafe retained artifact path or size')
            if not info.is_dir() and len(p.parts)==1 and p.suffix in ('.json','.wav'):files[p.name]=archive.read(info)
    story_bytes=files.get('story.json')
    if story_bytes:
        story=json.loads(story_bytes)
        if story.get('profile')!=request['profile'] or len(story.get('scenes',[]))!=8:raise ValueError('Retained story profile or scene count differs')
        full=' '.join(s['narration'] for s in story['scenes'])
        if 'narration.wav' in files:
            source=json.loads(files['narration.source.json'])
            if source.get('text')!=full or source.get('output_sha256')!=hashlib.sha256(files['narration.wav']).hexdigest():raise ValueError('Retained narration provenance differs')
        data=editorial.registry();row=next((r for r in data['episodes'] if r.get('slot')==request['slot']),None)
        if row and row.get('story') and row['story']['topic_key']!=story['topic_key']:raise ValueError('Retained delivery conflicts with durable topic reservation')
        if row is None:
            row={'slot':request['slot'],'topic_key':story['topic_key'],'canonical_subject':story['canonical_subject'],'title':story['title'],'status':'reserved','story':story}
            data['episodes'].append(row);editorial.save(data)
        out=Path('professional_motion/delivery');out.mkdir(parents=True,exist_ok=True)
        for name,content in files.items():(out/name).write_bytes(content)
        print('Restored exact retained story/voice/ASR from artifact',artifact['id']);return
    draft_bytes=files.get('last-draft.json')
    if draft_bytes and request['profile']!='news':
        path=Path('reviews/requested')/('retained-'+request['slot']+'.json');path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(draft_bytes)
        request['retained_draft']={'path':str(path),'source_run':int(run),'sha256':hashlib.sha256(draft_bytes).hexdigest()}
        request_path.write_text(json.dumps(request,ensure_ascii=False,indent=2)+'\n')
        print('Restored retained original draft; no new full drafting requested')
if __name__=='__main__':main()
