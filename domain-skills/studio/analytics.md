---
name: studio-youtube-analytics
description: Control every filter, toggle, breakdown, metric, and export on YouTube Studio's Analytics → Advanced mode. URL-driven, with UI fallbacks for the few things URL params can't express.
---

# YouTube Studio — Analytics Advanced Mode

Studio's Advanced-mode explore page (`/channel/<CID>/analytics/tab-overview/period-default/explore`) is **almost entirely URL-driven**. Every filter, dimension, metric-column set, sort, chart type, granularity, and date range lives in the query string. Get the URL right and the UI is a side-effect.

## ⚠ Critical gotcha (this is what silently breaks the page)

Studio's router **requires these params even when empty**. Omit any of them and the page renders an empty black pane with hidden `<ytcp-error-section>` children and no `yta-*` components — looks dead, reload doesn't help, there is no user-visible error.

- **Duplicate empty params** for every filter that has a secondary/comparison slot:
  - `ur_values=&ur_values=%27VIDEO_ON_DEMAND%27`
  - `ur_inclusive_starts=20240101&ur_inclusive_starts=`  (primary value + empty secondary)
  - `ur_exclusive_ends=20250101&ur_exclusive_ends=`
- **`t_metrics=...` array** with the metrics shown as table columns. A single `t_metrics` may work; omitting the array entirely breaks the page.
- **`metric=...`** and **`o_column=...`** must name real metric enums.

When in doubt, build URLs from the template in `studio_url()` below.

## URL parameter schema

| Param | Type | Example | Meaning |
|---|---|---|---|
| `entity_type` | enum | `CHANNEL` | Scope (CHANNEL/VIDEO/PLAYLIST/...) |
| `entity_id` | string | `UC9JWnvl5ZjZv09F5RqiLptw` | Channel/Video ID |
| `ur_dimensions` | repeat | `VIDEO_PUBLISH_DATE`, `CREATOR_CONTENT_TYPE`, `GEOGRAPHY`, ... | Applied filter dimensions (filter chips) |
| `ur_values` | repeat, paired w/ `ur_dimensions` | empty, `%27VIDEO_ON_DEMAND%27` | Value per dimension. Quoted enum for content type |
| `ur_inclusive_starts` | YYYYMMDD + empty dup | `20240101`, `` | Primary start date (dup required) |
| `ur_exclusive_ends` | YYYYMMDD + empty dup | `20250101`, `` | Primary exclusive end date |
| `time_period` | enum | `lifetime`, `last_7_days`, `last_28_days`, `last_90_days`, `last_365_days`, `year_to_date`, `custom` | Chart time range |
| `explore_type` | enum | `TABLE_AND_CHART`, `TABLE_ONLY`, `CHART_ONLY` | Layout |
| `metric` | enum | `EXTERNAL_VIEWS`, `AVERAGE_WATCH_TIME`, `RECENT_VIEWERS` | Primary chart metric |
| `granularity` | enum | `DAY`, `WEEK`, `MONTH` | Chart bucket |
| `t_metrics` | repeat | see metrics list below | Table columns (order matters visually) |
| `dimension` | enum | `VIDEO`, `GEOGRAPHY`, `TRAFFIC_SOURCE`, ... | Table row dimension |
| `o_column` | enum | `EXTERNAL_VIEWS` | Sort column (must appear in `t_metrics`) |
| `o_direction` | enum | `ANALYTICS_ORDER_DIRECTION_DESC` / `_ASC` | Sort direction |

### Content-type enum values (for `ur_values` when filtering `CREATOR_CONTENT_TYPE`)
Quoted-percent-encoded: `%27VIDEO_ON_DEMAND%27`, `%27SHORT%27`, `%27LIVE_STREAM%27`, `%27POST%27`.

### Metric enums (for `metric`, `o_column`, `t_metrics`)
```
EXTERNAL_VIEWS, EXTERNAL_WATCH_TIME
AVERAGE_WATCH_TIME, AVERAGE_WATCH_PERCENTAGE
RECENT_VIEWERS, RETURNING_VIEWERS, OCCASIONAL_VIEWERS, FREQUENT_VIEWERS
SUBSCRIBERS_GAINED, SUBSCRIBERS_LOST, SUBSCRIBERS_NET_CHANGE
RATINGS_LIKES, RATINGS_DISLIKES, LIKES_PER_LIKES_PLUS_DISLIKES_PERCENT
SHARINGS, COMMENTS
HYPES, HYPE_POINTS
TOTAL_ESTIMATED_EARNINGS
VIDEO_THUMBNAIL_IMPRESSIONS, VIDEO_THUMBNAIL_IMPRESSIONS_VTR
ENGAGED_VIEWS, UNIQUE_VIEWERS, AVERAGE_VIEWS_PER_VIEWER
NEW_VIEWERS
IMPRESSIONS, IMPRESSIONS_CTR, STAYED_TO_WATCH
VIDEOS_ADDED, VIDEOS_PUBLISHED
```

### Breakdown (`dimension`) enums — table row types
Observed in the Breakdown dropdown:
```
VIDEO (Content), TRAFFIC_SOURCE, GEOGRAPHY, CREATOR_CONTENT_TYPE (Content type),
PLAYLIST, PODCAST, COURSE, POST,
CITIES, VIEWER_AGE, VIEWER_GENDER, NEW_AND_RETURNING_VIEWERS,
AUDIENCE_BY_WATCH_BEHAVIOR, SUBSCRIPTION_STATUS, SUBSCRIPTION_SOURCE,
YOUTUBE_PRODUCT, DEVICE_TYPE, OPERATING_SYSTEM, ORGANIC_AND_PAID_TRAFFIC,
DATE, SUBTITLES_AND_CC, VIDEO_INFO_LANGUAGE, AUDIO_TRACK, TRANSLATION_USE,
END_SCREEN_ELEMENT, END_SCREEN_ELEMENT_TYPE, CARD, CARD_TYPE,
PLAYBACK_LOCATION, PLAYER_TYPE, SHARING_SERVICE
```
(User-visible label → likely enum; verify by clicking and reading the resulting URL.)

