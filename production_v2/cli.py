"""Readiness and migration tools; none of these commands publish or activate v2."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from .ledger import Ledger
from .media import verify
from .schedule import window
from .gate import evaluate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    snapshot = commands.add_parser('snapshot')
    snapshot.add_argument('--root', default='.')
    snapshot.add_argument('--ledger', required=True)
    status = commands.add_parser('status')
    status.add_argument('--ledger', required=True)
    media = commands.add_parser('verify')
    media.add_argument('video')
    media.add_argument('--report')
    gate = commands.add_parser('gate')
    gate.add_argument('manifest')
    gate.add_argument('--report')
    clock = commands.add_parser('window')
    clock.add_argument('--now')
    args = parser.parse_args()
    if args.command == 'window':
        result = window(datetime.fromisoformat(args.now.replace('Z', '+00:00')) if args.now else datetime.now(timezone.utc))
    elif args.command == 'gate':
        result = evaluate(json.loads(Path(args.manifest).read_text()))
        if args.report:
            target = Path(args.report)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == 'verify':
        result = verify(args.video)
        if args.report:
            target = Path(args.report)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if args.command == 'status' and not Path(args.ledger).is_file():
            parser.error('Ledger does not exist; status must not create a new ledger')
        with Ledger(args.ledger) as ledger:
            if args.command == 'snapshot':
                result = {'legacy_files': ledger.import_legacy(args.root), 'active_pipeline': 'legacy'}
            else:
                result = {table: ledger.db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]
                          for table in ('legacy_files', 'reservations', 'reservation_tokens', 'videos', 'intents', 'schedule_claims', 'submission_acks', 'receipts', 'events')}
                result['unresolved_intents'] = ledger.db.execute('SELECT COUNT(*) FROM intents i LEFT JOIN receipts r USING(slot,service) WHERE r.post_id IS NULL').fetchone()[0]
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.command == 'gate' and not result['cutover_eligible']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
