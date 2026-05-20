# Feature Release Tracker — Requirements & Build Plan

## 1. Project Overview

A tool that monitors release notes for major data engineering platforms and delivers AI-generated summaries to a Google Chat channel on a weekly cadence. The goal is to keep consultants informed of the latest product developments so they can give clients the most up-to-date advice.

**Primary users:** Data engineering / AI consultants at AnalytixPower  
**Primary delivery:** Google Chat channel via incoming webhook  
**Future delivery:** Web application dashboard

---

## 2. Platforms to Track

| Platform | Release Notes Source |
|---|---|
| Databricks | https://docs.databricks.com/release-notes/ |
| Microsoft Fabric | https://learn.microsoft.com/en-us/fabric/fundamentals/whats-new |
| Snowflake | https://docs.snowflake.com/en/release-notes/ |
| BigQuery | https://cloud.google.com/bigquery/docs/release-notes |

> **Risk: JS-rendered pages.** Some of these release notes pages may be JavaScript-rendered SPAs that don't return useful HTML server-side. During Phase 2, each scraper must be validated against the actual page response. If a platform requires JS rendering, the scraper should use `playwright` (headless browser) instead of `httpx` + `BeautifulSoup`. Similarly, if a platform offers an RSS feed or public API for release notes, prefer that over scraping for reliability. This should be evaluated per platform during build time.

---

## 3. Functional Requirements

### 3.1 Data Collection
- Scrape or fetch release notes from each platform's public documentation
- Support configurable scraping schedules (default: weekly, Monday morning)
- Deduplicate releases to avoid reprocessing already-seen entries
- Store raw release data locally in JSON format (one file per platform)
- On each run, only collect releases published since the last run date

### 3.2 AI Summarisation
- Use the **Anthropic Claude API** (recommended: `claude-sonnet-4-6`) to generate summaries
- Each platform gets its own structured summary per weekly digest
- Summary format per platform:

```
### [Platform Name] — Week of [date]

**New Features**
- ...

**Deprecations & Removals**
- ...

**Breaking Changes**
- ...

**What This Means for Clients**
- ...
```

- Summaries must be consistent in tone, length, and structure across all runs
- Highly technical low-level details (e.g., internal API changes, patch-level bug fixes) should be filtered or deprioritised
- Client relevance framing covers a mix of: migrations, architecture decisions, cost optimisation, and new capability adoption

### 3.3 Delivery
- Post the weekly digest to a **Google Chat channel** via incoming webhook
- Message format: one structured card per platform, grouped in a single weekly post
- Schedule: **every Monday morning** (configurable via config file)
- If no new releases are found for a platform, note that explicitly rather than skipping the platform
- On **scraping or API failures**, post a notification to the Google Chat channel indicating which platform failed (e.g., "Failed to fetch Snowflake releases this week") so the team is aware without needing to check local logs

### 3.4 Configuration
- All configurable values live in a single `config.yaml` file:
  - Platforms to track (enable/disable per platform)
  - Scrape schedule (cron expression or simple interval)
  - Google Chat webhook URL
  - Anthropic API key reference (loaded from `.env`, not hardcoded)
  - Summary language (default: English)

---

## 4. Non-Functional Requirements

- **Local deployment** for first iteration — runs on a developer machine or lightweight server
- **No authentication** required in first iteration
- **No search/filter UI** in first iteration (nice-to-have for future)
- **Extensible by design** — adding a new platform should require minimal code changes (ideally only a config entry + a scraper module)
- **Idempotent runs** — running the tool twice in a row should not produce duplicate messages or duplicate stored data

---

## 5. Technology Recommendations

| Concern | Recommendation | Rationale |
|---|---|---|
| Language | Python 3.11+ | User familiarity, rich ecosystem for scraping + LLM + automation |
| Package manager | `uv` | Fast, modern Python package and project manager; replaces pip + venv |
| Scraping | `httpx` + `BeautifulSoup4` | Lightweight, async-capable, well-supported |
| LLM | Google Gemini API (`gemini-2.5-flash`) | Free tier, no credit card required, structured JSON output, sufficient quality for release summarisation |
| Local storage | JSON files (one per platform) | Simple, human-readable, easy to inspect and debug; straightforward migration to SQLite in v2 |
| Scheduling | `APScheduler` or system cron | APScheduler keeps everything in one Python process; cron is simpler for local use |
| Config | `python-dotenv` + `PyYAML` | Secrets in `.env`, non-secret config in `config.yaml` |
| Delivery | Google Chat incoming webhook (`httpx` POST) | No bot infrastructure needed; simple and reliable |

