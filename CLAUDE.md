# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture

This is a static navigation homepage ("星元检验工具箱") that aggregates clinical laboratory tool links. The page is **data-driven**: `tools.json` is the single source of truth; `generate_nav.py` reads it and produces `index.html`. Never edit `index.html` directly — all changes go through `tools.json` or `generate_nav.py`.

The `/html/` directory contains standalone tool pages (phone directory, lab test query, weekend scheduler, eGFR calculator). Some tools link to external sites.

## Commands

- **Regenerate the page**: `python generate_nav.py` — reads `tools.json`, writes `index.html`
- **Adding a tool**: edit `tools.json` → run `generate_nav.py` to preview locally

## CI/CD

GitHub Actions (`.github/workflows/static.yml`) triggers on push to `main`:
1. Runs `python generate_nav.py`
2. Commits the regenerated `index.html` back to the repo
3. Deploys the entire repo to GitHub Pages

## Multi-site deployment

The same page is deployed to multiple mirrors (configured in `tools.json` → `siteUrls`). The site-switcher menu in the header detects which mirror the user is on and lets them switch.

## Key files

| File | Role |
|------|------|
| `tools.json` | Data: tool list + tag definitions + site mirror URLs |
| `generate_nav.py` | Template engine: reads JSON, outputs static HTML |
| `index.html` | Generated output, committed for direct viewing |
| `find_favicon.py` | Utility: extract favicon URLs from target websites |
