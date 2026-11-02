"""Inspect actual media and preserve full decoder exit status."""
import hashlib
import json
import math
from fractions import Fraction
from pathlib import Path
import subprocess
from .schedule import require_duration


def verify(path, *, profile=None):
    video = Path(path).resolve()
    if not video.is_file() or video.stat().st_size == 0:
        raise ValueError('Missing or empty MP4')
    probe = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-count_frames',
                            '-of', 'json', str(video)], check=True, capture_output=True, text=True)
    data = json.loads(probe.stdout)
    duration = require_duration(data['format']['duration'],profile=profile)
    streams = data.get('streams', [])
    visual = [s for s in streams if s.get('codec_type') == 'video']
    audio = [s for s in streams if s.get('codec_type') == 'audio']
    if len(visual) != 1 or (visual[0].get('width'), visual[0].get('height')) != (1080, 1920):
        raise ValueError('Exactly one 1080x1920 video stream required')
    if not audio:
        raise ValueError('Narration audio stream required')
    def stream_duration(stream):
        try:
            value = float(stream['duration'])
        except (KeyError, TypeError, ValueError):
            try:
                value = int(stream['duration_ts']) * float(Fraction(stream['time_base']))
            except (KeyError, TypeError, ValueError, ZeroDivisionError) as error:
                raise ValueError('Explicit actual video/audio stream duration required') from error
        if not math.isfinite(value) or abs(value - duration) > .15:
            raise ValueError('Actual video/audio stream length does not match complete film duration')
        return value
    video_duration = stream_duration(visual[0])
    audio_duration = stream_duration(audio[0])
    try:
        fps = float(Fraction(visual[0]['avg_frame_rate']))
        frames = int(visual[0]['nb_read_frames'])
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as error:
        raise ValueError('Decoded video frame count and average frame rate required') from error
    if not math.isfinite(fps) or fps <= 0 or frames <= 0 or abs(frames / fps - video_duration) > .15:
        raise ValueError('Decoded video frames do not cover the entire film')
    decoded = subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(video),
                              '-map', '0:v:0', '-map', '0:a:0', '-f', 'null', '-'],
                             capture_output=True, text=True)
    if decoded.returncode != 0:
        raise ValueError('Full video/audio decode failed: ' + decoded.stderr[-1000:])
    digest = hashlib.sha256()
    with video.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return {'validated': True, 'path': str(video), 'sha256': digest.hexdigest(),
            'decode': 'PASS', 'width': 1080, 'height': 1920, 'duration': duration,
            'video_duration': video_duration, 'audio_duration': audio_duration,
            'decoded_video_frames': frames, 'fps': fps,
            'video_codec': visual[0].get('codec_name'), 'audio_codec': audio[0].get('codec_name'),
            'bytes': video.stat().st_size,
            'limitation': 'Stream/decode validation does not prove narration correctness, novelty, or editorial approval'}
