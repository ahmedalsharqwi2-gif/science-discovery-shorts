"""Bounded public-domain Commons image fallback; approval still inspects bytes."""
from __future__ import annotations
import hashlib
import json
import subprocess
from pathlib import Path
from urllib.parse import urlparse
import requests
try:
    from scripts.media_audio import media_executable
except ModuleNotFoundError:
    from media_audio import media_executable

API = "https://commons.wikimedia.org/w/api.php"
HEADERS = {"User-Agent": "StoryVideoMedia/1.0 (https://github.com/ahmedalsharqwi2-gif)"}

def search_images(query: str, limit: int = 4) -> list[dict]:
    response = requests.get(API, headers=HEADERS, params={
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": query, "gsrnamespace": 6, "gsrlimit": min(limit, 4),
        "prop": "imageinfo", "iiprop": "url|mime|extmetadata", "iiurlwidth": 1920,
    }, timeout=(10, 25))
    response.raise_for_status()
    result = []
    for page in response.json().get("query", {}).get("pages", {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata", {})
        license_name = meta.get("LicenseShortName", {}).get("value", "").strip()
        # BY/SA assets require publication attribution integration, not just a local log.
        if license_name.lower() not in {"public domain", "cc0"}:
            continue
        url = info.get("thumburl") or info.get("url", "")
        if info.get("mime") not in {"image/jpeg", "image/png"}:
            continue
        if urlparse(url).hostname != "upload.wikimedia.org" or not url.startswith("https://"):
            continue
        result.append({"id": "commons_" + str(page["pageid"]), "url": url,
            "source": "wikimedia_commons", "source_url": info.get("descriptionurl", ""),
            "license": license_name, "title": page.get("title", ""),
            "artist": meta.get("Artist", {}).get("value", ""), "media_type": "animated_image"})
    return result

def animate_image(source: Path, destination: Path, *, width=1920, height=1080, seconds=8.0):
    # Fit and pad keeps maps, captions and historical details inside the frame.
    vf = (f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
          f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,"
          f"zoompan=z='min(zoom+0.00015,1.035)':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':"
          f"d=1:s={width}x{height}:fps=30")
    subprocess.run([media_executable("ffmpeg"), "-y", "-v", "error", "-loop", "1", "-i", str(source),
        "-t", str(seconds), "-vf", vf, "-an", "-c:v", "libx264", "-preset", "veryfast",
        "-pix_fmt", "yuv420p", str(destination)], check=True, timeout=120)

def image_fallback(query: str, topic: str, directory: Path, reviewer, *, historical=False,
                   width=1920, height=1080, limit=2) -> list[dict]:
    accepted = []
    directory.mkdir(parents=True, exist_ok=True)
    try:
        candidates = search_images(query)
    except (requests.RequestException, ValueError):
        print("Commons image search unavailable; no approval granted")
        return accepted
    scene_id = hashlib.sha256((topic + query).encode()).hexdigest()[:12]
    for candidate in candidates:
        if len(accepted) >= limit:
            break
        stem = directory / (candidate["id"] + "_" + scene_id)
        image = stem.with_suffix(".jpg")
        video = stem.with_suffix(".mp4")
        try:
            with requests.get(candidate["url"], headers=HEADERS, stream=True, timeout=(10, 25)) as response:
                response.raise_for_status()
                size = 0
                with image.open("wb") as stream:
                    for chunk in response.iter_content(65536):
                        size += len(chunk)
                        if size > 20 * 1024 * 1024:
                            raise ValueError("Image exceeds download budget")
                        stream.write(chunk)
            animate_image(image, video, width=width, height=height)
            review = reviewer(video, query, topic, historical=historical)
            item = {**candidate, "file": str(video), "pexels_id": candidate["id"],
                    "keyword": query, "visual_review": review, "audio_decision": "VOICE ONLY"}
            video.with_suffix(".source.json").write_text(json.dumps(item, ensure_ascii=False, indent=2))
            accepted.append(item)
        except (requests.RequestException, OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
            video.unlink(missing_ok=True)
            print(f"Commons candidate rejected: {type(exc).__name__}")
        finally:
            image.unlink(missing_ok=True)
    return accepted
