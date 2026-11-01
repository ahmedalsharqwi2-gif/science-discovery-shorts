# Opt-in production core

This package is a candidate safety core. It does not enable a cron, disable the
legacy pipeline, or claim all channels passed. The Buffer adapter is dormant until complete cutover evidence exists; live API behavior remains unverified.
The branch's renderer/isolated review command supplies media orchestration.

Run from the repository root:

```sh
python -m pytest -q tests/test_production_v2.py
python -m production_v2 window --now 2026-12-01T12:00:00Z
python -m production_v2 snapshot --root . --ledger state/production-v2.sqlite3
python -m production_v2 status --ledger state/production-v2.sqlite3
python -m production_v2 verify path/to/full-film.mp4 --report path/to/media-check.json
python -m production_v2 gate path/to/acceptance-manifest.json --report path/to/cutover-check.json
```

`window` targets 17:00 Cairo on the current civil day. Production may start from
09:00 until before 15:00; dispatch delays inside this interval remain eligible.
Too-early and missed outcomes do not move the publication date. Durations must
be at least 120 and strictly less than 180 seconds.

`Ledger.import_legacy` reads all `state/**/*.json` plus known root history files,
stores their exact bytes and checksums, and imports topic, slot and video identity
for deduplication. It never changes old files. Invalid historical JSON blocks the
transaction. Reserved slots/topics and video hashes are unique, and update/delete
triggers make the ledger append-only. Keep the SQLite database and old history
in durable storage before external mutations; a job-local database alone does
not protect concurrent machines. Use one shared Actions concurrency group for
production and preserve the database before sending anything remotely.

The provider-independent `schedule_three` protocol requires three distinct
confirmed channel IDs. The provider adapter supplies `preflight(mapping)`,
`submit(channel_id=..., due_at=..., media_url=...)`, and `lookup(post_id)`.
Submission intent commits before calling `submit`. A timeout leaves the intent
unresolved; retries stop and require explicit provider lookup/reconciliation.
They do not blindly send a replacement. Partial verified receipts remain in the
ledger. Every retry re-queries already accepted posts and checks the exact post,
channel, due time, media URL and scheduled status. The core does not promise
exactly-once delivery from a provider without an atomic provider idempotency key.

Media validation checks real stream lengths, decoded frame coverage, and a full
video/audio decode. It proves container/codec completeness, not meaningful
speech, accurate sources, novelty, or viewing/listening approval.

The read-only cutover gate requires all five profiles (`science`, `horror`,
`history`, `news`, `stickman`) with the following per-profile evidence:

```json
{
  "profiles": {
    "science": {
      "profile": "science",
      "origin": "new_generation",
      "repo_root": "/absolute/checkout",
      "legacy_snapshot": [{"path": "state/professional_topics.json", "sha256": "..."}],
      "story_path": "/absolute/new/story.json",
      "topic_key": "new-source-subject",
      "narration": {
        "origin": "new_generation", "provider": "gemini", "voice": "Charon",
        "provider_evidence_id": "real-provider-request-evidence",
        "story_sha256": "...", "path": "/absolute/new/voice.wav", "sha256": "..."
      },
      "renderer": {"pipeline": "v2", "source_sha256": {"professional_motion/scene.js": "..."}},
      "video_path": "/absolute/new/full-film.mp4",
      "video_sha256": "...",
      "review": {"video_sha256": "...", "visual": "PASS", "audio": "PASS", "reviewed_by": "actual reviewer"}
    }
  }
}
```

Repeat complete evidence for every profile. Provider and human review evidence
must be genuine; these metadata assertions are not cryptographic attestations
from an external service. An archive-based technical rerender cannot pass as a
new-topic production acceptance film. No command activates v2. After all channels
pass, a separate explicit switch must remove/disable every old production trigger
before enabling the replacement; until then `active_pipeline` remains `legacy`.


Fresh candidate orchestration (still never publishes):

```sh
python -m production_v2.generate --profile science --run-dir .candidate-v2/new-review \
  --ledger .candidate-v2/shared.sqlite3 --git-state --then-review
```

Use the original Gemini secrets belonging to the current repository. The manual
`production-v2-generate.yml` workflow passes that repository's existing secrets;
no common Buffer key is requested or consumed. It checkpoints reservations on
`codex/production-v2-state` before calling TTS. The state store preserves the source
branch/index and uses normal fast-forward Git pushes; a competing writer or
unavailable state branch blocks generation instead of resetting history. Failed
TTS retains the exact reserved story and failure event. Generation, ASR and Actions
execution are not considered verified until a real new full film passes the checks.

For live receipt audits run the manual `production-v2-audit.yml` in the matching
repository. It reads that repository's own `BUFFER_API_KEY`; the local CLI defaults
to a clearly unverified retained-state report and rejects live use outside the
matching Actions context. It never creates, updates or deletes Buffer posts.

The publisher protocol additionally requires a `persist(ledger)` callback. Intent
must reach durable storage before submission; accepted IDs are retained before
lookup, so a lookup outage resumes with the same ID rather than submitting again.
A legacy record queued for tomorrow also blocks a new daily reservation for that
same due time even if its old slot has a different date. Channel/due claims prevent
alternate candidate slot names from bypassing that guard.


An explicit `.github/production-v2-launch.json` review marker on the candidate
branch triggers one review job using a standard free runner in these public
repositories. Ordinary commits do not trigger another full review; no new cron
exists. The existing professional daily dispatcher defaults to `legacy`; only
an explicit `pipeline=v2` selects the review-only path. Its production and alert
jobs are skipped for that selection. A semantic baseline test proves all existing
schedule/job settings remain unchanged when the explicit candidate additions are removed.

`export_review` retains started/final evidence on `codex/production-v2-status`,
and only uploads a full, fingerprinted decoded MP4 as a clearly named GitHub
review Release. Read-only Buffer observations use their separate
`codex/production-v2-audit-status` branch and each repository's own secret.
Status and state branches preserve the complete source tree and use ordinary
fast-forward Git pushes. API and Actions outcomes are not claimed until their
real status records/artifacts have been retrieved.
