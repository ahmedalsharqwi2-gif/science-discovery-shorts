"""Independent Arabic TTS fallback using gTTS; no Cloud project or API key."""
from pathlib import Path


def google_arabic_voice(text: str, output: Path) -> None:
    if not text.strip():
        raise ValueError("Cannot synthesize empty narration")
    from gtts import gTTS
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".building.mp3")
    try:
        gTTS(text=text, lang="ar", lang_check=False, slow=False, timeout=(10, 30)).save(str(temporary))
        if not temporary.exists() or temporary.stat().st_size == 0:
            raise RuntimeError("Free Arabic TTS returned no audio")
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
