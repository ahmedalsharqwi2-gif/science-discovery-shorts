"""Keep six Cairo publishing slots reserved across the next three calendar days.

Dispatches only missing/failed slots; never considers an in-progress build empty.
GitHub workflow run names are the idempotency key, not local state.
"""
import json
import os
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

repo = os.environ["GITHUB_REPOSITORY"]
token = os.environ["GITHUB_TOKEN"]
workflow = os.environ["PRODUCTION_WORKFLOW"]
now = datetime.now(ZoneInfo("Africa/Cairo"))
headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
           "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "stock-replenisher"}
def api(path, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(f"https://api.github.com/repos/{repo}/{path}",
                                 data=data, headers=headers, method="POST" if data else "GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp) if resp.status != 204 else {}

runs = []
for page in (1, 2, 3):
    result = api(f"actions/workflows/{workflow}/runs?per_page=100&page={page}")
    runs.extend(result.get("workflow_runs", []))
    if len(result.get("workflow_runs", [])) < 100:
        break

for day in range(1, 4):
    date = (now + timedelta(days=day)).date().isoformat()
    for hour in (12, 18):
        title = f"stock {date} {hour:02d} Cairo"
        matches = [r for r in runs if r.get("display_title") == title]
        good = any(r.get("status") != "completed" or r.get("conclusion") == "success" for r in matches)
        if good:
            print(f"Already reserved: {title}")
            continue
        if len(matches) >= 2:
            print(f"Needs human attention (2 failed attempts): {title}")
            continue
        print(f"Dispatching: {title}")
        api(f"actions/workflows/{workflow}/dispatches", {
            "ref": "main", "inputs": {"stock_date": date, "stock_hour": str(hour), "dry_run": "false"}
        })
