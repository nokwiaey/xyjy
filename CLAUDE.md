# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture

This is a static navigation homepage ("星元检验工具箱") that aggregates clinical laboratory tool links. The page is **data-driven**: `tools.json` is the single source of truth; `generate_nav.py` reads it, along with `style.css` and `script.js`, and produces a self-contained `index.html`. Never edit `index.html` directly — all changes go through the source files.

### Build pipeline

```
tools.json ──┐
style.css  ──┤──> generate_nav.py ──> index.html
script.js  ──┘
```

`generate_nav.py` inlines CSS/JS at build time so the output is a single HTML file with no external dependencies.

The `/html/` directory contains standalone tool pages (phone directory, lab test query, weekend scheduler, eGFR calculator). Some tools link to external sites. `/html/data/` holds JSON data files consumed by those tool pages.

### Schedule page (`html/jyk_schedule/`)

`html/jyk_schedule/index.html` is a file-driven PDF navigator: a vertical list on the left, an embedded PDF preview on the right. Schedule PDFs live in `html/jyk_schedule/data/` and follow a naming convention:

- monthly: `YYYY-MM-schedule.pdf` (e.g. `2026-09-schedule.pdf`)
- holiday: `YYYY-CODE-schedule.pdf`, where CODE is one of `YD` 元旦节, `CJ` 春节, `QM` 清明节, `LD` 劳动节, `DW` 端午节, `ZQ` 中秋节, `GQ` 国庆节 (Chinese names and common aliases are also accepted, e.g. `2026-劳动节.pdf`)

`generate_schedule_manifest.py` scans that directory and writes `html/jyk_schedule/data/schedule.json`, which lists every month and holiday of each year (missing files are marked `available: false` and render greyed out). **Adding a schedule is just dropping a PDF in and re-running the script** — the page itself defines no list.

The preview is a plain `<iframe>` on desktop, where browsers ship a built-in PDF viewer. **On mobile the list replaces the preview entirely** (tapping a row opens its PDF in a new window / 系统阅读器): Chrome for Android has no built-in PDF viewer, so an embedded PDF renders as a blank/error frame. Mobile detection lives in the page JS (`detectMobile()` + `body.mode-mobile`), keyed off the UA plus a coarse-pointer/narrow-viewport check, so a shrunken desktop window still gets the embedded preview.

### Client-side features

The page includes: dark/light theme toggle, search with keyboard navigation (Ctrl+K, arrow keys), tag-based filtering, recently visited tools (localStorage), copy-link buttons on cards, QR code modal, WeChat sharing integration, site-switcher menu for multi-mirror deployment, and Vercount visitor statistics.

`sw.js` provides **offline caching** via Service Worker (cache-first for static assets, network-first for navigations). Cache version is in the `CACHE_NAME` constant — bump it when assets change.

## Commands

- **Regenerate the page**: `python generate_nav.py` — reads `tools.json`, `style.css`, `script.js`, writes `index.html`
- **Adding a tool**: edit `tools.json` → run `generate_nav.py` to preview locally
- **Editing styles**: edit `style.css` → run `generate_nav.py`
- **Editing JS behavior**: edit `script.js` → run `generate_nav.py`
- **Regenerate the schedule manifest**: `python generate_schedule_manifest.py` — scans `html/jyk_schedule/data/*.pdf`, writes `html/jyk_schedule/data/schedule.json`
- **Adding a schedule**: drop the PDF into `html/jyk_schedule/data/` → run `generate_schedule_manifest.py`

## CI/CD

GitHub Actions (`.github/workflows/static.yml`) triggers on push to `main`:
1. Runs `python generate_nav.py` and `python generate_schedule_manifest.py`
2. Commits the regenerated `index.html` and `html/jyk_schedule/data/schedule.json` back to the repo
3. Deploys the entire repo to GitHub Pages

Cloudflare Pages is also configured via `wrangler.jsonc` (deploys the entire repo as static assets).

## Multi-site deployment

The same page is deployed to multiple mirrors (configured in `tools.json` → `siteUrls`). The site-switcher menu in the header detects which mirror the user is on and lets them switch.

## Key files

| File | Role |
|------|------|
| `tools.json` | Data: tool list + tag definitions + site mirror URLs |
| `generate_nav.py` | Template engine: reads JSON + CSS + JS, outputs self-contained `index.html` |
| `generate_schedule_manifest.py` | Scans `html/jyk_schedule/data/*.pdf`, writes `data/schedule.json` for the schedule page |
| `style.css` | Stylesheet, inlined into `index.html` at build time |
| `script.js` | Client-side JS (search, tags, theme, QR, recent visits, WeChat, etc.), inlined at build time |
| `index.html` | Generated output, committed for direct viewing |
| `sw.js` | Service Worker for offline caching (cache-first strategy) |
| `wrangler.jsonc` | Cloudflare Pages deployment configuration |
| `find_favicon.py` | Utility: extract favicon URLs from target websites |
