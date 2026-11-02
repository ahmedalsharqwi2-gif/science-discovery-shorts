"""Owner-confirmed permanent limits: news >60s, every other channel >90s."""
import math
MINIMUMS={'science':90.0,'horror':90.0,'history':90.0,'news':60.0,'stickman':90.0}
MAX_SECONDS=180.0
def require_duration(seconds,profile):
    value=float(seconds)
    if profile not in MINIMUMS:raise ValueError('Known channel duration profile required')
    if not math.isfinite(value) or not MINIMUMS[profile]<value<MAX_SECONDS:
        raise ValueError(profile+' must exceed '+str(int(MINIMUMS[profile]))+' seconds and stay under180seconds')
    return value