## UI control map

Viewport is 1492×786 at 2x Retina. Coordinates below are the CENTER of each control.

### Top header (y ≈ 32–105)
| Label | Center | Selector (shadow-piercing) |
|---|---|---|
| Report dropdown (Content/Overview/etc) | (306, 32) | `ytcp-text-dropdown-trigger` with text `"Report"` |
| Close (X) | (1448, 34) | `ytcp-icon-button[aria-label="Close"]` |
| Send feedback | (1400, 36) | `ytcp-icon-button[aria-label="Send Feedback"]` |
| **Advanced mode** page-title row at y=101 |  | |
| Save report (bookmark) | (1408, 105) | `ytcp-icon-button[aria-label="Save report"]` or `yta-explore-bookmark-toggler` |
| **Export current view** | (1448, 105) | `ytcp-icon-button[aria-label="Export current view"]` |
| Show chart toggle | (1319, 105) | `button` with text `"Show chart"` |

### Left control panel (x ≈ 128, varies by year)
| Control | Center | Custom tag |
|---|---|---|
| Add comparison | (128, 99) | `ytcp-button` |
| Channel/entity selector (e.g. "SCALER") | (128, 205) | `yta-explore-entity-dropdown-v2` |
| Time / date-range picker | (128, 273) | `yta-time-picker` |
| Breakdown (dimension) | (128, 389) | `yta-explore-column-picker-dropdown` |
| Metrics preset picker | (128, 501) | `yta-explore-column-picker-dropdown` (second one) |
| Filter chip: Publish date | (125, 617) | `ytcp-chip` |
| Filter chip: Content type | (79, 657) | `ytcp-chip` |
| Search for filter (input) | (129, 697) | `input` |

### Chart toolbar (y ≈ 169)
| Control | Center | Tag |
|---|---|---|
| Chart type (Line / Bar / Area) | (1271, 169) | `ytcp-dropdown-trigger` |
| Granularity (Daily / Weekly / Monthly) | (1406, 169) | `ytcp-dropdown-trigger` |

### Export dropdown (opens after clicking Export at y=105)
| Option | Location (approximate) | Behavior |
|---|---|---|
| Google sheets (new tab) | (1318, 113) | Opens a Google Sheet in a new tab |
| Comma-separated values (.csv) | (1318, 145) | Downloads a ZIP with `Table data.csv`, `Chart data.csv`, `Totals.csv` |

Positions of dropdown items are reflowed — find them by text with the helper below rather than hardcoding y-coords.

## Python helpers

Copy into any `browser-harness <<'PY' ... PY` block.

```python
from urllib.parse import urlencode

DEFAULT_T_METRICS = [
    "AVERAGE_WATCH_TIME", "AVERAGE_WATCH_PERCENTAGE",
    "RECENT_VIEWERS", "RETURNING_VIEWERS", "OCCASIONAL_VIEWERS", "FREQUENT_VIEWERS",
    "HYPES", "HYPE_POINTS",
    "SUBSCRIBERS_GAINED", "SUBSCRIBERS_LOST",
    "RATINGS_LIKES", "RATINGS_DISLIKES", "LIKES_PER_LIKES_PLUS_DISLIKES_PERCENT",
    "SHARINGS", "COMMENTS",
    "EXTERNAL_VIEWS", "EXTERNAL_WATCH_TIME",
    "SUBSCRIBERS_NET_CHANGE", "TOTAL_ESTIMATED_EARNINGS",
    "VIDEO_THUMBNAIL_IMPRESSIONS", "VIDEO_THUMBNAIL_IMPRESSIONS_VTR",
]

def studio_url(channel_id, start="20240101", end="20250101",
               dimension="VIDEO",
               content_type="VIDEO_ON_DEMAND",   # or "SHORT", "LIVE_STREAM", "POST", or None for all
               metric="AVERAGE_WATCH_TIME",
               granularity="DAY",
               t_metrics=None,
               sort_by="RECENT_VIEWERS",
               sort_dir="DESC",
               time_period="lifetime"):
    """Build a valid YT Studio analytics-explore URL that Studio's router will actually hydrate."""
    t_metrics = list(t_metrics or DEFAULT_T_METRICS)
    # Manual query-string build because urlencode collapses duplicate keys we need to keep.
    parts = [
        ("entity_type", "CHANNEL"),
        ("entity_id", channel_id),
        ("ur_dimensions", "VIDEO_PUBLISH_DATE"),
        ("ur_dimensions", "CREATOR_CONTENT_TYPE"),
        ("ur_values", ""),
        ("ur_values", f"'{content_type}'" if content_type else ""),
        ("ur_inclusive_starts", start),
        ("ur_inclusive_starts", ""),     # required duplicate empty
        ("ur_exclusive_ends", end),
        ("ur_exclusive_ends", ""),       # required duplicate empty
        ("time_period", time_period),
        ("explore_type", "TABLE_AND_CHART"),
        ("metric", metric),
        ("granularity", granularity),
    ]
    for m in t_metrics:
        parts.append(("t_metrics", m))
    parts.extend([
        ("dimension", dimension),
        ("o_column", sort_by),
        ("o_direction", f"ANALYTICS_ORDER_DIRECTION_{sort_dir.upper()}"),
    ])
    qs = urlencode(parts)  # handles URL-encoding of %27 etc
    base = f"https://studio.youtube.com/channel/{channel_id}/analytics/tab-overview/period-default/explore"
    return f"{base}?{qs}"
```

