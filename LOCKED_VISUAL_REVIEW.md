# Locked visual contract v1.3

Review-only branch. Do not merge or publish on the basis of unit tests alone.
`config/visual_template.json` is this channel's visual source of truth. The runtime rejects cross-channel profiles and per-episode palette overrides. The original logo has not been fabricated.

New production drafts generate and retain a separately reviewed hook before the title, scene plan, images or voice request. A new episode must carry `visual_template_version: 1`, exact `hook_line`, one `title_accent_word` for the overall title and each scene label. Existing acknowledged drafts are retained, not silently rewritten. Missing new metadata blocks their render for explicit migration.

`remotion_motion/review.mjs --props <json> --output-dir <new-dir>` creates watermarked reviews without importing a publisher. `--diagnostic-stills` is only a visual diagnostic, not a full-film acceptance. Only stickman may use `--silent-review`.

The `audit/manifest.json` contains two-second and caption-onset image samples, isolated shaped-text pixel masks and measured projected focal bounds. Run:

```
python scripts/verify_safe_area.py --video <mp4> --manifest <audit/manifest.json> --output <new-audit-result-dir>
python scripts/verify_hook.py <captions.ass> --story <story.json>
```

Real phone screenshots remain required separately for Shorts, TikTok and Reels. Overlay PNGs are conservative interface previews, not actual app screenshots. Unmapped or unavailable audio cues stay silent, with no synthesized substitute. Audio and scene timing must come from the actual voice alignment; short caption events are reported rather than stretched.

No workflow, cron, publication destination or professional_release configuration is changed. The existing publisher and its review gates are not activated by this branch.
