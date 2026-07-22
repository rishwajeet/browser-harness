# LinkedIn — reading your own post analytics (impressions)

Goal: pull per-post **impressions** (and engagement) for posts you authored. The public Apify scrape returns likes/comments/shares but **never impressions** — only the author can see those, logged in.

## Where impressions live

As the author, the post page itself renders an inline `"<n> impressions"` element near the social bar (e.g. `1,690 impressions`) plus a `Post impressions` label. No click needed.

- **Post page**: `https://www.linkedin.com/feed/update/urn:li:activity:{ACTIVITY_ID}/`
- **Dedicated analytics page** (more detail — members reached, demographics): `https://www.linkedin.com/analytics/post-summary/urn:li:activity:{ACTIVITY_ID}/`
- The post page exposes both as anchors: `a[href*="analytics"]` → the `post-summary` URL and the global `analytics/creator/content/`.

`{ACTIVITY_ID}` is the 19-digit number in the post URL (`...-activity-7467870264358379520-xxxx`).

## Extraction (reliable, no pixel-clicking)

Navigate to the feed-update URL, wait, then read the leaf node that matches `^[\d,]+ impressions?$`:

```python
import time, json
posts = {"7467870264358379520":"almost-quit", "7468594973203034112":"packaging"}
out = {}
for pid, name in posts.items():
    goto(f"https://www.linkedin.com/feed/update/urn:li:activity:{pid}/")
    wait_for_load(); time.sleep(3)
    imp = js(r"""(function(){
      for (const el of document.querySelectorAll('*')){
        if (el.children.length===0){
          const m=(el.innerText||'').trim().match(/^([\d,]+)\s+impressions?$/i);
          if(m) return m[1];
        }
      } return null;})()""")
    out[name] = imp
    print(name, pid, imp)
```

Strip the comma before storing (`1,690` → `1690`).

## Connection note (Chrome 149, macOS) — the part that actually costs time

The user's **default** Chrome profile on Chrome 136+ will NOT bind `--remote-debugging-port` (and the sticky `chrome://inspect` checkbox triggers an un-clickable consent modal). Use the **dedicated automation profile** instead (see `interaction-skills/connection.md` §"automation profile"). It's already seeded + logged into LinkedIn here:

```bash
DST="$HOME/Library/Application Support/Google/Chrome-Automation"
rm -f "$DST/SingletonLock"
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --user-data-dir="$DST" --remote-debugging-port=9222 --remote-allow-origins='*' \
  --no-first-run --no-default-browser-check >/dev/null 2>&1 &
WS=$(curl -s http://127.0.0.1:9222/json/version | python3 -c "import sys,json;print(json.load(sys.stdin)['webSocketDebuggerUrl'])")
BU_CDP_WS="$WS" browser-harness <<'PY'
...
PY
```

Trap: the **first** `browser-harness` call after launching the daemon can fail once with `daemon ... didn't come up` (startup race) even though the daemon then comes up fine — just re-run the same call. If a stale socket lingers, `rm -f /tmp/bu-default.sock /tmp/bu-default.pid` and retry.

If the automation profile is logged out (cookies expired), re-seed Default→Chrome-Automation per connection.md while the normal Chrome is fully quit.