---

## 6. Data Storage Design (v1 — Flat JSON)

Each platform stores its data in `data/<platform>.json` with the following structure:

```json
{
  "platform": "databricks",
  "last_updated": "2026-05-20T08:00:00Z",
  "releases": [
    {
      "id": "databricks-2026-05-05",
      "date": "2026-05-05",
      "title": "Runtime 15.4 LTS",
      "raw_content": "...",
      "summary": {
        "new_features": ["..."],
        "deprecations": ["..."],
        "breaking_changes": ["..."],
        "client_relevance": ["..."]
      },
      "summarised_at": "2026-05-20T08:05:00Z"
    }
  ]
}
```

**v2 migration path:** Replace JSON files with SQLite (`releases` table, indexed by `platform` + `date`). No logic changes needed — only the storage layer changes.

---

## 7. Project Structure

```
feature-release-tracker/
├── config.yaml                  # Non-secret configuration
├── .env                         # API keys and webhook URL (gitignored)
├── .env.example                 # Template for .env
├── pyproject.toml               # uv project definition and dependencies
├── main.py                      # Entry point — run manually or via scheduler
├── src/
│   ├── scrapers/
│   │   ├── base.py              # Abstract base scraper class
│   │   ├── databricks.py
│   │   ├── fabric.py
│   │   ├── snowflake.py
│   │   └── bigquery.py
│   ├── summariser.py            # Claude API integration
│   ├── storage.py               # JSON read/write + deduplication
│   ├── delivery.py              # Google Chat webhook posting
│   ├── scheduler.py             # APScheduler setup
│   └── config.py                # Config loading (yaml + dotenv)
├── data/                        # Auto-created, gitignored
│   ├── databricks.json
│   ├── fabric.json
│   ├── snowflake.json
│   └── bigquery.json
└── prompts/
    └── summarise.txt            # The system prompt for Claude (versioned separately)
```

---

## 8. Build Plan — Phased Approach

### Phase 1 — Foundation (Week 1)
- [x] Set up project structure with `uv init` and configure `pyproject.toml`
- [x] Implement `config.py` — load `config.yaml` and `.env`
- [x] Implement `storage.py` — JSON read/write, deduplication logic
- [x] Write abstract `BaseScraper` class with shared interface

### Phase 2 — Scrapers (Week 1–2)
- [x] Implement Databricks scraper (RSS feed — 716 entries)
- [x] Implement Snowflake scraper (HTML — 4 most recent releases on index)
- [x] Implement BigQuery scraper (Atom feed — 30 entries)
- [x] Implement Microsoft Fabric scraper (HTML — GA features grouped by month)
- [x] Test each scraper independently, validate raw output

### Phase 3 — Summarisation (Week 2)
- [x] Write and iterate on the Claude system prompt (`prompts/summarise.txt`)
- [x] Implement `summariser.py` with structured output parsing
- [x] Enable prompt caching for cost efficiency on repeated summarisation runs
- [x] Validate summary quality and consistency across platforms

### Phase 4 — Delivery (Week 2–3)
- [x] Set up Google Chat channel and incoming webhook
- [x] Implement `delivery.py` — format and POST the weekly digest
- [x] Handle edge cases: no new releases, API failures, webhook errors

### Phase 5 — Scheduling & Polish (Week 3)
- [x] Implement `scheduler.py` — Monday morning cron trigger
- [x] Wire up `main.py` as the single entry point
- [x] Add basic logging throughout
- [x] Write `.env.example` and setup instructions in README
- [x] End-to-end test run

---

## 9. Nice-to-Haves (Future Iterations)

- Web app dashboard with search and filter (v2)
- SQLite storage backend (v2)
- Per-consultant topic subscriptions (v3)
- Slack integration alongside Google Chat (v3)
- Consultant-facing talking points per release (v2)
- Relevance scoring per release (v3)
- Microsoft Teams delivery (previously considered, deprioritised)

---

## 10. Decision Log

| # | Question | Current Decision |
|---|---|---|
| 1 | Which Monday time exactly? | 08:00 Amsterdam time (CEST, UTC+2) |
| 2 | Backfill / as-is comparison? | Removed — tool delivers weekly summaries of new releases only, starting from the first run |
| 3 | Max summary length per platform? | ~200 words per platform per digest |
| 4 | What happens if a platform's page structure changes and scraping breaks? | Log error, skip platform, still post digest with a note |
