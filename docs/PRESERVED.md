# Preserved materials

All listed bytes preserved at their original paths, except the Nafhamha identity receives a new rebuild_tokens member and its exact original is saved beside it as nafhamha-identity.original.json. The full original source remains on the verified backup branch and tag. Additional extracted topic identifiers are in state/legacy-topic-index.json; new reservations never overwrite that index.

| Original path | SHA256 before rebuild |
|---|---|
| `topic_history.json` | `a8cf21b1cd90d0039bd99823eb69c082a2e0f422379e2c57a5858bfcd8fe7d93` |
| `config/channel_identity.json` | `e630d4d625ecee6e2b48d1a511cdb43d28b2e421ba83082af0a000a3e5c2a606` |
| `config/arabic_pronunciation.json` | `942e37bd8c59e2295229348b01b403c09e2820f1593d4ee540b20bfdade205a2` |
| `state/science_visual_history.json` | `95bc6ec7115c4a8bc0323fa2535dccbe03588dac1957c1bcd6f6b2d513908e56` |
| `professional_motion/branding.json` | `e28364e79ca1f56ea6a45a0524fb0731979ebf9f70fa06e2784e6d25aaf53b85` |
| `remotion_motion/public/fonts/Arabic-Bold.ttf` | `ded6fc7359ca36d15d7aab9ef0c066e21ce48b26a069994d6602fa2cb9a1b952` |
| `remotion_motion/public/fonts/Arabic-Regular.ttf` | `504d7407d86875acf7d04dfaa0fd7524d0b8797723bc4aa18022f29db25b0b6e` |
| `photo_motion/assets/Noto-Fonts-Copyright.txt` | `075f91382875da1c4b491f1facf2586f55448705133264d98ce15cab6211b125` |
| `photo_motion/assets/NotoSansArabic-Bold.ttf` | `ded6fc7359ca36d15d7aab9ef0c066e21ce48b26a069994d6602fa2cb9a1b952` |
| `photo_motion/assets/NotoSansArabic-Regular.ttf` | `504d7407d86875acf7d04dfaa0fd7524d0b8797723bc4aa18022f29db25b0b6e` |
| `professional_motion/fonts/OFL-IBM-Plex.txt` | `7e6b2818edbd8f6a01ae80641cc8f16a51080d08fb4e532be3a0b6f74adb07da` |
| `professional_motion/fonts/Noto-Fonts-Copyright.txt` | `075f91382875da1c4b491f1facf2586f55448705133264d98ce15cab6211b125` |
| `professional_motion/fonts/NotoSansArabic-Bold.ttf` | `ded6fc7359ca36d15d7aab9ef0c066e21ce48b26a069994d6602fa2cb9a1b952` |
| `professional_motion/fonts/IBMPlexMono-Medium.ttf` | `a9b4c49bb299e05b5f6c481e7fb5e78943d2793249a0c8874ab574a2d1ea6755` |

Original logo present in checkout: no. The owner subsequently supplied inline logo references. Their original file bytes have not been exposed by the upload tool; no replacement has been drawn. See config/logo-intake.json. Original font files and their available notices remain. Charon and intended 17:00 Africa/Cairo destination names remain in config. No .mp4 files were tracked on the cloned main snapshots; no approved media was deleted from remote media branches. Legacy scheduling files are in the backup, but the new branch has only one active workflow.

## Follow-up original logo installation

Source: Owner supplied logos.zip / science-discovery-shorts.jpg

Canonical file: `brand/logo/logo.jpg`

SHA-256: `21b536514d9e76218d72aae06fe5c59ef61ac822db2f65ceef148b049ee0e227`

Byte-for-byte copy verified; no redraw, recolor, background removal, raster edit or vectorization. The public/brand/logo directory is a symlink to the canonical directory. Header, intro/outro and thumbnail use the same Logo component and source.
