# Titles and covers before publishing

New episodes produce `publication.json` during preparation, before requesting
speech. The existing writing request supplies an accurate 35–85 character Arabic
title and a short `cover_text`; no additional model or vidIQ call is made. Saved
episodes without the new field keep their complete title, with a recognized
channel prefix removed for publication. Invalid JSON-shaped or overlong titles
stop before speech generation instead of being published or silently truncated.

Remotion displays a branded cover heading over the episode's own opening artwork
for the first 18 frames (0.6 seconds). It does not add time, delay the narration,
replace the audio, or introduce an unrelated generated photograph. `cover.png`
exports frame 6 at 1080×1920. The existing delivery/output workflow artifacts keep
the image and metadata. Story, package and cover hashes are checked before upload
and when recovering a retained movie. Legacy completed movies stay unchanged.

Buffer receives the prepared title as the YouTube title and as the first caption
line for all destinations. For Instagram only, the video asset contains
`metadata: {thumbnailOffset: 200}` to select that cover frame. Buffer does not
support selecting a YouTube/Facebook thumbnail through this endpoint: including
the cover in the video does **not** guarantee either network will choose it.
An independent, authorized direct-platform integration is needed to force a
custom image there. This change does not connect new social accounts, alter
existing queues, resubmit published movies, or change the 17:00 Cairo schedule.

Reference: https://developers.buffer.com/examples/create-video-post.html
Test: `python -m unittest discover -s remotion_factory/tests -q`
Renderer check: `cd remotion_motion && npm run check`
