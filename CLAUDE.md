# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Weekly AI-powered release tracker for data engineering platforms (Databricks, Microsoft Fabric, Snowflake, BigQuery). Scrapes release notes, summarises with Claude API, and posts structured digests to a Google Chat channel every Monday at 08:00 CEST. See `REQUIREMENTS.md` for the authoritative spec and decision log.

## Commands

```bash
# Setup
uv sync                   # Install dependencies

# Run manually (one-off scrape + summarise + deliver cycle)
python main.py

# Run with scheduler (weekly Monday 08:00 CEST via APScheduler)
python main.py --schedule
```

## Architecture

Data flows in one direction: scrapers → storage → summariser → delivery.

```
src/scrapers/   — one file per platform, all extend BaseScraper (httpx + BS4)
src/storage.py  — JSON I/O in data/{platform}.json, deduplication by release ID
src/summariser.py — Anthropic Claude API (claude-sonnet-4-6) with prompt caching
src/delivery.py — Google Chat incoming webhook (httpx POST), idempotent
src/scheduler.py — APScheduler, Monday 08:00 CEST
src/config.py   — loads config.yaml (non-secrets) + .env (API key, webhook URL)
prompts/summarise.txt — versioned system prompt (structured output: new_features, deprecations, breaking_changes, client_relevance)
main.py         — entry point
```

## Configuration

| File | Purpose |
|------|---------|
| `config.yaml` | Platforms, schedule, backfill start date, max summary length |
| `.env` | `GEMINI_API_KEY`, `GOOGLE_CHAT_WEBHOOK_URL` |
| `.env.example` | Template committed to git |

## Key Constraints

- **Idempotent**: re-running must never post duplicate messages or reprocess seen releases
- **LLM**: summariser uses Google Gemini (`gemini-2.0-flash`) — free tier, no credit card required
- **Error handling**: if a platform scraper or API call fails, skip that platform and post a failure note — do not abort the full run
- **Storage v1**: JSON files; logic layer must stay storage-agnostic for a future SQLite migration

## Tracking Progress

Whenever a phase item is completed, update the corresponding checkbox in the `REQUIREMENTS.md` build plan (Section 8) from `- [ ]` to `- [x]`. Do this as part of the same work — don't leave `REQUIREMENTS.md` out of sync with what has actually been built.

## Tech Stack

Python 3.11+, `uv`, `httpx`, `beautifulsoup4` (possibly `playwright` for JS-rendered pages — validate per platform), `google-generativeai` SDK, `pydantic`, `apscheduler`, `pyyaml`, `python-dotenv`.
