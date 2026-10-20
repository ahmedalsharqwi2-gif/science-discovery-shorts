#!/usr/bin/env bash
set -euo pipefail
if [[ "${VOICETUT_LEGACY:-0}" == "1" ]]; then
  bash voice_provider/install_legacy_voicetut.sh
else
  python -c 'from voice_provider.client import config; print("Accepted voice:", config()["speaker"], config()["model"])'
  command -v ffmpeg >/dev/null || { echo 'FFmpeg is required for MP3 narration'; exit 1; }
fi
