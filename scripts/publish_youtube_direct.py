"""رفع الفيديو الكامل مباشرة على يوتيوب عبر YouTube Data API v3، بديلًا
عن Buffer اللي لا يدعم فيديوهات يوتيوب الطويلة (Long-form) إطلاقًا —
Buffer بيدعم YouTube Shorts فقط (موثّق رسميًا من Buffer نفسها)، فأي
محاولة لنشر فيديو أفقي أطول من 3 دقايق عن طريقه هترجع دايمًا:
"Video must be no longer than 3 minutes / must be vertical for
YouTube Shorts" — بغض النظر عن أي تعديل في الـ metadata أو النص.

هذا السكريبت مستقل تمامًا عن publish_buffer.py، ولا يمس نشر الشورتس أو
فيسبوك أو انستجرام، اللي تفضل شغالة عبر Buffer زي ما هي.

المتغيرات المطلوبة (GitHub Secrets):
    YT_CLIENT_ID
    YT_CLIENT_SECRET
    YT_REFRESH_TOKEN

الاستخدام:
    python scripts/publish_youtube_direct.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from pathlib import Path

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload
except ImportError:  # Optional locally; CI installs these from requirements.
    Request = Credentials = build = MediaFileUpload = None
    class HttpError(Exception):
        pass

SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent
EPISODE_PATH = ROOT_DIR / "state" / "current_episode.json"
VIDEO_PATH = ROOT_DIR / "output" / "final_video_full.mp4"
# يُحدَّث في كل مرة يتجدّد فيها access token بنجاح، عشان
# scripts/check_youtube_token_age.py يقدر يحسب منه كام يوم فاضل قبل ما
# Google يلغي صلاحية الـ refresh_token (7 أيام لتطبيق في وضع Testing).
TOKEN_STATE_PATH = ROOT_DIR / "state" / "yt_token_last_success.json"

TOKEN_URI = "https://oauth2.googleapis.com/token"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# نفس تصنيف Entertainment المستخدم في publish_buffer.py، قابل للتغيير
# عبر متغيّر بيئة لو احتجت تصنيفًا مختلفًا.
YT_CATEGORY_ID = os.environ.get("YT_CATEGORY_ID", "24")
YT_PRIVACY = os.environ.get("YT_PRIVACY", "public")  # public | unlisted | private
YT_MADE_FOR_KIDS = os.environ.get("YT_MADE_FOR_KIDS", "false").lower() == "true"
# الفيديو الطويل أداؤه أفضل مساءً (وقت فراغ فعلي عند المشاهد) بعكس
# الشورتس اللي أداؤها أفضل صبحًا/ضهرًا. لو الـ workflow بيشتغل صباحًا،
# القيمة دي بتأجل النشر الفعلي على يوتيوب لنفس اليوم مساءً بدل النشر
# الفوري وقت الرفع — بنفس منطق FULL_VIDEO_DELAY_HOURS في

# publish_buffer.py، ولازم تتظبط بنفس القيمة عشان يوتيوب وباقي المنصات
# ينشروا في نفس التوقيت تقريبًا.
FULL_VIDEO_DELAY_HOURS = float(os.environ.get("FULL_VIDEO_DELAY_HOURS", "0"))

def publish_target_utc(hour: int = 17) -> datetime:
    """Return the next 17:00 Africa/Cairo converted to UTC.
    This is absolute scheduling, so generation duration does not shift the post.
    """
    now = datetime.now(timezone.utc)
    cairo = now.astimezone(ZoneInfo("Africa/Cairo"))
    target = cairo.replace(hour=hour, minute=0, second=0, microsecond=0)
    if target <= cairo:
        target += timedelta(days=1)
    return target.astimezone(timezone.utc)


def scheduled_publish_utc(default_hour: int = 17) -> datetime:
    """Use the workflow's exact final slot when one was computed."""
    raw = os.environ.get("PUBLISH_DUE_AT", "").strip()
    if raw:
        from scripts.daily_schedule import validate_slot
        return validate_slot(raw).astimezone(timezone.utc)
    return publish_target_utc(default_hour)




def load_credentials() -> Credentials:
    if Credentials is None or Request is None:
        raise RuntimeError("حزم Google YouTube غير مثبتة؛ سيتم تخطي النشر مع استمرار الـworkflow")
    client_id = os.environ.get("YT_CLIENT_ID", "").strip()
    client_secret = os.environ.get("YT_CLIENT_SECRET", "").strip()
    tokens = [os.environ.get("YT_REFRESH_TOKEN", "").strip(), os.environ.get("YT_REFRESH_TOKEN_FALLBACK", "").strip()]
    if not client_id or not client_secret or not any(tokens):
        missing = [name for name, value in (("YT_CLIENT_ID", client_id), ("YT_CLIENT_SECRET", client_secret), ("YT_REFRESH_TOKEN/YT_REFRESH_TOKEN_FALLBACK", any(tokens))) if not value]
        raise RuntimeError("متغيرات يوتيوب ناقصة: " + ", ".join(missing))
    errors = []
    unique_tokens = list(dict.fromkeys(token for token in tokens if token))
    for index, refresh_token in enumerate(unique_tokens):
        credentials = Credentials(token=None, refresh_token=refresh_token, token_uri=TOKEN_URI, client_id=client_id, client_secret=client_secret, scopes=SCOPES)
        try:
            credentials.refresh(Request())
            _record_token_success()
            if index:
                print("⚠️ تم استخدام YT_REFRESH_TOKEN_FALLBACK بعد فشل التوكن الأساسي")
            return credentials
        except Exception as exc:
            errors.append(f"token-{index + 1}: {exc}")
            print(f"⚠️ فشل تجديد توكن يوتيوب ({index + 1}/{len(unique_tokens)}): {exc}")
    raise RuntimeError("تعذر تجديد أي Refresh Token: " + " | ".join(errors)[-800:])

