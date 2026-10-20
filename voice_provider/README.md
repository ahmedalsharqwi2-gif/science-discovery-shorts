# Accepted narration provider

Gemini 3.8 Flash TTS, Charon; exact approved Egyptian full-narration style in `config/accepted_voice.json`. `generate(text, output_path)` returns the output Path and supports genuine PCM WAV and correctly encoded MP3. One full transcript per API request. No silent fallback or reference-video audio.

Credentials: `GEMINI_TTS_API_KEY` or existing `GEMINI_API_KEY`; writing can use `GEMINI_TEXT_API_KEY`. Never print keys or provider error bodies. Atomic outputs, audio length validation, SHA-verified cache, two maximum attempts, no retry of explicit daily quota exhaustion. SQLite safety limits are local safeguards, not live Google remaining quotas.

Run `python -m voice_provider.smoke` for one real newly generated test and an exact cache reuse check. CI unit tests use synthetic WAV bytes, never a fabricated provider proof. Retired experiments are preserved in Git history.
