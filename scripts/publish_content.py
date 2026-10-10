# -*- coding: utf-8 -*-
"""Publish a generated science video through Buffer's current GraphQL API.

Buffer does not accept local file uploads.  This module first stores the video as
an immutable GitHub Release asset, then creates one confirmed Buffer post per
configured channel using the public asset URL.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

log = logging.getLogger("pipeline")
BUFFER_ENDPOINT = "https://api.buffer.com"
GITHUB_API = "https://api.github.com"
# The repository secret stores positional channel IDs as TikTok, YouTube,
# Facebook; keep this order identical anywhere the workflow omits an override.
DEFAULT_SERVICES = ("tiktok", "youtube", "facebook")
TIKTOK_TEXT_LIMIT = 2200
BUFFER_FACEBOOK_REEL_LIMIT_SECONDS = 90.0


def _graphql_input(value: object) -> str:
    """Serialize a small Python object as a GraphQL input literal."""
    if isinstance(value, dict):
        return "{" + " ".join(f"{key}: {_graphql_input(item)}" for key, item in value.items()) + "}"
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    return json.dumps(str(value), ensure_ascii=False)


def build_social_description(topic: str, narration: str, source_urls: list[str] | None = None) -> str:
    """Create a hashtag-only description without publishing narration or source links.

    ``source_urls`` remains an accepted argument for caller compatibility, but
    scientific source URLs and the full extracted narration are deliberately
    kept out of public descriptions. The video title is supplied separately.
    """
    topic = " ".join(str(topic or "").split()).strip() or "اكتشاف علمي جديد"
    tags = ["#علوم", "#معلومة_علمية", "#اكتشافات"]
    lowered = topic.lower()
    if any(word in lowered for word in ("فضاء", "كون", "كوكب", "نجمة", "ثقب")):
        tags.insert(1, "#فضاء")
    return " ".join(dict.fromkeys(tags))


def post_text_for_service(title: str, description: str, service: str) -> str:
    """Prepare channel-safe text without changing the complete video asset."""
    title = " ".join(str(title or "").split()).strip() or "اكتشاف علمي جديد"
    text = f"{title}\n\n{str(description or '').strip()}".strip()
    if service != "tiktok" or len(text) <= TIKTOK_TEXT_LIMIT:
        return text
    suffix = "\n\n#علوم #اكتشافات"
    prefix = text[: TIKTOK_TEXT_LIMIT - len(suffix)]
    prefix = prefix.rsplit(" ", 1)[0].rstrip() if len(prefix) < len(text) else prefix
    return prefix.rstrip() + suffix


def probe_video_duration(video_path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


class ContentPublisher:
    """Upload media and create verified, scheduled Buffer posts."""

    def __init__(self):
        self.buffer_api_key = os.getenv("BUFFER_API_KEY", "").strip()
        self.github_token = (os.getenv("GH_RELEASE_TOKEN") or os.getenv("GITHUB_TOKEN") or "").strip()
        self.repository = os.getenv("GITHUB_REPOSITORY", "").strip()
        self.run_id = os.getenv("GITHUB_RUN_ID", "local").strip()
        self.schedule_mode = os.getenv("BUFFER_SCHEDULE_MODE", "addToQueue").strip()

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

        tag = f"auto-publish-{self.run_id}"
        release_url = f"{GITHUB_API}/repos/{self.repository}/releases/tags/{tag}"
        response = requests.get(release_url, headers=self._headers(self.github_token), timeout=30)
        if response.status_code == 404:
            response = requests.post(
                f"{GITHUB_API}/repos/{self.repository}/releases",
                headers=self._headers(self.github_token),
                json={
                    "tag_name": tag,
                    "name": f"Auto publish media {self.run_id}",
                    "body": "Temporary public media asset for scheduled Buffer publishing.",
                    "prerelease": True,
                },
                timeout=30,
            )
        if response.status_code not in (200, 201):
            raise RuntimeError(f"تعذر إنشاء Release للفيديو: HTTP {response.status_code} {response.text[:300]}")

        release = response.json()
        asset_name = f"science-video-{self.run_id}.mp4"
        existing = next((a for a in release.get("assets", []) if a.get("name") == asset_name), None)
        if existing and existing.get("browser_download_url"):
            return existing["browser_download_url"]

        upload_url = release.get("upload_url", "").split("{", 1)[0]
        if not upload_url:
            raise RuntimeError("Buffer media upload: GitHub لم يرجع upload_url")
        with video_path.open("rb") as media:
            upload = requests.post(
                upload_url,
                params={"name": asset_name},
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

    @staticmethod
    def _channel_map(raw: str, services: tuple[str, ...]) -> dict[str, str]:
        """Accept JSON, service=id pairs, or IDs aligned with service order."""
        raw = (raw or "").strip()
        if not raw:
            return {}
        try:
            value = json.loads(raw)
            if isinstance(value, dict):
                return {str(k).strip().lower(): str(v).strip() for k, v in value.items() if str(v).strip()}
        except json.JSONDecodeError:
            pass
        tokens = [x.strip() for x in raw.replace("\n", ",").split(",") if x.strip()]
        result: dict[str, str] = {}
        positional: list[str] = []
        for token in tokens:
            if "=" in token:
                key, value = token.split("=", 1)
                result[key.strip().lower()] = value.strip()
            elif ":" in token and token.split(":", 1)[0].strip().lower() in services:
                key, value = token.split(":", 1)
                result[key.strip().lower()] = value.strip()
            else:
                positional.append(token)
        for service, channel_id in zip(services, positional):
            result.setdefault(service, channel_id)
        return {k: v for k, v in result.items() if k in services and v}

    def _create_buffer_post(
        self,
        channel_id: str,
        text: str,
        media_url: str,
        due_at: Optional[str],
        service: str = "tiktok",
        title: str = "اكتشاف علمي جديد",
        facebook_type: str = "reel",
    ) -> dict:
        text_json = json.dumps(text, ensure_ascii=False)
        channel_json = json.dumps(channel_id)
        media_json = json.dumps(media_url)
        metadata = None
        if service == "youtube":
            metadata = {"youtube": {"title": title[:100] or "اكتشاف علمي جديد", "categoryId": "27", "privacy": "public", "madeForKids": False, "notifySubscribers": False}}
        elif service == "instagram":
            metadata = {"instagram": {"type": "reel", "shouldShareToFeed": True}}
        elif service == "facebook":
            metadata = {"facebook": {"type": facebook_type}}
        if service == "youtube":
            metadata_clause = (
                "metadata: {youtube: {title: "
                + json.dumps(title[:100] or "اكتشاف علمي جديد", ensure_ascii=False)
                + ', categoryId: "27", privacy: public, madeForKids: false, notifySubscribers: false}}'
            )
        elif service == "instagram":
            metadata_clause = "metadata: {instagram: {type: reel, shouldShareToFeed: true}}"
        elif service == "facebook":
            metadata_clause = f"metadata: {{facebook: {{type: {facebook_type}}}}}"
        else:
            metadata_clause = ""
        if self.schedule_mode == "customScheduled":
            if not due_at:
                raise RuntimeError("BUFFER_SCHEDULE_MODE=customScheduled يتطلب PUBLISH_DUE_AT")
            due_json = json.dumps(due_at)
            scheduling = f"mode: customScheduled, dueAt: {due_json}"
        else:
            scheduling = "mode: addToQueue"
        query = f"""
        mutation CreateSciencePost {{
          createPost(input: {{
            text: {text_json}
            channelId: {channel_json}
            schedulingType: automatic
            {scheduling}
            {metadata_clause}
            assets: [{{ video: {{ url: {media_json} }} }}]
          }}) {{
            ... on PostActionSuccess {{ post {{ id dueAt }} }}
            ... on MutationError {{ message }}
          }}
        }}
        """
        response = requests.post(
            BUFFER_ENDPOINT,
            headers={"Authorization": f"Bearer {self.buffer_api_key}", "Content-Type": "application/json"},
            json={"query": query},
            timeout=60,
        )
        if response.status_code != 200:
            raise RuntimeError(f"Buffer HTTP {response.status_code}: {response.text[:300]}")
        payload = response.json()
        if payload.get("errors"):
            raise RuntimeError(f"Buffer GraphQL: {json.dumps(payload['errors'], ensure_ascii=False)[:500]}")
        result = payload.get("data", {}).get("createPost", {})
        post = result.get("post")
        if not post or not post.get("id"):
            raise RuntimeError(f"Buffer لم يؤكد إنشاء المنشور: {json.dumps(result, ensure_ascii=False)[:500]}")
        return post

    def publish_to_buffer(
        self,
        video_path: Path,
        title: str,
        description: str,
        channel_ids: list[str],
        schedule_time: Optional[datetime] = None,
    ) -> bool:
        if not self.buffer_api_key:
            raise RuntimeError("BUFFER_API_KEY غير موجود؛ أوقفنا التشغيل بدل الادعاء بنجاح النشر")
        services = tuple(x.strip().lower() for x in os.getenv("PUBLISH_CHANNELS", ",".join(DEFAULT_SERVICES)).split(",") if x.strip())
        configured = self._channel_map(os.getenv("BUFFER_CHANNEL_IDS", ""), services)
        if not configured and channel_ids:
            configured = self._channel_map(",".join(channel_ids), services)
        if not configured:
            raise RuntimeError("لم يتم العثور على BUFFER_CHANNEL_IDS صالحة للقنوات المستهدفة")

        media_url = self._release_asset_url(video_path)
        due_at = os.getenv("PUBLISH_DUE_AT", "").strip() or (schedule_time.isoformat() if schedule_time else None)
        failures: dict[str, str] = {}
        skipped: dict[str, str] = {}
        successes: dict[str, dict] = {}
        for service in services:
            channel_id = configured.get(service)
            if not channel_id:
                failures[service] = "لا يوجد channel ID مضبوط"
                continue
            video_duration = None
            facebook_type = "reel"
            try:
                if service == "facebook":
                    video_duration = probe_video_duration(video_path)
                    if video_duration > BUFFER_FACEBOOK_REEL_LIMIT_SECONDS:
                        # Meta now accepts longer Reels. Buffer's deployed Reel
                        # validator can still reject at 90s, so try its standard
                        # video-post type first rather than shortening the story.
                        facebook_type = "post"
                        log.info("Trying Facebook standard video-post type for %.1fs vertical video", video_duration)
                post_text = post_text_for_service(title, description, service)
                post = self._create_buffer_post(
                    channel_id, post_text, media_url, due_at, service, title, facebook_type
                )
                successes[service] = post
                log.info("✓ Buffer confirmed %s post=%s dueAt=%s", service, post.get("id"), post.get("dueAt"))
            except Exception as exc:  # keep independent channel results visible
                message = str(exc).casefold()
                if service == "facebook" and video_duration and video_duration > BUFFER_FACEBOOK_REEL_LIMIT_SECONDS and (
                    "no longer than 1m 30s" in message or "90 seconds" in message
                ):
                    skipped[service] = (
                        f"Buffer rejected the full {video_duration:.1f}s video even as a standard post: {exc}; "
                        "the complete master was preserved and not cut into an excerpt"
                    )
                    log.warning("↷ Buffer skipped %s after its duration rejection: %s", service, skipped[service])
                    continue
                failures[service] = str(exc)
                log.error("✗ Buffer failed for %s: %s", service, exc)

        log.info("Buffer result: %d/%d channels confirmed", len(successes), len(services))
        if skipped:
            log.warning("Skipped incompatible channels: %s", json.dumps(skipped, ensure_ascii=False))
        if failures:
            log.error("Unpublished channels: %s", json.dumps(failures, ensure_ascii=False))
        eligible_channels = len(services) - len(skipped)
        return eligible_channels > 0 and len(successes) == eligible_channels

    def save_metadata(self, metadata_path: Path, title: str, description: str, tags: list[str], video_path: Path) -> bool:
        try:
            metadata = {
                "title": title,
                "description": description,
                "tags": tags,
                "video_path": str(video_path),
                "published_at": datetime.now().isoformat(),
            }
            metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
            log.info("Metadata saved to %s", metadata_path)
            return True
        except Exception as exc:
            log.error("Failed to save metadata: %s", exc)
            return False
