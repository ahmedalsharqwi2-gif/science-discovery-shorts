# Independent daily video health

Production remains09:00 Africa/Cairo with publication17:00 on the same civil day. This separate workflow observes completed production and checks at11:30,15:00,16:15 and17:30 Cairo; paired UTC triggers handle DST. It does not have text/TTS secrets and never creates or updates social posts.

The audit independently downloads each immutable video once, verifies its SHA256 against the episode ledger and live release metadata, fully decodes it, checks1080x1920, audio level, visual samples and the permanent duration rule (>60s news, >90s other channels). Subsequent checks reuse this exact-media result only while live asset identity/digest remain unchanged.

Each checkpoint reads the three own channel queues and then reads the same live post IDs. Before publication all three must be scheduled for17:00 Cairo using the same retained film. The17:30 check requires Buffer status sent, sentAt and an externalLink for every destination. This is provider-confirmed publication, not a claim of independently reading every social platform page.

The morning scheduler must have an actual successful cron run for that date; a missing/failed cron is an alert even if an old stock video is available. A future-date preview labels this observation not due yet. No automatic rollover, regeneration or resubmission occurs.

Reports are append-only under reviews/daily_health/YYYY-MM-DD/run-attempt.json, with reviews/daily_health/latest.json and immutable-media checks under reviews/daily_health/media/. Each run has an Actions summary and artifact. A failure opens/reopens one marked GitHub Issue for that date in this repository; recovery closes that same issue. Existing user issue comments are preserved. An alert transport failure leaves the audit red.

Manual review: Actions → Independent daily video health → Run workflow. Leave date empty for today; use a prior date with postpublish to recheck a late publication. This checks technical health and provider receipts; it is not a human review of storytelling or scientific accuracy.
