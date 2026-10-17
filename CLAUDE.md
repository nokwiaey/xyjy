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

### Lab test item change log (`html/data/item-changes.json`)

`html/data/item.json` (HIS 项目 / 收费价格 / LIS 关联) is re-exported by hand from the intranet from time to time, so the site cannot know when a project actually changed. `generate_item_changes.py` diffs the current export against the previous one (`html/data/item-snapshot.json`) and appends a change record to `html/data/item-changes.json`, which `html/lab-test-query.html` renders in the modal opened by clicking the header title ("点击查看数据更新与变更记录").

- Detected: HIS 项目增删改、收费明细与价格变化、LIS 检验分组 / 诊疗项目 / 分析项目、申请单变化
- 项目整体新增或删除时，其价格信息并入该条目，不再重复记一条价格变更
- LIS 以**诊疗项目**为单位记录：关联的分析项目作为该条目的明细一起展示（诊疗项目 ↔ 分析项目是一对多，与 HIS 项目 ↔ 收费明细同理），没有关联分析项目时明细为「（无）」。只有分析项目自身属性（名称 / 代号 / 互认标识）的变化、以及未挂任何诊疗项目的孤立分析项目增删，才单独成条
- No changes → no record is appended (only `lastCheckedAt` / `lastExportTime` in the file are refreshed); the very first run writes a baseline record instead
- Each record stores `recordedAt` (script run time; git commit time for backfilled records) and `exportTime` (export file time). **Neither is when the project changed** — a change is only known to fall between `prevExportTime` and `exportTime`, and the page says so explicitly
- `python generate_item_changes.py --backfill-git YYYY-MM-DD` rebuilds records from the git history of `item.json`, covering exports that happened before the script existed
- Future plan: run this script on a schedule inside the intranet so every export is recorded as it happens

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
- **Regenerate the item change log**: `python generate_item_changes.py` — diffs `html/data/item.json` against `html/data/item-snapshot.json`, appends a record to `html/data/item-changes.json`. Useful flags: `--init` (rebuild the baseline only), `--dry-run` (print the diff, write nothing), `--max-records N`
- **Backfill history from git**: `python generate_item_changes.py --backfill-git 2026-09-24` — rebuilds records from every commit of `item.json` on/after that date (commit time becomes `recordedAt`, records are marked `source: git` and the page labels them 提交于). Records already present for the same `exportTime` are replaced; `--dry-run` previews the result
- **After a manual `item.json` export**: 只需提交新的 `item.json`，CI 会在 push 后自动运行脚本并提交生成结果（详见「生成文件由 CI 生成，本地只拉取」）；本地预览可用 `--dry-run`，不要提交生成文件
- Times are recorded in `--tz-offset` (default `+8`, Beijing) so a UTC CI runner does not shift them

## CI/CD

GitHub Actions (`.github/workflows/static.yml`) triggers on push to `main`:
1. Runs `python generate_nav.py`, `python generate_schedule_manifest.py` and `python generate_item_changes.py`
2. Commits the regenerated `index.html`, `html/jyk_schedule/data/schedule.json`, `html/data/item-changes.json` and `html/data/item-snapshot.json` back to the repo
3. Deploys the entire repo to GitHub Pages

### 生成文件由 CI 生成，本地只拉取

`index.html`、`html/data/item-changes.json`、`html/data/item-snapshot.json`、`html/jyk_schedule/data/schedule.json` 是**生成文件**，由上面的 CI 流程在每次 push 后重新生成并提交回来。本地规则：

- **不要修改、不要提交这些文件**；本地提交只包含输入与源码（`item.json`、`item.formatted.json`、`tools.json`、`style.css`、`script.js`、`html/*.html`、`*.py` 等）
- 需要看到生成结果时用 `git pull` 拉取，不要在本地跑 `generate_*.py` 后提交产物（会和 CI 的提交打架）
- 与远端冲突时以 GitHub 生成的版本为准：这些文件在 `.gitattributes` 里标了 `merge=take-incoming`，配合下面的本地配置会在合并时自动采用传入（远端）版本
- 每台机器执行一次，启用本地保护：
  ```sh
  git config --local core.hooksPath .githooks     # 阻止本地提交生成文件
  git config --local merge.take-incoming.name "keep incoming (CI-generated) version"
  git config --local merge.take-incoming.driver "cp -f %B %A"   # 冲突时取远端版本
  git config --local pull.rebase false            # 始终用 merge，让「传入版本」= GitHub
  ```
  （Linux/macOS 还需 `chmod +x .githooks/pre-commit`）
- 拉取前若这些文件被本地改脏导致无法 pull：`git checkout -- index.html html/data/item-changes.json html/data/item-snapshot.json html/jyk_schedule/data/schedule.json` 再 pull
- 确需手工提交生成文件（例如生成脚本升级后首次修正历史数据）时：`git commit --no-verify`

Cloudflare Pages is also configured via `wrangler.jsonc` (deploys the entire repo as static assets).

## Multi-site deployment

The same page is deployed to multiple mirrors (configured in `tools.json` → `siteUrls`). The site-switcher menu in the header detects which mirror the user is on and lets them switch.

## Key files

| File | Role |
|------|------|
| `tools.json` | Data: tool list + tag definitions + site mirror URLs |
| `generate_nav.py` | Template engine: reads JSON + CSS + JS, outputs self-contained `index.html` |
| `generate_schedule_manifest.py` | Scans `html/jyk_schedule/data/*.pdf`, writes `data/schedule.json` for the schedule page |
| `generate_item_changes.py` | Diffs `html/data/item.json` exports, appends to `html/data/item-changes.json` and refreshes `html/data/item-snapshot.json` |
| `html/data/item-changes.json` | Generated change log rendered by the lab test query page (header-title modal) |
| `html/data/item-snapshot.json` | Baseline snapshot of the last diffed `item.json` — build input, not used by the page |
| `style.css` | Stylesheet, inlined into `index.html` at build time |
| `script.js` | Client-side JS (search, tags, theme, QR, recent visits, WeChat, etc.), inlined at build time |
| `index.html` | Generated output, committed for direct viewing |
| `sw.js` | Service Worker for offline caching (cache-first strategy) |
| `wrangler.jsonc` | Cloudflare Pages deployment configuration |
| `find_favicon.py` | Utility: extract favicon URLs from target websites |
