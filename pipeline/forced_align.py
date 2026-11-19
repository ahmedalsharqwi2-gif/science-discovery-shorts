"""Measured forced alignment of the original script, with independent ASR QA.

No word timing is estimated from text length. ASR never replaces captions.
"""
import difflib
import json
import re
import sys
import unicodedata
from pathlib import Path


# Latin -> approximate Arabic phonetic letters, for comparison only. ASR often
# writes known brands in Latin (whisper: "Nvidia") while the script is Arabic
# ("إنفيديا"); the gate must compare what was SAID, not the alphabet chosen.
_LAT2AR = str.maketrans({'a':'ا','b':'ب','c':'ك','d':'د','e':'ي','f':'ف','g':'ج','h':'ه','i':'ي','j':'ج','k':'ك','l':'ل','m':'م','n':'ن','o':'و','p':'ب','q':'ك','r':'ر','s':'س','t':'ت','u':'و','v':'ف','w':'و','x':'كس','y':'ي','z':'ز'})
# Arabic names of Latin letters, for all-caps acronyms: scripts spell them out
# for TTS ("آر تي إكس") while ASR prints "RTX". Expanding the acronym to letter
# names makes the comparison about what was said.
_LAT_NAME = {'a':'اي','b':'بي','c':'سي','d':'دي','e':'اي','f':'اف','g':'جي','h':'اتش','i':'اي','j':'جيه','k':'كي','l':'ال','m':'ام','n':'ان','o':'او','p':'بي','q':'كيو','r':'ار','s':'اس','t':'تي','u':'يو','v':'في','w':'دبليو','x':'اكس','y':'واي','z':'زد'}
_AR_ONES = {'0':'صفر','1':'واحد','2':'اتنين','3':'تلاته','4':'اربعه','5':'خمسه','6':'سته','7':'سبعه','8':'تمانيه','9':'تسعه','10':'عشره','11':'حداشر','12':'اتناشر','13':'تلاتاشر','14':'اربعتاشر','15':'خمستاشر','16':'ستاشر','17':'سبعتاشر','18':'تمنتاشر','19':'تسعتاشر'}
_AR_TENS = {'2':'عشرين','3':'تلاتين','4':'اربعين','5':'خمسين','6':'ستين','7':'سبعين','8':'تمانين','9':'تسعين'}
_AR_HUNDREDS = {'1':'ميه','2':'ميتين','3':'تلتميه','4':'اربعميه','5':'خمسميه','6':'ستميه','7':'سبعميه','8':'تمنميه','9':'تسعميه'}

def _ar_number(s):
    n = int(s)
    if n > 9999:
        return ' '.join(_AR_ONES.get(c, c) for c in s)
    parts = []
    if n >= 1000:
        th, n = divmod(n, 1000)
        parts.append(_AR_ONES[str(th)] + ' الاف' if th > 2 else {1: 'الف', 2: 'الفين'}[th])
    if n >= 100:
        h, n = divmod(n, 100)
        parts.append(_AR_HUNDREDS[str(h)])
    if n >= 20:
        t, o = divmod(n, 10)
        parts.append((_AR_ONES[str(o)] + ' و' if o else '') + _AR_TENS[str(t)])
    elif n:
        parts.append(_AR_ONES[str(n)])
    return ' و'.join(parts)

def _expand_digits(text):
    return re.sub(r'\d+', lambda m: _ar_number(m.group(0)), text)

def _expand_acronyms(text):
    # All-caps Latin tokens (len>=2) are acronyms: expand to Arabic letter names.
    return re.sub(r'\b[A-Z]{2,}\b', lambda m: ' '.join(_LAT_NAME.get(c, c) for c in m.group(0).lower()), text)

def norm(text):
    text = unicodedata.normalize('NFKC', text)
    text = re.sub('[\u064b-\u065f\u0670\u0640]', '', text)
    text = text.translate(str.maketrans('أإآىة٠١٢٣٤٥٦٧٨٩', 'ااايه0123456789'))
    text = text.lower()
    text = re.sub(r'[a-z]+', lambda m: m.group(0).translate(_LAT2AR), text)
    return re.sub(r'[^\w\s]', '', text).strip()

def norm_compare(text):
    """norm() plus spoken-form normalization: digits -> Arabic words, % -> في المئة.
    Used for the ASR comparison only; missingNumerals still uses norm() with digits intact."""
    text = unicodedata.normalize('NFKC', text)
    text = re.sub('[\u064b-\u065f\u0670\u0640]', '', text)
    text = text.translate(str.maketrans('أإآىة٠١٢٣٤٥٦٧٨٩', 'ااايه0123456789'))
    text = text.replace('%', ' في المئة ')
    return norm(_expand_acronyms(_expand_digits(text)))


class AlignmentError(ValueError):
    def __init__(self, code, details=None):
        super().__init__(code)
        self.code, self.details = code, details or {}


def verify_speech(original, recognized, config):
    expected, heard = norm_compare(original), norm_compare(recognized)
    ratio = difflib.SequenceMatcher(None, expected.replace(' ', ''), heard.replace(' ', ''), autojunk=False).ratio()
    a, b = expected.split(), heard.split()
    matched = sum(block.size for block in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks())
    coverage = matched / max(1, len(a))
    missing_numbers = sorted(set(re.findall(r'\d+', norm(original))) - set(re.findall(r'\d+', norm(recognized))))
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
        if end > duration + .05 and end - duration <= .5:
            end = duration  # provider overshoot past the container end: clamp small excess, never invent timing
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