### Flow: export a CSV ZIP for an arbitrary date range

```python
import time, os, shutil, json

def studio_export_csv(channel_id, start, end, dest_path=None, **kwargs):
    """Navigate to the date range, wait for the table, click Export → CSV, return downloaded path."""
    url = studio_url(channel_id, start=start, end=end, **kwargs)
    focus_browser()
    # Ensure we're on a Studio tab (or create one)
    t = find_tab(url_substr="studio.youtube.com")
    if t:
        switch_tab(t["targetId"])
    goto(url)
    wait_for_load(timeout=25)
    # Wait for the table to hydrate — yta-explore-table-row confirms analytics data rendered.
    if not wait_for_element("yta-explore-table-row", timeout=25, visible=True):
        raise RuntimeError(f"Studio table didn't hydrate — URL likely malformed: {url}")
    time.sleep(1.0)  # allow any lingering chart XHR to finish

    before = snapshot_downloads()
    click_deep('ytcp-icon-button[aria-label="Export current view"]')
    time.sleep(1.2)

    # Find CSV menu option by text (position shifts slightly)
    csv = js(r"""
    (() => {
      function* walk(root) {
        if (!root || !root.querySelectorAll) return;
        for (const el of root.querySelectorAll('tp-yt-paper-item')) yield el;
        for (const el of root.querySelectorAll('*')) if (el.shadowRoot) yield* walk(el.shadowRoot);
      }
      for (const el of walk(document)) {
        const t = (el.innerText || '').trim().toLowerCase();
        if (t.includes('.csv') || t.includes('comma-separated')) {
          const r = el.getBoundingClientRect();
          if (r.width > 0) return JSON.stringify({x: r.x + r.width/2, y: r.y + r.height/2});
        }
      }
      return null;
    })()
    """)
    if not csv: raise RuntimeError("export CSV menu option not found")
    pos = json.loads(csv)
    click(pos["x"], pos["y"])

    path = wait_for_download(before_files=before, timeout=120, stable_seconds=2.0)
    if not path: raise RuntimeError("download did not complete within 120s")
    if dest_path:
        shutil.move(path, dest_path)
        path = dest_path
    return path
```

### Flow: change the breakdown (table row dimension)

Two ways, prefer URL:

**(a) URL** — just call `studio_url(..., dimension='GEOGRAPHY')` and `goto(...)`.

**(b) UI click** — useful when you want to preserve other URL state:

```python
# Open Breakdown dropdown
click(128, 389)      # y may shift if filter chips change; re-probe via query_deep('yta-explore-column-picker-dropdown')
time.sleep(0.6)
# Click the option by visible text
click_deep('tp-yt-paper-item')  # first; better: find by text
# Or, targeted:
hit = js(r'''(()=>{
  for (const el of document.querySelectorAll("tp-yt-paper-item")) {
    const t=(el.innerText||"").trim();
    if (t === "Geography") { const r=el.getBoundingClientRect(); return JSON.stringify({x:r.x+r.width/2,y:r.y+r.height/2}); }
  }
  return null;
})()''')
```

### Flow: change filter chips (Publish date, Content type)

Clicking a chip opens an editor popup. For `Publish date`, the popup exposes a date-range input + preset list (Last 7 / Last 28 / This year / Lifetime / Custom). For `Content type`, it exposes checkboxes for Videos / Shorts / Live / Posts.

URL-level control is always cleaner: change `ur_inclusive_starts` / `ur_exclusive_ends` for date, or `ur_values` (second slot) for content type.

### Flow: add a comparison (second time range overlaid on the chart)

