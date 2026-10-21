"""Recover exact Arabic token splits/merges from real ASR timestamps."""
from difflib import SequenceMatcher


def recover_token_boundaries(expected, heard_tokens, heard, script_words, timings):
    """Only recover identical joined tokens, never fuzzy or unrelated words."""
    matcher = SequenceMatcher(None, expected, heard_tokens, autojunk=False)
    for tag, a, b, c, d in matcher.get_opcodes():
        if tag != "replace" or not (0 < b-a <= 4 and 0 < d-c <= 4):
            continue
        left, right = "".join(expected[a:b]), "".join(heard_tokens[c:d])
        if not left or left != right:
            continue
        ranges = []
        position = 0
        for token, (_, start, end) in zip(heard_tokens[c:d], heard[c:d]):
            if token:
                ranges.append((position, position + len(token), start, end))
            position += len(token)
        def stamp(index, ending=False):
            candidates = ranges if not ending else list(reversed(ranges))
            for lo, hi, start, end in candidates:
                if lo <= index <= hi:
                    return start + (end-start) * (index-lo) / (hi-lo)
            raise ValueError("ASR token boundary outside spoken range")
        position = 0
        for i in range(a,b):
            size = len(expected[i])
            if size and timings[i] is None:
                start, end = stamp(position), stamp(position + size, True)
                timings[i] = {"text": script_words[i], "offset": start, "duration": max(end-start, 0.06)}
            position += size
    return timings