def _record_token_success() -> None:
    """يسجّل تاريخ آخر مرة نجح فيها تجديد access token بنجاح، عشان
    check_youtube_token_age.py يقدر يحسب منه قرب انتهاء صلاحية
    refresh_token (7 أيام لتطبيق في وضع Testing) ويحذّرنا قبل ما ينتهي
    فعليًا. فشل الكتابة هنا (مثلًا مجلد state غير قابل للكتابة) لا يوقف
    النشر — دي مجرد بيانات مساعدة للتنبيه، مش جزء أساسي من عملية الرفع."""
    try:
        TOKEN_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_STATE_PATH.write_text(
            json.dumps(
                {"last_success_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    except OSError as exc:
        print(f"⚠️ تعذّر تسجيل تاريخ نجاح التوكن (غير خطير): {exc}")


def load_title_and_description() -> tuple[str, str]:
    if not EPISODE_PATH.exists():
        raise RuntimeError(f"state/current_episode.json غير موجود: {EPISODE_PATH}")
    episode = json.loads(EPISODE_PATH.read_text(encoding="utf-8"))
    from scripts.channel_brand import display_title
    title = display_title(episode.get("title", "Horror Episode"))
    caption = str(episode.get("caption", "")).strip() or title
    # وصف يوتيوب بيسمح بحد أقصى 5000 حرف، الكابشن الحالي عادة أقصر بكتير.
    description = caption[:4900]
    return title, description


def upload_video(youtube, video_path: Path, title: str, description: str) -> str:
    status: dict = {"selfDeclaredMadeForKids": YT_MADE_FOR_KIDS, "containsSyntheticMedia": True}
    from scripts.publication_state import immediate_requested
    if immediate_requested():
        status["privacyStatus"] = "public"
    elif os.getenv("PUBLISH_DUE_AT"):
        # جدولة نشر مؤجَّلة: يوتيوب بيطلب privacyStatus="private" مع
        # publishAt (ISO 8601)، وبيحوّل الفيديو تلقائيًا لـpublic في
        # الموعد المحدد بالظبط — الفيديو مش هيكون مرئي لحد ده الموعد.
        publish_at = scheduled_publish_utc(17)
        status["privacyStatus"] = "private"
        status["publishAt"] = publish_at.isoformat(timespec="seconds").replace("+00:00", "Z")
        print(f"⏰ الفيديو مجدول ينشر تلقائيًا عند: {status['publishAt']} UTC")
    else:
        status["privacyStatus"] = YT_PRIVACY

    body = {
        "snippet": {
            "title": title or "Horror Episode",
            "description": description,
            "tags": json.loads(EPISODE_PATH.read_text()).get("tags", []),
            "defaultAudioLanguage": "ar",
            "categoryId": YT_CATEGORY_ID,
        },
        "status": status,
    }
    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        chunksize=8 * 1024 * 1024,
        resumable=True,
    )
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  📤 جاري الرفع... {int(status.progress() * 100)}%")
    return response["id"]


def main() -> int:
    try:
        from scripts.publication_state import accepted_receipt, require_services
        if accepted_receipt("youtube"):
            print("YouTube already accepted this slot; reusing stored receipt")
            return 0
        if os.getenv("PUBLICATION_RECEIPTS_ENABLED", "false").lower() == "true":
            require_services({"youtube"})
        if not VIDEO_PATH.exists() or VIDEO_PATH.stat().st_size == 0:
            raise RuntimeError(f"الفيديو الكامل غير موجود: {VIDEO_PATH}")
        title, description = load_title_and_description()
        credentials = load_credentials()
        youtube = build("youtube", "v3", credentials=credentials)
        print(f"📤 جاري رفع الفيديو الكامل على يوتيوب: {title}")
        try:
            video_id = upload_video(youtube, VIDEO_PATH, title, description)
        except HttpError as exc:
            status = getattr(exc.resp, "status", None)
            if status not in (401, 403):
                raise
            print(f"⚠️ YouTube أعاد HTTP {status}؛ إعادة تجديد التوكن والمحاولة مرة واحدة")
            credentials = load_credentials()
            video_id = upload_video(build("youtube", "v3", credentials=credentials), VIDEO_PATH, title, description)
        if os.getenv("PUBLICATION_RECEIPTS_ENABLED", "false").lower() == "true":
            from scripts.publication_state import record_receipt
            record_receipt("youtube", video_id, os.getenv("PUBLISH_DUE_AT"))
        print(f"✅ تم قبول فيديو يوتيوب: https://youtu.be/{video_id}")
    except Exception as exc:
        print(f"❌ YouTube publication failed: {exc}")
        return 1
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
