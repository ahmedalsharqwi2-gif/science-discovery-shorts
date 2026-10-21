import os
import tempfile
import unittest
import re
import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch

from scripts.assemble_video import _caption_text, write_ass_subtitles
from scripts.generate_voice import normalize_spoken_text


def write_fixture_subtitles(text, duration, path):
    """Typography fixture: known word timestamps, independent of ASR availability."""
    words = text.split()
    events = [{"text": word, "offset": i * duration / len(words), "duration": duration / len(words)}
              for i, word in enumerate(words)]
    with patch("scripts.assemble_video.align_words_with_whisper", return_value=events):
        write_ass_subtitles(text, duration, path, audio_path=path.with_suffix(".wav"))


class VideoAssemblyTests(unittest.TestCase):
    def test_arabic_caption_payload_has_no_bidi_controls_that_break_shaping(self):
        caption = _caption_text("هذا نص عربي سليم".split())

        self.assertNotIn("\u200f", caption)
        self.assertNotIn("\u200e", caption)
        self.assertEqual(caption, "هذا نص عربي سليم")

    def test_active_arabic_caption_preserves_logical_source_order(self):
        caption = _caption_text("الدم داخل الأوعية بسرعة".split(), active_index=0)
        self.assertTrue(caption.startswith(r"{\c&H000000FF&}الدم"))
        self.assertIn("الدم داخل الأوعية بسرعة", caption.replace(r"{\c&H000000FF&}", "").replace(r"{\c&H00FFFFFF&}", ""))

    def test_subtitles_keep_four_word_line_and_highlight_each_word(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "captions.ass"
            write_fixture_subtitles(
                "واحد اثنان ثلاثة أربعة خمسة ستة سبعة",
                7.0,
                path,
            )
            text = path.read_text(encoding="utf-8")
            dialogue_lines = [line for line in text.splitlines() if line.startswith("Dialogue:")]
            self.assertEqual(len(dialogue_lines), 25)
            self.assertNotIn(r"\N", text)
            self.assertIn("واحد", text)
            self.assertIn("اثنان", text)
            self.assertIn("ثلاثة", text)
            self.assertIn("أربعة", text)
            self.assertIn(r"\c&H000000FF&}", text)
            self.assertIn("Noto Naskh Arabic", text)
            self.assertGreaterEqual(text.count(r"\c&H000000FF&}"), 7)
            self.assertTrue(all(r"\pos(" in line for line in dialogue_lines))
            # Each event contains one Arabic word; libass never has to reorder
            # a mixed-color multiword paragraph. The first logical word sits
            # at the right of the line, as Arabic is read right-to-left.
            self.assertTrue(all(len(re.sub(r"\{[^}]*\}", "", line.split(",", 9)[-1]).split()) == 1 for line in dialogue_lines))
            first_word = next(line for line in dialogue_lines if r"\c&H000000FF&}واحد" in line)
            center_x = int(re.search(r"\\pos\((\d+),", first_word).group(1))
            self.assertGreater(center_x, 540)

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg is required for the rendered RTL regression")
    def test_ffmpeg_places_active_first_arabic_word_on_the_right(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as directory:
            ass_path = Path(directory) / "reef.ass"
            frame_path = Path(directory) / "frame.png"
            write_fixture_subtitles("الشعاب المرجانية تحمي السواحل", 4.0, ass_path)
            subprocess.run([
                "ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                "color=c=black:s=1080x1920:r=30:d=1", "-vf", f"subtitles='{ass_path}'",
                "-frames:v", "1", str(frame_path),
            ], check=True)
            image = Image.open(frame_path).convert("RGB")
            red_pixels = [
                x for y in range(image.height) for x in range(image.width)
                if (lambda pixel: pixel[0] > 150 and pixel[1] < 110 and pixel[2] < 110)(image.getpixel((x, y)))
            ]
            self.assertTrue(red_pixels, "active word was not rendered in red")
            self.assertGreater(sum(red_pixels) / len(red_pixels), image.width / 2)

    def test_spoken_text_removes_formatting_and_repeated_pauses(self):
        text = normalize_spoken_text("  هذا\n**نص**، ،؛؛  مهم...  ")
        self.assertEqual(text, "هذا نص، مهم…")

    def test_captions_are_top_centered_below_mobile_notch_safe_area(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "captions.ass"
            write_fixture_subtitles("نص تجريبي للترجمة العربية", 5.0, path)
            text = path.read_text(encoding="utf-8")
        self.assertIn(",8,70,70,260,1", text)

    @patch("scripts.assemble_video.align_words_with_whisper", side_effect=RuntimeError("Whisper alignment too weak: 77/157 words"))
    @patch.dict(os.environ, {"QUALITY_GATES_BLOCKING": "true"})
    def test_weak_whisper_alignment_blocks_publication(self, align):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "captions.ass"
            with self.assertRaisesRegex(RuntimeError, "فشلت محاذاة"):
                write_ass_subtitles("واحد اثنان ثلاثة أربعة خمسة ستة سبعة ثمانية", 8.0, path,
                                    audio_path=Path(directory) / "narration.mp3")
            self.assertFalse(path.exists())
        align.assert_called_once()

    @patch("scripts.assemble_video.align_words_with_whisper", side_effect=RuntimeError("word timings unavailable"))
    @patch.dict(os.environ, {"QUALITY_GATES_BLOCKING": "false", "CAPTION_ALIGNMENT_REQUIRED": "false"})
    def test_nonblocking_alignment_uses_plain_captions(self, align):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "captions.ass"
            write_ass_subtitles("واحد اثنان ثلاثة أربعة", 8.0, path,
                                audio_path=Path(directory) / "narration.mp3")
            captions = path.read_text(encoding="utf-8")
            self.assertIn("واحد", captions)
            self.assertIn("أربعة", captions)
            self.assertIn("Dialogue:", captions)
            self.assertNotIn(r"\c&H000000FF&", captions)
        align.assert_called_once()


if __name__ == "__main__":
    unittest.main()
