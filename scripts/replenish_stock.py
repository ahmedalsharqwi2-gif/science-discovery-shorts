"""One-job-at-a-time replenishment of a rolling four-day Cairo video reserve."""
from __future__ import annotations
import json
import os
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ACTIVE = {"queued", "in_progress", "waiting", "pending", "requested"}


def desired_slots(now: datetime, days: int = 4):
    cairo = now.astimezone(ZoneInfo("Africa/Cairo"))
    for offset in range(days + 1):
        for hour in (12, 18):
            target = (cairo + timedelta(days=offset)).replace(hour=hour, minute=0, second=0, microsecond=0)
            if target > cairo:
                yield target, f"stock {target.date().isoformat()} {hour:02d} Cairo"


def next_missing_slot(runs: list[dict], now: datetime):
    if any(run.get("status") in ACTIVE for run in runs):
        return None
    for target, title in desired_slots(now):
        matches = [run for run in runs if run.get("display_title") == title]
        if any(run.get("confirmed") is True for run in matches):
            continue
        failures = sorted((run for run in matches if run.get("conclusion") == "failure"),
                          key=lambda run: run.get("updated_at", ""), reverse=True)
        if failures:
            latest = datetime.fromisoformat(failures[0]["updated_at"].replace("Z", "+00:00"))
            # An exhausted slot is retried after cooling down; never abandon it forever.
            cooldown = timedelta(minutes=min(120, 15 * 2 ** min(len(failures) - 1, 3)))
            if now - latest < cooldown:
                continue
        return target, title
    return None


def main():
    repo, token = os.environ["GITHUB_REPOSITORY"], os.environ["GITHUB_TOKEN"]
    workflow = os.environ["PRODUCTION_WORKFLOW"]
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "stock-replenisher"}
    def api(path, payload=None):
        data = None if payload is None else json.dumps(payload).encode()
        req = urllib.request.Request(f"https://api.github.com/repos/{repo}/{path}", data=data,
                                     headers=headers, method="POST" if data else "GET")
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.load(response) if response.status != 204 else {}
    runs = []
    for page in (1, 2, 3):
        batch = api(f"actions/workflows/{workflow}/runs?per_page=100&page={page}").get("workflow_runs", [])
        runs.extend(batch)
        if len(batch) < 100:
            break
    # Only confirmed provider receipts count as reserve, even if later housekeeping failed.
    from pathlib import Path
    ledger_path = Path(__file__).resolve().parents[1] / "state/publication_stock.json"
    if ledger_path.exists():
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        runs.extend({"display_title": title, "confirmed": True}
                    for title, entry in ledger.get("slots", {}).items() if entry.get("confirmed"))
    selected = next_missing_slot(runs, datetime.now(ZoneInfo("Africa/Cairo")))
    if selected is None:
        print("Production active, reserve complete, or failed slots cooling down; next poll will recheck.")
        return
    target, title = selected
    print(f"Dispatching ONE missing rolling-reserve slot: {title}")
    api(f"actions/workflows/{workflow}/dispatches", {"ref": "main", "inputs": {
        "stock_date": target.date().isoformat(), "stock_hour": str(target.hour),
        "dry_run": "false", "publish_now": "false"}})


if __name__ == "__main__":
    main()
