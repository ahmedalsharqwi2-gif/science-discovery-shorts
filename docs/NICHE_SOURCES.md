# Niche sources

All calls send the User-Agent `NicheIntel/1.0 (+repo URL)`, cache results and cap rate. Each figure records source and fetch date. Failure or absence records `unknown`.

| Source | Type | Key | Default |
|---|---|---|---|
| Google Trends RSS (Egypt) | official public RSS, cached 6h | none | on |
| Wikimedia Pageviews API, ar.wikipedia | official API, cached 7d | none | on |
| Google News RSS (ar, EG) | public RSS, cached 12h | none | on |
| Reddit search RSS | public RSS, unofficial | none | off (config `sources.reddit`) |
| YouTube Data API v3 | official API | `YOUTUBE_API_KEY` | on when the secret exists |
| YouTube Analytics API (OAuth) | official API, feedback loop | not wired, CSV import instead | off |

Not used: search autocomplete suggestions and any scraping of protected pages.
Gemini (existing pooled keys) is used for bank ideas, quality-gap grading and packaging copy.
Without `YOUTUBE_API_KEY` the tool runs on free sources and reports competition metrics as unknown.
