"""Visible channel identity; topic matching retains the original subject."""
import json
from pathlib import Path
BRAND = json.loads((Path(__file__).resolve().parents[1]/'config/brand.json').read_text())['display_name']

def display_title(topic, limit=100):
    topic=' '.join(str(topic or '').split()).strip()
    return (topic if topic.startswith(BRAND+' | ') else BRAND+' | '+topic)[:limit].rstrip()
