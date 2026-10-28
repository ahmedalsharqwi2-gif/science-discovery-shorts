import os

def preflight():
    missing=[]
    for names in [('GEMINI_TEXT_API_KEY','GEMINI_API_KEY'),('GEMINI_TTS_API_KEY','GEMINI_API_KEY')]:
        if not any(os.getenv(n,'').strip() for n in names):missing.append(' or '.join(names))
    if missing:raise RuntimeError('Missing repository Actions secret: '+'; '.join(missing))
