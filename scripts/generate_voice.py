"""One approved Gemini Charon narration, with no alternate voice provider."""
import os
import re
from pathlib import Path

def normalize_spoken_text(text: str) -> str:
    """Flatten model formatting that makes Edge TTS pause between fragments.

    The narration remains unchanged for captions and fact-checking; only the
    spoken payload is normalized. Markdown bullets, line breaks, and repeated
    punctuation are common causes of unnatural stop-start Arabic delivery.
    """
    value = str(text or "")
    value = re.sub(r"[`*_#]+", "", value)
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(r"([،؛:؟!])\s*[،؛:؟!]+", r"\1", value)
    value = re.sub(r"\.{2,}", "…", value)
    return value

class VoiceGenerator:
    def __init__(self, output_dir=Path("output")):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, text, output_path=None, engine="gemini", voice=None):
        if os.getenv("TTS_ENGINE", engine).lower() != "gemini":
            raise ValueError("Production requires Gemini Charon")
        if voice not in (None, "Charon"):
            raise ValueError("Unapproved speaker")
        from voice_provider.client import generate
        path = Path(output_path or self.output_dir / "narration.mp3")
        generate(normalize_spoken_text(text), path)
        return path, True
