"""Render one original, animated Canvas scene to an MP4 without a visual API."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANVAS_FILE = ROOT / "assets" / "motion" / "canvas.html"


def render_scene(output: Path, seconds: float, scene: dict[str, Any], cfg: dict[str, Any]) -> Path:
    """Render a 9:16 Canvas scene with a silent AAC track; narration is mixed later."""
    if seconds <= 0:
        raise ValueError("Canvas scene duration must be positive")
    if not CANVAS_FILE.is_file():
        raise FileNotFoundError(f"Canvas template is missing: {CANVAS_FILE}")

    width = int(cfg.get("width", 1080))
    height = int(cfg.get("height", 1920))
    fps = int(cfg.get("fps", 30))
    if (width, height, fps) != (1080, 1920, 30):
        raise ValueError("Canvas artwork is authored for 1080x1920 at 30fps")

    frames = max(1, round(seconds * fps))
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "profile": str(cfg.get("profile", "science")),
        "text": str(scene.get("text", "")),
        "title": str(scene.get("title", "")),
        "caption": str(scene.get("caption", scene.get("text", ""))),
        "topic": str(scene.get("topic", "")),
        "visual_keywords": scene.get("visual_keywords", []),
        "scene_id": str(scene.get("id", "")),
        "scene_index": int(scene.get("scene_index", 0)),
        "total_scenes": int(scene.get("total_scenes", 1)),
        "duration": float(seconds),
    }

    command = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "image2pipe", "-vcodec", "mjpeg", "-framerate", str(fps), "-i", "pipe:0",
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
        "-map", "0:v:0", "-map", "1:a:0", "-frames:v", str(frames), "-shortest",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(output),
    ]
    # Keep the argument vector shell-free; output paths remain one argv item.
    proc = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        shell=False,
        close_fds=True,
    )
    try:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError("Playwright is required; install scripts/requirements.txt and run `python -m playwright install chromium`.") from exc

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
            try:
                context = browser.new_context(
                    viewport={"width": width, "height": height},
                    device_scale_factor=1,
                    reduced_motion="reduce",
                )
                page = context.new_page()
                page.goto(CANVAS_FILE.as_uri(), wait_until="load")
                page.evaluate("async () => { await document.fonts.ready; return true; }")
                page.evaluate("scene => window.setScene(scene)", payload)
                canvas = page.locator("#stage")
                for index in range(frames):
                    page.evaluate("t => window.renderAt(t)", index / fps)
                    jpeg = canvas.screenshot(type="jpeg", quality=88, animations="disabled")
                    assert proc.stdin is not None
                    proc.stdin.write(jpeg)
                    if index and index % (fps * 10) == 0:
                        print(f"Canvas render: {index}/{frames} frames", flush=True)
                context.close()
            finally:
                browser.close()
    except Exception:
        if proc.stdin and not proc.stdin.closed:
            proc.stdin.close()
        proc.kill()
        proc.wait(timeout=10)
        raise
    else:
        assert proc.stdin is not None
        proc.stdin.close()
        stderr = proc.stderr.read() if proc.stderr else b""
        code = proc.wait(timeout=max(180, int(seconds * 5)))
        if code != 0:
            raise RuntimeError(f"FFmpeg Canvas encode failed ({code}): {stderr.decode('utf-8', 'replace')[-1600:]}")

    if not output.is_file() or output.stat().st_size < 1024:
        raise RuntimeError(f"Canvas render is missing or too small: {output}")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--duration", type=float, default=2.0)
    parser.add_argument("--profile", choices=("science", "history", "horror"), default="science")
    parser.add_argument("--text", default="رسوم توضيحية للمشهد")
    args = parser.parse_args()
    cfg = {"width": 1080, "height": 1920, "fps": 30, "profile": args.profile}
    result = render_scene(args.output, args.duration, {"text": args.text}, cfg)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
