# ViewStats — Outliers & Thumbnail search

Extracting YouTube outlier intelligence from ViewStats Pro (`viewstats.com/pro/*`) via DOM scraping. Requires a logged-in Pro account with cookies already set in the user's Chrome.

## URL patterns

| Tool | URL |
|---|---|
| Outliers (keyword) | `/pro/outliers?isRecent=true&isShort=false&q=<query>` |
| Thumbnails (keyword) | `/pro/thumbnails?q=<query>` |
| A/B Tests | `/pro/ab-tests` (filter via Filter & Sort) |
| Competitors | `/pro/competitors` |
| Collections | `/pro/collections` |

Params: `isRecent=true` sorts Outliers by upload recency; `isShort=false` excludes Shorts. `pageNumber=N` for pagination. Always pass both sort + short flags on direct nav — otherwise results load stale.

## Traps

1. **"My Channel" AI-anchor carryover.** If the account's My Channel is set (e.g. `@roshankotla`), every Outliers search silently appends `aiChannelSearch=<handle>` and biases results semantically toward that channel's niche. After navigation, clear with:
   ```js
   document.querySelectorAll('.wrapper_sub_text__k8y_4 button, [class*=wrapper_sub_text] button').forEach(b => b.click())
   ```
   Then `wait(3-5)` — results re-fetch after clear. Detect via page text: if "Outlier Results for '...' @handle" appears, the anchor is active.

2. **"New Feature Alert" modal re-opens on every nav.** Kill in JS after each `goto()`:
   ```js
   document.querySelectorAll('[role=dialog],[class*=modal]').forEach(m=>m.remove())
   document.body.style.overflow='auto'
   ```
   Setting `localStorage.creatorDashboardPopupSeen='1'` and `localStorage.newFeatureAlert_seen='1'` did **not** prevent re-opening in our test — the modal uses server-side state.

3. **Search input doesn't submit via Enter alone reliably.** When triggering via JS-typed text, use `press_key("Enter")` after `type_text(q)` and wait 3+ seconds. More reliable: navigate directly to the URL with `q=` param set.

4. **Initial results may load before @chip clear triggers.** After clearing the AI anchor, wait 3-5s for refetch, then scroll. Results from the pre-clear state return 0 cards after chip clear.

5. **Some queries genuinely return 0.** "Minimum payment trap" returns zero hits even with perfect setup — the exact token has no breakout content indexed. Swap to "minimum payment" or split the keyword.

## Private API

Endpoint found: `https://api.viewstats.com/outliers/search/qdrant?category=0&isRecent=true&isShort=false&q=<query>&pageNumber=<n>`

- `qdrant` in the path = Qdrant vector DB (semantic search, not keyword-exact)
- Requires `Authorization: Bearer <token>` from `VS_AUTH` cookie
- Response is `application/octet-stream` — NOT gzip / brotli / msgpack / JSON. A proprietary binary format we didn't crack. Starts with `27 01` magic bytes.

**Conclusion: API is not directly usable without reverse-engineering the binary codec.** DOM scraping via browser-harness is the pragmatic path. ~20-30 cards per query, scroll 4-6 times for full page load (~40 cards max visible before pagination).

Getting the bearer token (if you want to try) — it's in the cookie:
```js
document.cookie.match(/VS_AUTH=([^;]+)/)[1]
```

## Stable selectors

| Target | Selector |
|---|---|
| Outlier card | `.outlier-video-wrapper` |
| Outlier card inner link | `a.video_section__fRI4G` |
| Views/date meta | `.video_meta__dqKB7` |
| Search input | `input[placeholder*="Search" i]` (Outliers), `input[placeholder*="Describe" i]` (Thumbnails) |
| Sort button (Thumbnails) | find `button` with `innerText` matching `Similarity\|Outlier Score\|Sort` |
| @channel-anchor clear X | `.wrapper_sub_text__k8y_4 button` |
| Modal container | `[role="dialog"], [class*="modal"]` |

