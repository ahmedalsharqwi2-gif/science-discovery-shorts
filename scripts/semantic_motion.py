"""Build explanatory motion from the words timed against the final narration."""
from __future__ import annotations
import json
import math
from pathlib import Path
import re

RULES = (
    ('losses', r'خسا[ئيل]|خسائر|هالك|مثالي|كامل'),
    ('pressure', r'ضغط'),
    ('twist', r'زوايا|زاوية|الميل|تتلوى|التواء|ملفوف'),
    ('energy', r'طاقة|الطاقه|المحرك|ينقل'),
    ('speed', r'أسرع|اسرع|مسار|السرعة|السرعه|المحور'),
    ('airfoil', r'جناح|المقطع|الإيربلاين|طائرة'),
)


def concept_for(words):
    text = ' '.join(w['text'] for w in words)
    for concept, pattern in RULES:
        match = next((w for w in words if re.search(pattern, w['text'])), None)
        if match:
            return concept, float(match['offset'])
    if re.search(r'الهوا|هواء|الدفع', text):
        return 'airflow', float(words[0]['offset'])
    return 'rotor', float(words[0]['offset'])


def load_word_timeline(subtitles, narration, duration):
    if subtitles is None:
        raise RuntimeError('Motion needs captions aligned to the final audio')
    path = Path(subtitles).with_suffix('.words.json')
    if not path.exists():
        raise RuntimeError('Audio-aligned word timeline is missing; approximate motion refused')
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('narration') != narration or abs(float(data['duration']) - duration) > .2:
        raise RuntimeError('Motion timeline belongs to another narration or audio duration')
    words = data['words']
    previous = -1.0
    for word in words:
        start, length = float(word['offset']), float(word['duration'])
        if not math.isfinite(start + length) or start < previous - .04 or start < 0 or length <= 0 or start + length > duration + .2:
            raise RuntimeError('Invalid audio-aligned motion timestamp')
        previous = start
    if not words:
        raise RuntimeError('Empty motion timeline')
    return words


def plan_motion_scenes(words, duration):
    # Sentence boundaries come from the approved script; their times come from
    # the waveform. A semantic cue never activates before its spoken keyword.
    phrases, pending, start = [], [], 0.0
    for index, word in enumerate(words):
        pending.append(word)
        end = (float(words[index + 1]['offset']) if index + 1 < len(words) else duration)
        boundary = bool(re.search(r'[،.!؟؛]$', word['text']))
        if (boundary and end - start >= 3.5) or end - start >= 11 or index == len(words) - 1:
            phrases.append((start, end, pending))
            pending, start = [], end
    scenes, previous, previous_origin = [], 'rotor', 0.0
    for index, (start, end, phrase) in enumerate(phrases):
        beats = [{'at': 0.0, 'concept': previous, 'origin':previous_origin}]
        clause = []
        for pos, word in enumerate(phrase):
            clause.append(word)
            if re.search(r'[،.!؟؛]$', word['text']) or pos == len(phrase)-1:
                concept, trigger = concept_for(clause)
                if concept != beats[-1]['concept']:
                    beats.append({'at': max(0.0, trigger-start), 'concept': concept, 'origin':trigger})
                clause = []
        concept = beats[-1]['concept']
        scenes.append({'id': f'scene_{index+1:03d}', 'start': start, 'end': end,
                       'text': ' '.join(w['text'] for w in phrase), 'kind': 'motion',
                       'prompt': 'Original explanatory diagram for this spoken clause.',
                       'query': '', 'motion': 'semantic', 'shot': concept,
                       'motion_beats': beats,
                       'spoken_words': [{'text': w['text'], 'at': float(w['offset'])-start,
                                         'duration': float(w['duration'])} for w in phrase]})
        previous = concept
        previous_origin = beats[-1]['origin']
    if not scenes or abs(scenes[-1]['end'] - duration) > .01:
        raise RuntimeError('Motion scenes do not cover the narration')
    return scenes
