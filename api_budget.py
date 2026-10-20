"""Local, persistent Gemini request budgets. This is not Google's live quota API.
Each repository serializes its own workflows; projects shared by repositories
still share Google's quota and require a shared scheduler.
"""
import hashlib, os, sqlite3, time
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

class BudgetExceeded(RuntimeError):
    pass

def reserve(kind, model, key):
    if kind not in {'text', 'tts'}:
        raise ValueError('Unknown API request category')
    root = Path(os.getenv('API_BUDGET_PATH', 'state/api_budget.sqlite3'))
    root.parent.mkdir(parents=True, exist_ok=True)
    project = hashlib.sha256(key.encode()).hexdigest()
    daily = min(int(os.getenv('GEMINI_'+kind.upper()+'_DAILY_BUDGET', '40' if kind=='text' else '6')), 100 if kind=='text' else 8)
    per_run = min(int(os.getenv('GEMINI_'+kind.upper()+'_RUN_BUDGET', '12' if kind=='text' else '2')), daily)
    gap = float(os.getenv('GEMINI_'+kind.upper()+'_MIN_INTERVAL', '4.2' if kind=='text' else '21'))
    run = os.getenv('GITHUB_RUN_ID', 'local') + ':' + os.getenv('GITHUB_RUN_ATTEMPT', '1')
    while True:
        now = time.time()
        day = datetime.fromtimestamp(now, ZoneInfo('America/Los_Angeles')).date().isoformat()
        with sqlite3.connect(root, timeout=30) as con:
            con.execute('CREATE TABLE IF NOT EXISTS calls (project TEXT, kind TEXT, model TEXT, day TEXT, run TEXT, stamp REAL)')
            con.execute('BEGIN IMMEDIATE')
            count = con.execute('SELECT count(*) FROM calls WHERE project=? AND kind=? AND day=?', (project,kind,day)).fetchone()[0]
            used = con.execute('SELECT count(*) FROM calls WHERE project=? AND kind=? AND run=? AND day=?', (project,kind,run,day)).fetchone()[0]
            if count >= daily or used >= per_run:
                raise BudgetExceeded(f'{kind} local safety budget reached; task preserved for a later run. No additional API request sent.')
            last = con.execute('SELECT max(stamp) FROM calls WHERE project=? AND kind=?', (project,kind)).fetchone()[0] or 0
            delay = gap-(now-last)
            if delay <= 0:
                con.execute('INSERT INTO calls VALUES (?,?,?,?,?,?)', (project,kind,model,day,run,now))
                con.execute('DELETE FROM calls WHERE stamp < ?', (now-35*86400,))
                return
        time.sleep(min(delay, 25))
