# License review

Remotion: inspected installed node_modules/remotion/LICENSE.md, copied to REMOTION-LICENSE.md. Free for individuals, nonprofits, and for-profit organizations with up to three employees, as well as noncommercial evaluation. Other eligible commercial use requires a paid Company License; entity size is unknown, so this is NOT cleared for an unqualified commercial launch. https://www.remotion.dev/docs/license/pricing

React, React DOM, Zod, fast-xml-parser, Express, faster-whisper: MIT. TypeScript: Apache-2.0. Pillow: HPND/MIT-CMU family, inspect the pinned distribution notice. Cairo/Noto Arabic/IBM Plex font families: SIL OFL 1.1; preserved original font notices plus public/fonts/Cairo-OFL.txt. Do not assume that possession of a TTF replaces its license notice. Full installed npm package license declarations: npm-license-inventory.json; an UNDECLARED entry requires upstream review. Transitive Python licenses are not exhaustively certified here.

FFmpeg: build-dependent LGPL/GPL, inspect `ffmpeg -L` for the installed binary, especially libx264 GPL. It is a system tool, not a relicensed bundled binary.

OpenMontage upstream LICENSE inspected: AGPL-3.0. MoneyPrinterTurbo upstream LICENSE inspected: MIT, copyright 2024 Harry. Architecture ideas only; NO source copied from either, so no undocumented AGPL code import. Models and generated image/voice use remain subject to their provider/model terms; generated media is not asserted to be CC0. Research article text is not an asset license. Original logo ownership supplied by channel owner; logo pixels not regenerated.

Noto Sans Arabic OFL 1.1 obtained from google/fonts upstream and retained in docs/Noto-OFL.txt.

Follow-up: @remotion/player 4.0.543 uses the same inspected Remotion license. Playwright Core 1.65.1: Apache-2.0, inspected installed package declaration/LICENSE. No additional paid library beyond Remotion eligibility.

Alignment dependencies: stable-ts2.19.1 MIT, OpenAI Whisper MIT, faster-whisper MIT, CPU PyTorch2.9.1 BSD-style and torchaudio2.9.1 BSD-style. Transitive installed distribution declarations retained separately when generated; not a blanket commercial clearance. Original model/provider terms continue to apply.
