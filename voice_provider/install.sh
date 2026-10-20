#!/usr/bin/env bash
set -euo pipefail
voice_runtime="${RUNNER_TEMP:-/tmp}/accepted-voicetut"
python -m venv "$voice_runtime"
"$voice_runtime/bin/python" -m pip install --upgrade pip
"$voice_runtime/bin/python" -m pip install 'torch==2.8.0+cpu' 'torchaudio==2.8.0+cpu' 'torchvision==0.23.0+cpu' --index-url https://download.pytorch.org/whl/cpu
"$voice_runtime/bin/python" -m pip install 'numpy==1.26.4' 'transformers==5.3.0' 'git+https://github.com/k2-fsa/OmniVoice.git@08be0b4ccbac3e13e374e86fbfead4b4cac343e2' 'git+https://github.com/MohammedAly22/VoiceTuT-TTS.git@44cba00cd3ddb04b5213353e19e960045e332da7'
if [[ -n "${GITHUB_ENV:-}" ]]; then
  echo "VOICETUT_PYTHON=$voice_runtime/bin/python" >> "$GITHUB_ENV"
fi
echo "VoiceTut interpreter: $voice_runtime/bin/python"
