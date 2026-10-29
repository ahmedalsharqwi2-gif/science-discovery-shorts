#!/usr/bin/env python3
"""Use the repository's approved publisher with independent HTTPS media hosting."""
from __future__ import annotations
import argparse, hashlib, importlib, ipaddress, json, os, re, shutil, sys, tempfile
from pathlib import Path
from urllib.parse import quote, urlparse


def media_url(base: str, relative: str) -> str:
    parsed=urlparse(base)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Media hosting requires a public HTTPS base URL')
    if parsed.hostname in {'localhost','localhost.localdomain'}:raise ValueError('Media URL must be reachable by the social platform')
    try:
        if not ipaddress.ip_address(parsed.hostname).is_global:raise ValueError('Media URL must use a public address')
    except ValueError as error:
        if 'public address' in str(error):raise
    return base.rstrip('/')+'/'+quote(relative,safe='/')


def store_media(video: Path, public_root: Path, profile: str, slot: str) -> tuple[str,Path]:
    if profile not in {'science','horror','history','news'}:raise ValueError('Unknown profile')
    digest=hashlib.sha256(video.read_bytes()).hexdigest()
    stem=re.sub(r'[^A-Za-z0-9_-]+','-',slot).strip('-') or 'episode'
    relative=f'{profile}/{stem}-{digest[:20]}.mp4';target=public_root/relative
    target.parent.mkdir(parents=True,exist_ok=True)
    target.parent.chmod(0o755)
    if target.exists():
        if hashlib.sha256(target.read_bytes()).hexdigest()!=digest:raise ValueError('Immutable public media checksum mismatch')
        return relative,target
    with tempfile.NamedTemporaryFile(dir=target.parent,delete=False) as tmp:
        pending=Path(tmp.name)
        with video.open('rb') as source:shutil.copyfileobj(source,tmp)
    pending.chmod(0o644);pending.replace(target)
    return relative,target


def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--profile',required=True);p.add_argument('--slot',required=True);p.add_argument('--due',required=True);p.add_argument('--public-root',type=Path,required=True);p.add_argument('--media-base-url',required=True);args=p.parse_args()
    repo=args.repo.resolve();os.chdir(repo);sys.path.insert(0,str(repo))
    publisher=importlib.import_module('professional_motion.publisher')
    original=publisher.ContentPublisher
    class HostedPublisher(original):
        def _release_asset_url(self,video_path):
            import requests
            relative,target=store_media(Path(video_path),args.public_root,args.profile,args.slot)
            url=media_url(args.media_base_url,relative)
            response=requests.head(url,allow_redirects=True,timeout=45)
            if response.status_code!=200:raise RuntimeError('Public video hosting did not return HTTP 200')
            if int(response.headers.get('Content-Length','-1'))!=target.stat().st_size:raise RuntimeError('Public video hosting returned an unexpected file length')
            return url
    publisher.ContentPublisher=HostedPublisher
    # Existing review approval, duration/hash/source checks, exact Cairo slot,
    # verified channels and provider acceptance receipts remain mandatory.
    publisher.publish(args.profile,args.slot,args.due)

if __name__=='__main__':main()
