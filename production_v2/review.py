"""Render an isolated, explicitly nonpublishable candidate with authentic narration.

No legacy output, registry, topic history, or receipts are written by this tool.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import wave


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def bundle(delivery, profile):
    delivery = Path(delivery).resolve()
    story_path, audio_path = delivery / 'story.json', delivery / 'narration.wav'
    story = json.loads(story_path.read_text())
    timing = json.loads((delivery / 'timing.json').read_text())
    if story.get('profile') != profile:
        raise ValueError('Delivery belongs to another channel')
    duration = float(timing['duration'])
    if not math.isfinite(duration) or not 120 <= duration < 180:
        raise ValueError('A complete 120 to under 180 second narrated film is required')
    if timing.get('story_sha256') != digest(story_path) or timing.get('audio_sha256') != digest(audio_path):
        raise ValueError('Story or original narration changed after measured alignment')
    if not story.get('topic_key') or timing.get('topic_key') != story['topic_key']:
        raise ValueError('Measured timing and authored topic differ')
    if len(story.get('scenes', [])) != 8 or len(timing.get('scenes', [])) != 8:
        raise ValueError('All eight authored and measured scenes are required')
    starts = [float(scene['start']) for scene in timing['scenes']]
    if not all(math.isfinite(value) for value in starts) or starts[0] != 0 or any(a >= b for a, b in zip(starts, starts[1:])) or starts[-1] >= duration:
        raise ValueError('Scene timing is incomplete or unordered')
    for index, (authored, measured) in enumerate(zip(story['scenes'], timing['scenes'])):
        end = float(measured.get('end', float('nan')))
        if measured.get('id') != authored.get('id') or not math.isfinite(end) or not starts[index] < end <= duration:
            raise ValueError('Every measured scene must match its authored identity and valid end time')
        if index + 1 < len(starts) and end > starts[index + 1] + .001:
            raise ValueError('Measured scenes overlap')
    if not .9 <= float(timing.get('coverage', 0)) <= 1:
        raise ValueError('Measured narration coverage is insufficient')
    with wave.open(str(audio_path)) as audio:
        if abs(audio.getnframes() / audio.getframerate() - duration) > .1:
            raise ValueError('Original narration duration differs from measured timing')
    return story, timing


def ffmpeg(*args):
    subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-nostdin', '-y', *map(str, args)], check=True)


def finish(delivery, output, profile):
    from professional_motion.score import build
    from production_v2.media import verify
    delivery, output = Path(delivery).resolve(), Path(output).resolve()
    story, timing = bundle(delivery, profile)
    duration = timing['duration']
    render = json.loads((output / 'render.json').read_text())
    if render.get('pipeline') != 'v2' or not render.get('originalVoice') or render.get('errors'):
        raise ValueError('Opt-in v2 visuals with measured original voice are required')
    if render.get('story_sha256') != digest(delivery / 'story.json'):
        raise ValueError('Rendered visuals belong to another story')
    if (render.get('start_frame'), render.get('end_frame')) != (0, math.ceil(duration * 30)):
        raise ValueError('A partial renderer output cannot pass as a complete film')
    build(duration, [row['start'] for row in timing['scenes']], output, profile,
          [row['scare_beat'] for row in timing['scenes'] if 'scare_beat' in row])
    ffmpeg('-i', delivery / 'narration.wav', '-af', 'loudnorm=I=-16:TP=-2:LRA=7,aresample=48000', output / 'voice.wav')
    ffmpeg('-i', output / 'score.wav', '-af', 'loudnorm=I=-29:TP=-5:LRA=9,aresample=48000', output / 'music.wav')
    graph = ('[1:a]aformat=channel_layouts=stereo,asplit=2[v][control];'
             '[2:a][control]sidechaincompress=threshold=.035:ratio=5:attack=12:release=250[ducked];'
             '[3:a]volume=.45[fx];[v][ducked][fx]amix=inputs=3:duration=first:normalize=0,'
             'alimiter=limit=.88:latency=1[mix]')
    film = output / 'candidate-review.mp4'
    if film.exists():
        raise FileExistsError('Completed review film already exists; preserve it and use a fresh output directory')
    ffmpeg('-i', output / 'visuals.mp4', '-i', output / 'voice.wav', '-i', output / 'music.wav',
           '-i', output / 'sfx.wav', '-filter_complex', graph,
           '-map', '0:v:0', '-map', '[mix]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
           '-t', duration, '-movflags', '+faststart', film)
    evidence = verify(film)
    evidence.update(profile=profile, topic_key=story['topic_key'], pipeline='v2',
                    story_sha256=digest(delivery / 'story.json'),
                    narration_sha256=digest(delivery / 'narration.wav'),
                    review_only=True, publishable=False, fresh_topic_verified=False, generation_origin='supplied_delivery_not_new_generation_verified',
                    narration_provenance='Supplied aligned original; see delivery source evidence',
                    automatic_publication=False, music_target_lufs=-29,
                    artistic_review='Requires human viewing and listening; technical validation only')
    (output / 'candidate-verification.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2))
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--delivery-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--profile', choices=['science', 'horror', 'history', 'news'], required=True)
    parser.add_argument('--finish-only', action='store_true')
    args = parser.parse_args()
    bundle(args.delivery_dir, args.profile)
    output = args.output_dir.resolve()
    if not args.finish_only:
        if output.exists() and any(output.iterdir()):
            raise FileExistsError('Use a fresh candidate output directory; existing evidence is retained')
        output.mkdir(parents=True, exist_ok=True)
        subprocess.run(['node', 'professional_motion/render.mjs', '--pipeline', 'v2', '--style', 'reference',
                        '--review', '--delivery-dir', str(args.delivery_dir.resolve()),
                        '--output-dir', str(output)], check=True)
    print(json.dumps(finish(args.delivery_dir, output, args.profile), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
