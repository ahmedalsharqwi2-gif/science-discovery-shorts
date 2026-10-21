"""Local forced alignment of approved narration; never invent uniform timings."""
from __future__ import annotations
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import tempfile


def normalized(word):
    word = re.sub(r'[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed]', '', word)
    return re.sub(r'[^\w]', '', word, flags=re.UNICODE).replace('_', '')


def validate_events(events, words, duration):
    if not words or len(events) != len(words):
        raise RuntimeError('Forced alignment did not cover every caption word')
    previous_end = 0.0
    output = []
    for index, (event, expected) in enumerate(zip(events, words)):
        if normalized(event['text']) != normalized(expected):
            raise RuntimeError('Forced alignment changed approved caption text')
        start, end = float(event['start']), float(event['end'])
        if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end > duration + .1:
            raise RuntimeError('Forced alignment timestamps outside audio')
        if end - start < .02 or end - start > 3 or start < previous_end - .04:
            raise RuntimeError(f'Invalid timing at word {index}: {expected!r}, start={start:.3f}, end={end:.3f}, previous_end={previous_end:.3f}')
        previous_end = end
        output.append({'text': expected, 'offset': start, 'duration': end-start})
    return output


def merge_waveform_alignments(candidates, words, duration):
    """Choose measured word intervals from independent aligners; never pad a gap."""
    candidates = [c for c in candidates if len(c) == len(words)]
    if len(candidates) < 2:
        raise RuntimeError('Two complete waveform alignments are needed for recovery')
    paths = [(0, [], -1)]
    for index, expected in enumerate(words):
        options = []
        reference = float(candidates[-1][index]['start'])
        for source, candidate in enumerate(candidates):
            event = candidate[index]
            try:
                validate_events([event], [expected], duration)
            except (RuntimeError, ValueError, TypeError):
                continue
            if abs(float(event['start']) - reference) <= 1.0:
                options.append((source, event))
        following = []
        for source, event in options:
            valid = [(cost, events, last) for cost, events, last in paths
                     if not events or float(event['start']) >= float(events[-1]['end']) - .04]
            if valid:
                cost, events, last = min(valid, key=lambda p:p[0] + (p[2] != source)*.1)
                following.append((cost + (last != source)*.1 + (source != len(candidates)-1)*.01,
                                  events + [event], source))
        paths = following
        if not paths:
            raise RuntimeError(f'No measured non-overlapping timing for word {index}: {expected!r}')
    result = min(paths, key=lambda p:p[0])[1]
    validate_events(result, words, duration)
    return result


def align_worker(audio, words):
    import stable_whisper
    import torch
    torch.set_num_threads(2)
    duration = float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration',
        '-of','default=noprint_wrappers=1:nokey=1',str(audio)],capture_output=True,text=True,check=True).stdout)
    failures, candidates = [], []
    for size in ('small', 'medium'):
        model = stable_whisper.load_faster_whisper(size, device='cpu', compute_type='int8')
        result = model.align(str(audio), ' '.join(words), language='ar',
                             failure_threshold=0.0, max_word_dur=3.0, fast_mode=False)
        del model
        if result is None:
            failures.append(size + ': no timestamps')
            continue
        events = [{'text': word.word.strip(), 'start': word.start, 'end': word.end}
                  for segment in result.segments for word in (segment.words or [])]
        candidates.append(events)
        try:
            validate_events(events, words, duration)
        except RuntimeError as exc:
            failures.append(size + ': ' + str(exc))
            continue
        print('Validated waveform alignment using ' + size, flush=True)
        return events
    try:
        result = merge_waveform_alignments(candidates, words, duration)
        print('Validated combined small/medium waveform alignment; no uniform timings', flush=True)
        return result
    except RuntimeError as exc:
        raise RuntimeError('; '.join(failures) + '; recovery: ' + str(exc)) from exc


def forced_word_alignment(audio: Path, words: list[str]) -> list[dict]:
    duration = float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration',
        '-of','default=noprint_wrappers=1:nokey=1',str(audio)],capture_output=True,text=True,check=True).stdout)
    with tempfile.TemporaryDirectory(prefix='forced-caption-', dir=audio.parent) as folder:
        root = Path(folder); transcript=root/'words.json'; output=root/'alignment.json'
        transcript.write_text(json.dumps(words,ensure_ascii=False),encoding='utf-8')
        try:
            subprocess.run([sys.executable,str(Path(__file__).resolve()),'worker',str(audio.resolve()),
                            str(transcript.resolve()),str(output.resolve())],
                           capture_output=True,text=True,check=True,timeout=900)
        except subprocess.CalledProcessError as exc:
            raise RuntimeError('Local forced caption alignment failed: ' + (exc.stderr or '')[-1200:]) from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError('Local forced caption alignment exceeded its bounded runtime') from exc
        events=json.loads(output.read_text(encoding='utf-8'))
    result=validate_events(events,words,duration)
    print(f'Local forced alignment validated all {len(result)} words against the actual audio',flush=True)
    return result


if __name__ == '__main__':
    if len(sys.argv)!=5 or sys.argv[1]!='worker':
        raise SystemExit('Expected worker AUDIO WORDS_JSON OUTPUT_JSON')
    audio=Path(sys.argv[2]);words=json.loads(Path(sys.argv[3]).read_text(encoding='utf-8'))
    Path(sys.argv[4]).write_text(json.dumps(align_worker(audio,words),ensure_ascii=False),encoding='utf-8')
