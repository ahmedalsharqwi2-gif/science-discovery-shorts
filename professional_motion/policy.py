"""User-requested length: strictly longer than 90s and shorter than 180s."""
MIN_SECONDS=90.0
MAX_SECONDS=180.0
MIN_WORDS=260
MAX_WORDS=330

def require_duration(seconds):
    if not MIN_SECONDS<float(seconds)<MAX_SECONDS:
        raise ValueError('The complete film must be longer than 90 seconds and shorter than 180 seconds')
    return float(seconds)
