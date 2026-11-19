# YouTube Data API quota budget

Default project quota is 10,000 units per day. `search.list` costs 100 units, `videos.list` and `channels.list` cost 1 each.

One keyword lookup = 100 + 1 + 1 = 102 units. The cap in `config/selection_weights.json` (`quota.maxSearchCallsPerDay`, default 20) holds a day to about 2,040 units, roughly 20% of the default quota. The counter is stored per day, results are cached for 7 days, and the call is skipped (not retried) once the cap is reached. Raising the cap is a config change, reviewed in a PR.
