"""Fill today's remaining Cairo slots and the next three days safely.

One production dispatch at a time prevents GitHub Actions pending-run eviction
and avoids concurrent writes to shared topic/history state.
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
    batch = api(f"actions/workflows/{workflow}/runs?per_page=100&page={page}").get("workflow_runs", [])
    runs.extend(batch)
    if len(batch) < 100:
        break

# GitHub Actions concurrency supports only one pending run per group.
# Never flood the workflow with six simultaneous dispatches.
if any(r.get("status") in ("queued", "in_progress", "waiting", "pending", "requested") for r in runs):
    print("Production already active or pending; defer replenishment to next poll.")
    raise SystemExit(0)

# Three-day publication batches. Start the next batch on the final day.
from datetime import date
anchor = date(2026, 10, 11)
batch_index = max(0, (now.date() - anchor).days // 3)
batch_start = anchor + timedelta(days=batch_index * 3)
batches = [batch_start]
if now.date() >= batch_start + timedelta(days=2):
    batches.append(batch_start + timedelta(days=3))

slots = []
for first_day in batches:
    for day in range(3):
        publication_day = first_day + timedelta(days=day)
        for hour in (12, 18):
            target = datetime(publication_day.year, publication_day.month,
                              publication_day.day, hour, tzinfo=ZoneInfo('Africa/Cairo'))
            if target <= now + timedelta(hours=2):
                continue
            slots.append((target, f'stock {publication_day.isoformat()} {hour:02d} Cairo'))

for target, title in slots:
    matches = [r for r in runs if r.get("display_title") == title]
    if any(r.get("conclusion") == "success" for r in matches):
        print(f"Already produced: {title}")
        continue
    if len(matches) >= 3:
        print(f"ALERT: slot failed three times; manual intervention required: {title}")
        continue
    print(f"Dispatching ONE missing slot: {title}")
    api(f"actions/workflows/{workflow}/dispatches", {
        "ref": "main",
        "inputs": {"stock_date": target.date().isoformat(), "stock_hour": str(target.hour),
                   "dry_run": "false", "publish_now": "false"}
    })
    break
else:
    print("No missing eligible stock slots found.")
