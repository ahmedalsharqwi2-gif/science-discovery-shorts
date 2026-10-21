"""Visible channel identity; topic matching retains the original subject."""
BRAND = "اسرار الكون"

def display_title(topic, limit=100):
    topic=' '.join(str(topic or '').split()).strip()
    return (topic if topic.startswith(BRAND+' | ') else BRAND+' | '+topic)[:limit].rstrip()
