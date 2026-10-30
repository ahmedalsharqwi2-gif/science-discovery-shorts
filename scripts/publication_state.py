"""Durable acceptance receipts; a rendered video alone never fills stock."""
from __future__ import annotations
import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]


def immediate_requested() -> bool:
    return os.getenv("PUBLISH_IMMEDIATE", "false").lower() == "true"


def immediate_due() -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=2)).isoformat(timespec="seconds").replace("+00:00", "Z")


def stock_key() -> str:
    if immediate_requested():
        return "immediate " + os.getenv("PRODUCTION_MEDIA_ID", os.getenv("GITHUB_RUN_ID", "local"))
    due = datetime.fromisoformat(os.environ["PUBLISH_DUE_AT"].replace("Z", "+00:00"))
    if due.tzinfo is None:
        raise ValueError("Publication due time must include its timezone")
    local = due.astimezone(ZoneInfo("Africa/Cairo"))
    return f"stock {local.date().isoformat()} {local.hour:02d} Cairo"


def accepted_receipt(service: str) -> dict | None:
    if os.getenv("PUBLICATION_RECEIPTS_ENABLED", "false").lower() != "true":
        return None
    path = ROOT / "state/publication_stock.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    receipt = data.get("slots", {}).get(stock_key(), {}).get("receipts", {}).get(service)
    return receipt if receipt and receipt.get("id") else None


def require_services(services) -> None:
    path = ROOT / "state/publication_stock.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"slots": {}}
    entry = data.setdefault("slots", {}).setdefault(stock_key(), {"confirmed": False, "receipts": {}})
    entry["required_services"] = sorted(set(entry.get("required_services", [])) | set(services))
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def record_receipt(service: str, identifier: str, due_at: str | None = None) -> None:
    if not identifier:
        raise ValueError("A publication receipt requires a real provider post/video ID")
    path = ROOT / "state/publication_stock.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"slots": {}}
    entry = data.setdefault("slots", {}).setdefault(stock_key(), {"confirmed": False, "receipts": {}})
    entry["receipts"][service] = {"id": identifier, "due_at": due_at,
                                  "run_id": os.getenv("GITHUB_RUN_ID", "local"),
                                  "accepted_at": datetime.now(timezone.utc).isoformat()}
    entry["confirmed"] = False
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def confirm_stock() -> None:
    if os.getenv("BUFFER_OUTCOME") != "success" or os.getenv("YOUTUBE_OUTCOME", "success") != "success":
        raise RuntimeError("Publication incomplete: reserve is not confirmed; preserve video and retry")
    path = ROOT / "state/publication_stock.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    entry = data["slots"][stock_key()]
    required = set(entry.get("required_services", []))
    if "YOUTUBE_OUTCOME" in os.environ:
        required.add("youtube")
    if not required or any(not entry.get("receipts", {}).get(service, {}).get("id") for service in required):
        raise RuntimeError("Missing acceptance receipts for required publishing destinations")
    if not entry.get("receipts") or any(not receipt.get("id") for receipt in entry["receipts"].values()):
        raise RuntimeError("No real provider acceptance receipts")
    entry["confirmed"] = True
    entry["confirmed_at"] = datetime.now(timezone.utc).isoformat()
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)
    print(f"Confirmed publication receipts for {stock_key()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["confirm"])
    parser.parse_args()
    confirm_stock()


def submission_intent(service,channel_id,due_at):
    """Persist a write-ahead marker; an ambiguous submission must be reconciled."""
    path=ROOT/'state/publication_stock.json'
    data=json.loads(path.read_text())
    entry=data['slots'][stock_key()]
    existing=entry.setdefault('submissions',{}).get(service)
    if existing and not entry.get('receipts',{}).get(service,{}).get('id'):
        raise RuntimeError('PublicationReconciliationRequired: a prior submission has no receipt; refusing a duplicate request')
    entry['submissions'][service]={'channel_id':channel_id,'scheduled_at':due_at,'status':'submitting','created_at':datetime.now(timezone.utc).isoformat()}
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2));temp.replace(path)
    if os.getenv('GITHUB_ACTIONS')=='true':
        import subprocess,sys
        subprocess.run([sys.executable,'-m','professional_motion.persist_state'],check=True)


def update_verified_receipts(receipts):
    path=ROOT/'state/publication_stock.json';data=json.loads(path.read_text())
    data['slots'][stock_key()]['receipts'].update(receipts)
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2));temp.replace(path)