The "Add comparison" button (128, 99) opens a preset list (Previous period / Previous year / Custom). When set, it writes a second value into the already-duplicated `ur_inclusive_starts` / `ur_exclusive_ends` slots (that's why the empty duplicates are required — they are placeholders for the comparison range).

To set via URL:
```python
# Example: compare 2024 vs 2023
parts.append(("ur_inclusive_starts", "20230101"))  # replaces the empty second slot
parts.append(("ur_exclusive_ends", "20240101"))
```

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Screenshot completely dark, no `yta-*` elements in DOM, no XHR fires, reload does not recover | URL malformed (missing duplicate date params, missing `t_metrics` array, or unknown enum value) | Rebuild URL via `studio_url()` |
| `click_deep("Export current view")` not found | Page is pre-hydrate; OR Studio reflowed and changed viewport size | `wait_for_element("yta-explore-table-row", timeout=25)` before clicking Export |
| Download never arrives | Studio queued the export but user was logged out mid-request, or the CSV option click hit a different element | Check `console_messages(level='error')` and `network_requests(status=401)` |
| Export ZIP has `Chart data.csv` covering the whole channel lifetime even though filter is set | Expected — Chart data always spans lifetime of the filtered videos. `Table data.csv` is the filtered set |
| Rows visible in UI don't match ZIP row count | UI virtualizes rows (only ~20 rendered at a time); the ZIP has all filter-matching rows. Trust the ZIP |

## Recorded observations (2026-04-19)

- Channel SCALER (`UC9JWnvl5ZjZv09F5RqiLptw`): 2024 VOD filter → 94 videos; 2026 YTD → ~20 rows
- Daemon buffer: the 500-event limit fills fast on Studio; call `drain_events()` or `network_requests(clear=True)` periodically if you're reading events across many steps
- `Target.activateTarget` brings the tab forward within Chrome, but does not raise Chrome.app over other macOS apps — always call `focus_browser()` before Studio flows, otherwise virtualized tables stall

## Switching to a brand-account channel (multi-channel Google accounts)

One Google login often has many channels (brand accounts). Studio defaults to the last-active one; navigating `studio.youtube.com/channel/<otherCID>` directly shows **"Oops, you don't have permission… Switch account"** — the *session identity* must be switched first. The in-Studio "Switch account" button is flaky; the reliable path is the youtube.com avatar menu:

1. `goto("https://www.youtube.com")`, click the avatar (top-right; in a 1200-wide viewport it's ~`(1152,28)` at 2× — re-probe per layout), then **Switch account**.
2. Click the target channel's account row (match the `@handle`, not the name — handles disambiguate e.g. "Masoom Minawala" vs "The Masoom Minawala Show Clips").
3. `goto("https://studio.youtube.com")` → now lands on that channel; grab the CID from the redirected URL.

The selection persists in cookies (and survives a profile copy — see connection.md autonomous-profile note).

## Per-VIDEO advanced explore (different recipe from channel scope)

For a single video, `entity_type=VIDEO` and base path `…/video/<vid>/analytics/tab-overview/period-default/explore`. **`time_period` must be a per-video value (`since_publish` or `4_weeks` / `28_days`), NOT `lifetime`** for `TABLE_AND_CHART` — `lifetime`+VIDEO black-p"anes the same way a malformed URL does. Read the real auto-generated links off the video analytics page (`a[href*=explore]`) to copy current enums; observed working set:

- `explore_type=TABLE_AND_CHART` + `dimension=DATE` (granularity=DAY) → daily time-series (for day-N cohort / decay). Total **Views** appears in the export by default even if `VIEWS` isn't in `t_metrics`.
- `dimension=TRAFFIC_SOURCE` → Browse / Suggested / Search / External split.
- `dimension=SUBSCRIPTION_STATUS` → subscribed vs not (pair with `IMPRESSIONS_CTR` for subs-vs-non-subs CTR).
- `explore_type=AUDIENCE_RETENTION` → the retention curve; `explore_type=LATEST_ACTIVITY` → recent activity.
- `metric=VIEWS` black-panes in some VIDEO views; `EXTERNAL_VIEWS` is the safe chart `metric`/`o_column` for hydration (the export still carries the real Views column).

## Channel-scope export recipe (field-tested 2026-06-19, Masoom `UCCDls-tg021M45i4LfDY_4A`)

`studio_url(cid, start, end)` with **`time_period="lifetime"`** and the dates used only as the **publish-date filter** hydrates reliably (17 long-form rows for a Mar–Jun publish window). Setting `time_period="last_90_days"` *with* explicit `ur_inclusive_starts/ends` black-panes — keep `time_period="lifetime"` and let the date params be the filter. Export → ZIP with `Table data.csv` (the filtered set: 25 cols incl. Impressions, CTR, AVD, retention, like-ratio, comments, subs, revenue), `Chart data.csv` (only the chart's *selected* metric over the date axis for the sorted subset — NOT a clean per-video daily matrix; use the per-video DATE explore for that), and `Totals.csv`.

## Per-video analytics TABS render blank on deep-link — load Overview, then CLICK the tab (field-tested 2026-06-19)

A LOT of per-video data is **not in the CSV export** — it lives in the rendered analytics tabs. Getting them to render reliably:

- `…/video/<vid>/analytics/tab-overview/period-since_publish` (the **Overview** tab) **renders on direct nav**.
- The other tabs (`tab-reach`, `tab-engagement`, `tab-audience`, `tab-revenue`) and the `…/explore` pages **cold-load BLANK on a direct deep-link** (content area empty, 0 `yta-*` rows — looks like the malformed-URL black pane but isn't). They only render via **in-app navigation**: load Overview first, then **click the tab by its visible text** ("Reach"/"Engagement"/…). If still blank, **`js("location.reload()")` recovers it** (the "just refresh it" trick, automated). Use `cdp("Page.reload")` ❌ — it drops the daemon WS; `location.reload()` or a re-click is safe. Drain the CDP event buffer between steps (`drain_events()`), heavy Studio pages flood it and cause `keepalive ping timeout`.
- The data is in rendered **innerText** (not the export). What each tab carries (per video, "Since published"):
  - **Overview**: views, watch time, subs, est. revenue, the **"typical performance" cohort band** ("…similar to the 6,500–17,900 your videos usually get" + per-metric "about the same / more than usual" labels — YouTube's own peer comparison), and **traffic sources** with % + view counts.
  - **Reach**: **Impressions**, **Impressions CTR**, unique viewers, traffic-source breakdown, external sites.
  - **Engagement**: watch time, **AVD** (+ "X more/less than usual"), **avg % viewed (retention)**, key moments (intro/top/dip), retention-vs-typical curve, **like ratio**, Hype.
  - **Audience**: unique viewers, returning/new, device type, **age & gender**, "viewers also watch". (Subs-vs-non-subs split is behind a "See more" / the SUBSCRIPTION_STATUS explore.)
  - **Revenue**: est. revenue, **CPM**, **RPM**, ad types.

Reference implementation: `client_analytics/masoom_minawala/tools/studio_pull.py` (boots Overview, clicks each tab, reload-retries blanks, dumps all five tabs + a quick-parse of headline numbers to JSON).

## Per-VIDEO Advanced mode — the reliable operating playbook (field-tested 2026-06-19)

Per-video Advanced/explore **blanks on deep-link** (even with `metrics_computation_type=DELTA` + the `v_metrics` array that Studio's own links carry). Drive it IN-APP:

1. **Open**: load the Overview tab, click **"Advanced mode"** (top-right, ~x>850 y<180). Verify `location.href` contains `/explore` AND a `yta-explore-table-row` exists; retry the click (don't reload — reload blanks it).
2. **Date**: left **date control** (~`(128,273)`) → presets: `First 24 hours`, `Last 7 / 28 / 90 / 365 days`, **`Since published`**, `Since uploaded (lifetime)`, year/month, `Custom`. (Default opens at "Last 28 days" — set `Since published` for full-life.)
3. **Breakdown**: left **dropdown** (~`(128,389)`) opens a **LONG SCROLLABLE menu** — lower options are below the fold, so `el.scrollIntoView({block:'center'})` the target option *then* coordinate-click it, and **verify the control's displayed value changed** (`document.elementFromPoint(128,389)` text). A "table exists" check is NOT enough — it passes on the stale previous table (this caused Device/Subscription/Date to silently return *Cities* data). The 31 dimensions: Content, Traffic source, Geography, Post, Cities, Viewer age, Viewer gender, New and Returning Viewers, Audience by watch behavior, Subscription status, Subscription source, YouTube product, Device type, Operating system, Revenue source, Ad type, Transaction type, Organic and paid traffic, Date, Subtitles and CC, Video info language, Audio track, Translation use, End screen element, End screen element type, Card, Card type, Playback location, Player type, Sharing service, Remixes of this video.
4. **Metrics (⊕ column picker)**: the `+` button by the table header opens ~81 metrics in categories. **Checked state = the `checked` ATTRIBUTE** (not `aria-checked`); the **element `id` IS the metric enum** (Views=`EXTERNAL_VIEWS`, Impressions=`VIDEO_THUMBNAIL_IMPRESSIONS`, CTR=`VIDEO_THUMBNAIL_IMPRESSIONS_VTR`, etc. — full map saved at `masoom_minawala/analysis/weekly_review/studio_metric_enums.json`). To toggle, coordinate-click the **left checkbox SQUARE** (`r.x+9`) — clicking the row/label center does NOT toggle; JS `.click()` does NOT toggle. **Usually unnecessary**: the CSV export already carries a comprehensive default column set.
5. **Export**: download icon top-right → "Comma-separated values (.csv)" → ZIP (`Table data.csv` = the breakdown × metrics; `Chart data.csv`; `Totals.csv`). More reliable than scraping cells.

**⚠ Data-freshness lag**: Advanced/explore lags the Overview/Realtime tabs by ~1–2 days (e.g., a 3-day-old video read 10,893 views in Advanced vs 13,575 in the Overview/realtime). Use the **tabs/realtime for the freshest headline**, **Advanced for the exact dimensional breakdowns**.

**AI / insight surfaces** (the natural-language "AI" info): per-video cards phrase performance vs the channel's own history — "…similar to the 6,500–17,900 your videos usually get", "Nice work! …kept your viewers watching for longer than usual", "48% of viewers are still watching at 0:30, which is typical". The channel dashboard adds **"Ask Studio"** (AI assistant), **"Ideas for you"**, **"See what's trending"**.

Reference tools: `studio_advanced_pull.py` (in-app open → per-breakdown export, scroll-into-view + verify), `consolidate_video_data.py` (tabs + breakdown CSVs → one complete record).

## Completeness gotchas (field-tested 2026-06-19)

- **The CSV export DOES respect the ⊕ metric checkboxes — but you must WAIT for the on-screen table to repopulate with the checked columns before exporting** (verified: checking a metric + waiting + exporting added that column to the CSV). If you export too soon (before the table re-renders the new columns) you get the previous/default columns and wrongly conclude the checkboxes are ignored. Sequence: tick boxes → Apply → wait for the table to show the new columns → export.
  - **⚠ Automating the ⊕ panel is finicky — go VISUAL-FIRST: `screenshot()` and dump element rects, THEN code the clicks.** Real geometry found 2026-06-19: the **⊕ add-metric button sits in the table header at ~y 374** (not up by the toolbar); the **metric checkboxes are at x≈567**, while **x≈304 checkboxes are the table ROW-selectors** (clicking those does nothing to columns); the metric list extends below the viewport. Toggle by clicking the LEFT square (`r.x+9`); `checked` attribute = state; element `id` = enum. Apply button ~bottom of the panel. **In practice, skip the panel entirely** — see the URL recipe below.

## DEFINITIVE per-video metric/dimension recipe + its hard limit (2026-06-19)

- **Columns = URL `t_metrics`; dimension = URL `dimension`** (enum map: label→enum, e.g. Geography=`COUNTRY`, Device=`DEVICE_PLATFORM_TYPE`, Subscription status=`SUBSCRIBED_TO_UPLOADER_STATE`, Traffic source=`TRAFFIC_SOURCE_TYPE`; full map saved at `masoom_minawala/analysis/weekly_review/studio_dimension_enums.json`).
- **`goto` changes `t_metrics` for the *already-active* dimension, but does NOT switch the dimension** (it falls back to the video-level/Content view). To change dimension you MUST use the **Breakdown dropdown** (left panel ~`(128,389)`, scrollIntoView the option, verify via `elementFromPoint(128,389)` text). So the recipe to render dimension X with all metrics: dropdown→X, then `goto` the *current* URL with all `t_metrics` appended.
- **HARD LIMIT on extracting all metrics:** with many columns the table renders all of them on-screen, BUT (a) the **CSV export button disables** ("Exporting is not available for the current view") once you override columns via URL / exceed a cap — only the *default* column set per dimension exports cleanly; and (b) **reading the wide table is unreliable** — row cells are nested in an opaque `div` with no per-cell selector, so `innerText`-split misaligns values vs headers on rows with sparklines/empties (verified wrong against YT's own export). 
- **⊕ metric panel — what's cracked (2026-06-19), and the one stuck piece:**
  - **+ button selector (stable):** `ytcp-icon-button[aria-label="Add metric to table"]`. Breakdown control: first `yta-explore-column-picker-dropdown`. Export: `ytcp-icon-button[aria-label="Export current view"]`. Use these, NOT coordinates.
  - **On the Content breakdown, adding metrics via the + menu keeps EXPORT ENABLED** (URL-overriding columns is what disables export — avoid that). So: Content breakdown → + → tick metrics → Apply → export works. Column selection persists across breakdown changes, so tick once then switch dimension + export each.
  - **Checkboxes are LIGHT DOM**, `id`=metric enum, `checked` attribute=DOM state. **The app ignores SYNTHETIC events** (`isTrusted=false`): `el.click()` / `el.dispatchEvent(MouseEvent)` / setting `el.checked=true` flip the *attribute* but NOT the app's model (Apply ignores them) — and they POLLUTE the attribute so you lose track of true state (re-warm to reset). Only **trusted compositor clicks** (CDP `Input.dispatchMouseEvent` via `click(x,y)` at the box's `r.x+9`) update the model.
  - **SOLVED (2026-06-19) — full programmatic all-metrics, aligned. The working recipe:**
    1. The metric list scroller is the ancestor `div` with `overflow-y:auto` & `scrollHeight>clientHeight`; **`scrollTop` on THAT element scrolls it** (an earlier failure was finding the wrong ancestor whose rect read garbage).
    2. **Metrics are grouped under COLLAPSIBLE category dropdowns** — the real categories are: Overview, Reach, Interactions, Revenue, Shopping, Premium, Playlists, Live, Posts, Remix, Clips, Cards, Endscreens. **Expand EVERY one by name via `el.scrollIntoView({block:'center'})` then click the header center** (a scroll-band scan silently skips edge categories like Endscreens — iterate the explicit name list instead). A category is collapsed iff NO isBox-verified metric sits within ~45px below its header.
    3. **Only click a checkbox where `document.elementFromPoint(r.x+11, center-y)` lands INSIDE the box** — off-screen boxes report garbage rects; and the app ignores synthetic events, so use real compositor `click(x,y)` on the **left square (`r.x+11`)**, not the label center.
    4. Apply → **wait for the table to repopulate** → export (works on the Content breakdown; the URL-override path is what disabled it).
    5. **Changing the breakdown RESETS the columns**, so repeat the expand+check per dimension. Result: Content → 59 cols; per-breakdown all-available metrics, all YT-export-ALIGNED (device 39, geography 50, etc.).
  - Reference tools: `studio_select_all_metrics.py` (Content) and `studio_allmetrics_per_breakdown.py` (every breakdown). Enum maps: `studio_metric_enums.json`, `studio_dimension_enums.json`.
  - **CATALOG-WIDE all-metrics (2026-06-20): same ⊕ method at CHANNEL scope, "Content" breakdown** → every video × all metrics in one CSV (175 rows × 48 cols incl subs gained/lost, like-ratio, comments, shares). Tool: `studio_catalog_allmetrics.py`. TWO hard-won gotchas the click recipe alone trips on:
    - **The metric picker renders DUPLICATE checkbox-lit DOM nodes** (a hidden set at x≈0 + a visible set at x>500) AND, for some groups (notably the **"Hypes"/Interactions group** = subs gained/lost, likes, dislikes, like-ratio, shares, comments, hypes), the visible nodes **overlap a sibling node**, so `elementFromPoint(r.x+11, cy)` returns a *different* checkbox-lit → the inside-gate reads FALSE and a compositor click hits the ghost (no toggle). These get silently skipped by the click+inside-gate method (that's why a 65-metric `select_all` still missed all 9 Interactions metrics).
    - **FIX — toggle by KEYBOARD, not mouse, for overlapped boxes:** find the VISIBLE instance (`[...document.querySelectorAll('ytcp-checkbox-lit[id="X"]')].find(b=>b.getBoundingClientRect().x>500)`), scroll the picker's own scroller so it's centered (`scrollTop`, not `scrollIntoView` — the latter scrolls the page not the dialog), then `el.querySelector('[tabindex]').focus()` + `press_key("Space")`. A trusted Space goes to the focused element regardless of what's painted on top. Verify by re-reading the `checked` attribute on ANY instance of that id. This toggled all 9 where clicks failed across ~7 attempts.
    - Open the panel idempotently: only click the ⊕ if no box is visible (`x>500`); a second click TOGGLES the dialog shut.
- **What IS reliable:** the **default per-dimension CSV export** (`studio_advanced_pull.py` / `studio_export_breakdowns.py`) — YT-aligned, carries the metrics YT computes for that dimension; and the **5 per-video tabs** (`studio_pull.py`) for the full video-level metric set. For literally-every-metric-per-breakdown aligned you'd need to **Save a custom report** (the bookmark) per column-set then export it, or batched exports merged by the dimension key — high effort, low marginal value (the extra columns are mostly empty per dimension).
- **YouTube curates which metrics each breakdown gets** — and helpfully includes **CTR by segment** where it's meaningful: `Traffic source` and `New and returning viewers` exports carry `Impressions` + `Impressions CTR` per row (e.g. Returning 6.21% vs New 2.05% CTR); `Subscription status` / `Device` / `Geography` carry Views/Watch/AVD only. So segment-level CTR ("types of CTR") lives in the traffic-source and new/returning breakdowns.
- **CHANNEL explore is the reliable, deep-linkable path** (unlike per-video): it deep-links with `time_period` (`last_7_days`/`last_28_days`/`last_90_days`/`last_365_days`/`lifetime`) + `dimension`. With `dimension=VIDEO` it returns every video as a row. ⚠ It **blanks if deep-linked cold** — first `goto` the channel analytics overview to warm the SPA, then deep-link. ⚠⚠ **CORRECTION (2026-06-20): the channel-VIDEO CSV EXPORT only emits the ~11 DEFAULT columns regardless of URL `t_metrics`** (t_metrics affects the on-screen chart, not the export column set). For all-metrics-per-video you MUST use the ⊕ checkbox method on the "Content" breakdown (see `studio_catalog_allmetrics.py` above), NOT URL params. Also the lifetime date verifier mis-reads (`now='Date'`) — for lifetime, skip the in-app date dance and export straight from the `time_period=lifetime` deep-link. Reference: `studio_channel_pull.py`, `studio_catalog_lifetime.py`.
- **Audience retention curve — SOLVED (2026-06-19).** The `AUDIENCE_RETENTION` explore renders the curve as an **SVG `path.line-series`** (the teal "This video" line). Extract the point-by-point series WITHOUT the internal XHR: sample the path with `getPointAtLength()` + `matrixTransform(getScreenCTM())`, and **calibrate screen→data using the axis tick labels** (x: `0:00…1:19:59`, y: `0%…90%`). Yields (second, retention%) points → find the intro cliff, mid dips, and rewatch spikes (points where retention RISES). Reference: `masoom_minawala/tools/studio_retention_curve.py`. (The Engagement-tab summary — AVD, avg % viewed, "X% still watching at Y", key-moment labels — is the quick read; the SVG extraction is the full curve.)
  - **PREFERRED (2026-07-03): pull the curve from the YouTube Analytics API, not the SVG.** `youtubeAnalytics.reports().query(metrics="audienceWatchRatio", dimensions="elapsedVideoTimeRatio", filters="video==VID")` returns 100 (ratio, watchRatio) points — no rendering, fast, parallel across channels, and immune to the unattended-render trap below. Convert ratio→seconds via the video duration. Reference: `masoom_minawala/tools/api_pull.py --curve`. Resolution caveat: 100 buckets across the whole video, so ~duration/100 per point (coarse early-seconds on long videos — the SVG's 200-pt sampling is similar). The API needs OAuth (`yt-analytics.readonly`); the SVG method below stays the FALLBACK when no token / API-absent metric.
  - **TRAP — unattended runs (early-morning cron, machine just woke): the chart SVG may never render** even though text/CSV pulls on the same page succeed. Hit on 2026-06-25 + 07-02 6:12am fires; NOT reproducible attended (even with the window minimized), so the exact trigger is unpinned. Mitigations that ship together: launch the automation Chrome with `--disable-backgrounding-occluded-windows --disable-renderer-backgrounding --disable-background-timer-throttling`; in-script force `Browser.setWindowBounds→normal` + `Page.bringToFront` + `Emulation.setFocusEmulationEnabled` + `Page.setWebLifecycleState:active`; on final failure write `.FAILED.json` (visibilityState, svg-path count) + `.FAILED.png` screenshot forensics; and keep a backfill retry later in the run (`cron/backfill_curves.py`). If you need curves reliably headless, prefer the YouTube Analytics API `audienceWatchRatio` — no rendering involved.

## Surfaces OUTSIDE the analytics CSV/explore (captured 2026-06-20)
The metrics-explore has 27 breakdown dimensions, but several Studio surfaces are NOT explore dimensions and never appear in a CSV. Capture map:
- **Per-video SEARCH TERMS, EXTERNAL SITES, and A/B (Test & compare) results all live in the per-video REACH tab TEXT** — and `studio_pull.py` already captures them when it dumps the 5 tabs. No separate scraper needed: parse the Reach tab string for "YouTube search terms" (term/% pairs, top-5 then "See more"), "External sites or apps" (referrer/% pairs), and "A/B test … Variant N is now visible … Ran from …". Per-video tabs blank on cold deep-link → `studio_pull.py` loads Overview then clicks each sub-tab in-app (the reliable render path). Reference: `pervideo_tabs_batch.sh`.
- **Channel AUDIENCE tab** (`tab-build_audience`, reached by clicking the "Audience" tab after warming `tab-overview` — the slug doesn't deep-link): cards "Channels your audience watches" (overlap → guest/collab targets, name + subs), "What your audience watches" (other videos), "When your viewers are on YouTube" (heatmap — canvas/div, no numeric DOM → **screenshot it**), "Formats your viewers watch", "Videos growing your audience", "Popular with different audiences". List cards paginate ("Next page" — flaky; page 1 = top signal). Reference: `studio_audience_tab.py`.
- **Research/Trends tab** (`tab-research`, the "Trends" tab label): content is in **shadow DOM** (a flat `innerText` dump returns nothing — use a recursive shadowRoot walker). "What people are looking for" = channel search-demand terms; "New videos to inspire you" = related/competitor videos. Sparse (a few terms) — screenshot + shadow-walk both.
- **Comments** are NOT in Studio analytics at all — fetch via **yt-dlp** (`--write-comments --extractor-args youtube:max_comments=…`), no Studio needed. Reference: `fetch_comments.py`.


## Multi-channel / delegated-manager channels (fleet) — the context trap
When one Google account manages MANY channels (agency case), Studio's **active channel is server-side session state, NOT in the URL** (no `authuser`/`pageId`). Consequences, verified 2026-07-03 (Roshan Kotla, a delegated-manager NON-brand channel):
- Navigating to `studio.youtube.com/` (home) **resets context to the account's default/owner channel.** Any subsequent `/channel/{OTHER_CID}/...` then loads under the wrong context → **"Oops, you don't have permission to view this page"** → blank/empty exports.
- **You cannot deep-link a delegated channel's explore from the wrong context.** There is no direct switch URL — the switcher entry is a JS `role=option` (`ytd-account-item-renderer`) that POSTs a context change server-side.
- **Reliable pattern:** do switch + ALL pulling in ONE continuous session, never returning to home mid-pull: home → avatar → "Switch account" → scroll the switcher list → click the target entry (lands on its dashboard = context set) → then navigate its explore URLs / click Advanced-mode in the same flow.
- **Owned/brand channels are exempt** — they deep-link regardless of context (that's why the Masoom-tested URL-driven recipe above "just works" for them but not for delegated channels).
- **Delegated channels: prefer the in-app "Advanced mode" BUTTON over a hand-built explore URL** — a constructed URL returned 0 rows even with correct context, while the button renders the real table (its Studio-default URL leads `t_metrics` with `EXTERNAL_VIEWS`).

## Delegated-manager FULL pull — the working recipe (SOLVED 2026-07-07, JBP `UCOuTW2qEI2c6R6DGh3oMnow`)
End-to-end recipe that reliably exports a delegated (You're-a-manager) channel's lifetime catalog CSV. Every step below is load-bearing; skipping one reproduces a specific earlier failure. **Do the WHOLE flow in ONE `browser-harness` invocation** — tab/overlay state does not survive across invocations (a fresh invocation lands on `about:blank`; the Advanced-mode overlay is gone).
1. **Set context via STUDIO's own avatar switcher, NOT youtube.com's.** The youtube.com avatar switcher changes the *viewing* identity but does NOT grant Studio delegated context (Studio still 403s). Reliable: `goto studio.youtube.com` (owner default) → click the top-right Studio avatar (~`(1451,32)` at 1492-wide) → click **"Switch account"** → the flyout is a SCROLLABLE list of `tp-yt-paper-item-body` rows; `scrollIntoView` the target (match `@handle`) then click it → lands on the target's dashboard = context set. Context then PERSISTS across invocations **as long as you never `goto studio.youtube.com/` (home) again** (home resets to the owner default).
2. **Set the period to Lifetime on the OVERVIEW first.** Open the top-right date dropdown (`yta-time-picker`) → click **"Lifetime"**. Advanced mode inherits the overview period, so you never fight the explore's own date control.
3. **Enter Advanced mode by triggering the SPA anchor — `document.querySelector('a[href*="explore"]').click()` — NOT a coordinate click and NOT a full `goto`.** A coordinate click on the "Advanced mode" button is intercepted by an overlay `DIV` (`elementFromPoint` returns a bare DIV, so the click never reaches the anchor). A full-page `goto` of the explore URL hydrates the TABLE (rows appear) but does **NOT** mount the export toolbar (`ytcp-icon-button[aria-label="Export current view"]` exists but has a 0×0 rect). Only the in-app SPA anchor click mounts the overlay + a working Export button. Poll up to ~15s for `aria-label="Export current view"` to have a nonzero rect.
4. **Export:** `click_deep('ytcp-icon-button[aria-label="Export current view"]')` → click the `tp-yt-paper-item` whose text contains `.csv`/`comma-separated` → `wait_for_download` → ZIP (`Table data.csv`, `Chart data.csv`, `Totals.csv`).
5. **NEVER press Escape inside Advanced mode** — it exits the explore back to the overview.
- **Column coverage:** the channel "Content" export emits only the ~10 DEFAULT columns (Views, Watch time, Subscribers-gained, Est. revenue, **Impressions, Impressions CTR**) — enough for the discovery/packaging/revenue funnel. Retention (avg % viewed), AVD, likes/comments/shares need the ⊕ all-metrics method (`studio_catalog_allmetrics.py`).
- **DON'T fight the ⊕ picker just for retention/AVD — DERIVE them.** The ⊕ column-picker on a delegated channel is the single most fragile surface (overlay-intercepted clicks, panel state that doesn't survive an invocation, the overlap-prone Interactions group). But `AVD_sec = watch_time_hours × 3600 / views` and `retention% = AVD_sec / duration_sec × 100` reproduce YouTube's own "Average view duration" / "Average percentage viewed" **exactly** (validated to the decimal against a Studio snapshot, 2026-07-07). So the default 10-col export + the video duration already give you retention/AVD for free. Only genuinely Studio-exclusive fields (subscribers-lost, shares) actually require the ⊕ pull. Reference: `justbecausepod/tools/derive_retention.py`.
- Reference implementation: `client_analytics/justbecausepod/tools/studio_browser_pull.py` (one-shot switch→lifetime→SPA-advanced-mode→export→unzip).