Prefer `.outlier-video-wrapper` over any class-hash-suffixed selectors — the semantic class is stable, the module-hashed twin (`video_video__nLEbG`) changes on deploys.

## Parse pattern — Outliers card `innerText`

```
MM:SS
<outlier>x

<title>

<channel_handle>

<subs> subs
<views> views • <date>
```

Lines after split-on-`\n` and filter-empty:
- `[0]` duration (or may be missing → shift by one)
- `[1]` outlier score with trailing `x`
- `[2]` title
- `[3]` channel handle
- `[4]` subs string
- `[5]` views • date string

Robust regex: outlier = `r"([\d.]+)x"`, views = `r"([\d.]+)\s*([KMkm]?)\s*views"`, subs = same.

## Parse pattern — Thumbnail card

Same skeleton, slightly different order on some variants. Extract via regex rather than index.

## Thumbnail image URLs

Images come from `i.ytimg.com/vi/<video_id>/maxresdefault.jpg` or `hqdefault.jpg`. `maxresdefault` often 404s for shorter videos — retry with `hqdefault` as fallback. Standard yt thumbnail URL structure so extraction-by-video-id is trivial.

## Batch search recipe

```python
import json, urllib.parse

def search_and_extract(q):
    url = f"https://www.viewstats.com/pro/outliers?isRecent=true&isShort=false&q={urllib.parse.quote(q)}"
    goto(url); wait_for_load(); wait(4)
    js("document.querySelectorAll('[role=dialog],[class*=modal]').forEach(m=>m.remove()); document.body.style.overflow='auto';")
    wait(1)
    # Clear AI channel anchor
    js("document.querySelectorAll('.wrapper_sub_text__k8y_4 button, [class*=wrapper_sub_text] button').forEach(b=>b.click())")
    wait(4)  # Wait for refetch after clear
    # Load more via scroll
    for _ in range(6):
        js("window.scrollBy(0, 1500)"); wait(0.7)
    wait(1)
    raw = js("JSON.stringify(Array.from(document.querySelectorAll('.outlier-video-wrapper'), c => c.innerText||''))")
    return json.loads(raw or "[]")
```

~6 scrolls yields 40 cards (the cap per page). For more: pagination via `&pageNumber=2`.

## Sort dropdown (Thumbnails)

Click the "Similarity" button (top-right), then the menu item with exact innerText `Outlier Score`. Selectors:
```js
// Open
Array.from(document.querySelectorAll('button')).find(b => /Similarity|Outlier Score/.test(b.innerText)).click()
// Pick
document.querySelectorAll('[role=menuitem], [role=option], li, button').forEach(i => { if (i.innerText.trim()==='Outlier Score') i.click() })
```

## Filtering tips (post-scrape)

ViewStats uses semantic (vector) search, so results bleed across topics. Apply your own keyword filter after scraping:

- **Positive match:** require any of ~50 domain keywords (debt, credit, loan, APR, bank, collections, etc.)
- **Negative match:** exclude topical contamination (crypto, real estate investing, dental, India-specific, etc.)
- **Ceiling test:** views ≥ 50K, channel subs ≥ 10K, outlier ≥ 3x. Rules out vanity outliers (200x on a dead channel with 25K views) and reinforces absolute-reach signal.
- **Dedupe on** `(title.lower(), channel.lower())` — semantic search often returns same video on multiple queries.

## Playbook reference

For the end-to-end workflow (weekly ideation, pre-record, title brainstorm, thumbnail brainstorm, monthly review), see `client_analytics/_tools/VIEWSTATS_PLAYBOOK.md` in the machine_house repo.

## Test run — 2026-04-20

Ran 25 keyword searches across a client's 4 content pillars for personal-finance channel ideation. Captured 580 outliers, filtered to 106 finance-relevant, derived launch slate with specific outlier citations. Total time ≈25 min. Output in `client_analytics/samder_khangarot/analysis/VIEWSTATS_IDEATION.md`. Zero-result queries: "minimum payment trap" (semantic), "why americans broke" (semantic). Swap to broader tokens and retry.
