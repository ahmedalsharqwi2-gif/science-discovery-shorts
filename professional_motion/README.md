# Professional daily factory — science

One supported production workflow: `.github/workflows/professional-daily.yml`. Each successful film chooses a different sourced subject, creates eight authored 3D scenes, produces original Charon narration, measures phrase timing, composes music, verifies the final video, and reserves the subject durably in `state/professional_topics.json`. A new title for an old topic is still a repeat. If no new suitable evidence-backed subject is available, production stops rather than recycling a film or inventing facts.

Review mode never posts externally. The current release configuration blocks all automatic publication until the user reviews the other channel samples. The science style is already approved. Future approval must record the actual reviewed film checksum in `config/professional_release.json`, set `style_approved` and `publication_approved` true, and update the matching legacy hold. An input cannot bypass this gate.

The UTC cron runs at 09:00 and 10:00; a timezone-aware `Africa/Cairo` guard selects local noon, across summer and winter. Once approved, the noon job prepares a new film and submits an absolute 17:00 Cairo scheduled publication to verified configured channels. It never changes a missed slot into immediate posting. GitHub dispatch timing and platform processing can delay execution/delivery; provider acceptance receipts are retained. Partial acceptance reuses receipts instead of republishing accepted destinations.

Videos and diagnostics are Actions artifacts. Review voice and safe metadata are also delivered to a run-specific review branch for Git-based inspection; secrets are never copied there. Media downloads for the user belong on separate review-media branches, not main. No publication is confirmed without real provider post/video IDs.

Local renderer: npm ci in professional_motion, then node professional_motion/render.mjs from repository root after prepared delivery/story.json and measured timing exist.
