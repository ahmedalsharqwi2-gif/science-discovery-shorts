# Bounded editorial recovery

An acknowledged draft that fails preflight gets at most one edit of the same topic before speech. It uses the configured text model and existing request budget; valid drafts make no extra call. The initial prompt plans words per scene.

The request intent and both drafts remain durable. The edit must keep the exact canonical topic, pass all preflight checks, and receive the original independent editorial review. Stickman retains its dialogue schema and normalizes the actual spoken turns. An invalid correction, exhausted quota or unknown request result stops for inspection rather than retrying. No voice or publication safety gate is disabled, no budget is increased, and no provider fallback is added.

The local suite covers normal drafts, durable intent before requests, ambiguous failures without retries, retained rejected corrections, topic identity, and the complete repair-to-independent-review handoff. It mocks provider calls and spends no generation credits.
