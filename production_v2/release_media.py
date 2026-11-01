"""Review-only GitHub media release helper shared with the fifth repository.

Upload logic retained from film_factory.buffer.ContentPublisher; no Buffer or
social publishing methods are included. Credentials are the current repo's
Actions GitHub token and never appear in retained reports.
"""
import hashlib
import os
from pathlib import Path
import re
import requests
GITHUB_API = 'https://api.github.com'

class ReviewReleaseUploader:
    def __init__(self):
        self.github_token = (os.getenv('GH_RELEASE_TOKEN') or os.getenv('GITHUB_TOKEN') or '').strip()
        self.repository = os.getenv('GITHUB_REPOSITORY', '').strip()
        self.run_id = os.getenv('PRODUCTION_MEDIA_ID', '').strip()

    @staticmethod
    def _headers(token: str, accept: str = "application/vnd.github+json") -> dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
            "Accept": accept,
            "User-Agent": "science-discovery-shorts/1.0",
        }

    def _release_asset_url(self, video_path: Path) -> str:
        if not self.github_token:
            raise RuntimeError("GH_RELEASE_TOKEN أو GITHUB_TOKEN مطلوب لرفع الفيديو إلى رابط عام")
        if not self.repository or "/" not in self.repository:
            raise RuntimeError("GITHUB_REPOSITORY غير مضبوط بصيغة owner/repository")
        if not video_path.is_file() or video_path.stat().st_size <= 0:
            raise RuntimeError(f"ملف الفيديو غير موجود أو فارغ: {video_path}")

        checksum=hashlib.sha256(video_path.read_bytes()).hexdigest()

        # Matrix inputs are empty for immediate runs. Keep a valid, stable ref
        # even if future callers supply punctuation or non-ASCII slot IDs.
        media_id = re.sub(r"[^A-Za-z0-9_-]+", "-", self.run_id).strip("-_") or "local"
        if media_id != self.run_id.strip("-_"):
            media_id += "-" + hashlib.sha256(self.run_id.encode()).hexdigest()[:10]
        tag = f"review-{media_id}"
        release_url = f"{GITHUB_API}/repos/{self.repository}/releases/tags/{tag}"
        response = requests.get(release_url, headers=self._headers(self.github_token), timeout=30)
        if response.status_code == 404:
            response = requests.post(
                f"{GITHUB_API}/repos/{self.repository}/releases",
                headers=self._headers(self.github_token),
                json={
                    "tag_name": tag,
                    "target_commitish": os.getenv("GITHUB_SHA", "").strip() or "main",
                    "name": f"Production v2 review {self.run_id}",
                    "body": "Review-only validation media. Not scheduled or published to social accounts.",
                    "prerelease": True,
                },
                timeout=30,
            )
        if response.status_code == 422:
            # A concurrent uploader may have created the same release.
            existing_release = requests.get(release_url, headers=self._headers(self.github_token), timeout=30)
            if existing_release.status_code == 200:
                response = existing_release
        if response.status_code not in (200, 201):
            raise RuntimeError(f"تعذر إنشاء Release للفيديو: HTTP {response.status_code} {response.text[:300]}")

        release = response.json()
        asset_name = f"review-video-{self.run_id}.mp4"
        existing = next((a for a in release.get("assets", []) if a.get("name") == asset_name), None)
        if existing and existing.get("browser_download_url"):
            digest=existing.get("digest") or existing.get("label")
            if digest!="sha256:"+checksum:raise RuntimeError("Existing release asset does not prove the same video checksum; refusing old or changed media")
            return existing["browser_download_url"]

        upload_url = release.get("upload_url", "").split("{", 1)[0]
        if not upload_url:
            raise RuntimeError("Buffer media upload: GitHub لم يرجع upload_url")
        with video_path.open("rb") as media:
            upload = requests.post(
                upload_url,
                params={"name": asset_name, "label": "sha256:"+checksum},
                headers={**self._headers(self.github_token, "application/vnd.github+json"), "Content-Type": "video/mp4"},
                data=media,
                timeout=(30, 300),
            )
        if upload.status_code not in (200, 201):
            raise RuntimeError(f"تعذر رفع الفيديو إلى GitHub Release: HTTP {upload.status_code} {upload.text[:300]}")
        url = upload.json().get("browser_download_url")
        if not url:
            raise RuntimeError("GitHub لم يرجع رابطًا عامًا للفيديو")
        return url
