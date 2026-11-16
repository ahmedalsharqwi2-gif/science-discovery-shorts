"""Measured forced alignment of the original script, with independent ASR QA.

No word timing is estimated from text length. ASR never replaces captions.
"""
import difflib
import json
import re
import sys
import unicodedata
from pathlib import Path


def norm(text):
    text = unicodedata.normalize('NFKC', text)
    text = re.sub('[\u064b-\u065f\u0670\u0640]', '', text)
    text = text.translate(str.maketrans('أإآىة٠١٢٣٤٥٦٧٨٩', 'ااايه0123456789'))
    return re.sub(r'[^\w\s]', '', text).lower().strip()


class AlignmentError(ValueError):
    def __init__(self, code, details=None):
        super().__init__(code)
        self.code, self.details = code, details or {}


def verify_speech(original, recognized, config):
    expected, heard = norm(original), norm(recognized)
    ratio = difflib.SequenceMatcher(None, expected.replace(' ', ''), heard.replace(' ', ''), autojunk=False).ratio()
    a, b = expected.split(), heard.split()
    matched = sum(block.size for block in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks())
    coverage = matched / max(1, len(a))
    missing_numbers = sorted(set(re.findall(r'\d+', expected)) - set(re.findall(r'\d+', heard)))
    proof = {'characterSimilarity': ratio, 'wordCoverage': coverage, 'sourceWords': len(a), 'recognizedWords': len(b), 'missingNumerals': missing_numbers}
    if ratio < config['minCharacterSimilarity'] or coverage < config['minWordCoverage'] or missing_numbers:
        raise AlignmentError('ALIGNMENT_SPEECH_MISMATCH', proof)
    return proof


def measured_original_words(original, forced, duration):
    """Merge measured subword spans; never split a span with guessed timing."""
    compact = lambda s: norm(s).replace(' ', '')
    source = original.split()
    pieces, cursor = [], 0
    for word in forced:
        text = compact(word['word'])
        if not text:
            continue
        start, end = float(word['start']), float(word['end'])
        if start < 0 or end <= start or end > duration + .05:
            raise AlignmentError('ALIGNMENT_INVALID_MEASURED_SPAN')
        pieces.append((cursor, cursor + len(text), start, end))
        cursor += len(text)
    if ''.join(compact(w['word']) for w in forced) != ''.join(compact(w) for w in source):
        raise AlignmentError('ALIGNMENT_FORCED_TEXT_MISMATCH')
    output, cursor = [], 0
    for word in source:
        token = compact(word)
        if not token:
            if output:
                output[-1]['text'] += ' ' + word
            continue
        end_char = cursor + len(token)
        spans = [p for p in pieces if p[0] < end_char and p[1] > cursor]
        if not spans or spans[0][0] != cursor or spans[-1][1] != end_char:
            raise AlignmentError('ALIGNMENT_WORD_BOUNDARY_UNRESOLVED')
        row = {'text': word, 'start': spans[0][2], 'end': spans[-1][3]}
        if output and row['start'] < output[-1]['end'] - .02:
            raise AlignmentError('ALIGNMENT_OVERLAPPING_WORDS')
        output.append(row)
        cursor = end_char
    if not output or norm(' '.join(w['text'] for w in output)) != norm(original):
        raise AlignmentError('ALIGNMENT_ORIGINAL_TEXT_NOT_PRESERVED')
    return output


def main(input_path, output_path):
    config = json.loads(Path('config/alignment.json').read_text())
    scenes = json.loads(Path(input_path).read_text())
    diagnostic_path = Path(output_path).with_name('alignment-diagnostics.json')
    diagnostics = {'method': 'stable-ts attention forced alignment; independent unprompted faster-whisper ASR', 'estimatedTiming': False, 'scenes': []}
    stage, scene_index = 'model_load', None
    try:
        import stable_whisper
        model = stable_whisper.load_faster_whisper(config['model'], device='cpu', compute_type='int8', cpu_threads=config['cpuThreads'], download_root=config['downloadRoot'])
        output = []
        for scene_index, scene in enumerate(scenes):
            stage = 'independent_asr'
            segments, _ = model.transcribe_original(scene['file'], language=config['language'], word_timestamps=True, beam_size=config['beamSize'], vad_filter=True)
            recognized = ' '.join(s.text for s in segments)
            proof = verify_speech(scene['text'], recognized, config)
            stage = 'forced_alignment'
            result = model.align(scene['file'], scene['text'], language=config['language'], regroup=False, failure_threshold=config['failureThreshold'])
            if result is None:
                raise AlignmentError('ALIGNMENT_MODEL_RETURNED_NO_RESULT')
            forced = [word for segment in result.to_dict()['segments'] for word in segment.get('words', [])]
            measured = measured_original_words(scene['text'], forced, scene['duration'])
            output.append(measured)
            diagnostics['scenes'].append({'scene': scene_index, 'passed': True, 'words': len(measured), **proof})
            diagnostic_path.write_text(json.dumps(diagnostics, ensure_ascii=False, indent=2))
        Path(output_path).write_text(json.dumps(output, ensure_ascii=False, indent=2))
        diagnostics['passed'] = True
        diagnostic_path.write_text(json.dumps(diagnostics, ensure_ascii=False, indent=2))
    except Exception as exc:
        code = exc.code if isinstance(exc, AlignmentError) else 'ALIGNMENT_MODEL_LOAD_FAILED' if stage == 'model_load' else 'ALIGNMENT_MODEL_EXECUTION_FAILED'
        diagnostics.update(passed=False, code=code, stage=stage, scene=scene_index, errorType=type(exc).__name__)
        if isinstance(exc, AlignmentError):
            diagnostics['details'] = exc.details
        diagnostic_path.write_text(json.dumps(diagnostics, ensure_ascii=False, indent=2))
        print(code, file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2]))
