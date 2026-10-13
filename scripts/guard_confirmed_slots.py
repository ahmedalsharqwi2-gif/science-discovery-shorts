"""Cancel redundant live stock production only after complete confirmed receipts."""
from __future__ import annotations
import base64
import json
import os
import urllib.request

ACTIVE = {"queued", "in_progress", "waiting", "pending", "requested"}
PRODUCTION_PATHS = {".github/workflows/main.yml", ".github/workflows/auto_publish.yml"}


def redundant_run_ids(runs, ledger):
    slots = ledger.get("slots", {})
    for run in runs:
        title = run.get("display_title", "")
        if (run.get("status") not in ACTIVE or run.get("head_branch") != "main"
                or run.get("path") not in PRODUCTION_PATHS or not title.startswith("stock ")):
            continue
        entry = slots.get(title, {})
        required = entry.get("required_services", [])
        receipts = entry.get("receipts", {})
        if (entry.get("confirmed") is True and required
                and all(isinstance(receipts.get(service), dict) and receipts[service].get("id")
                        for service in required)):
            yield run["id"]


def main():
    repo = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["GITHUB_TOKEN"]
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "confirmed-slot-guard"}
    def api(path, cancel=False):
        request = urllib.request.Request(f"https://api.github.com/repos/{repo}/{path}",
                                         headers=headers, method="POST" if cancel else "GET")
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response) if response.status != 202 else {}
    # Always read the live default-branch ledger; reruns may check out an old SHA.
    content = api("contents/state/publication_stock.json?ref=main")
    ledger = json.loads(base64.b64decode(content["content"]).decode("utf-8"))
    runs = api("actions/runs?per_page=100").get("workflow_runs", [])
    for run_id in redundant_run_ids(runs, ledger):
        api(f"actions/runs/{run_id}/cancel", cancel=True)
        print(f"Cancelled redundant production {run_id}: slot already has complete confirmed receipts")


if __name__ == "__main__":
    main()
