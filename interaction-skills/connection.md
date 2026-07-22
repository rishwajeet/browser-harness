# Connection & Tab Visibility

## The omnibox popup problem

When Chrome opens fresh, the only CDP `type: "page"` targets are `chrome://inspect` and `chrome://omnibox-popup.top-chrome/` (a 1px invisible viewport). If the daemon attaches to the omnibox popup, all subsequent work — including `new_tab()` and `goto()` — happens on tabs that exist in CDP but may not be visible in the Chrome UI.

The daemon's `attach_first_page()` handles this by creating an `about:blank` tab when no real pages exist. If you still end up on an invisible tab, use `switch_tab()` which calls `Target.activateTarget` to bring the tab to front.

## Startup sequence

1. Check if a daemon is already running with `daemon_alive()`
2. If stale sockets exist but daemon is dead, clean them up
3. List open tabs with `list_tabs()` to see what's available
4. `ensure_real_tab()` attaches to a real page
5. `switch_tab(target_id)` both attaches AND activates (brings to front)

```python
if not daemon_alive():
    import os
    for f in ["/tmp/bu-default.sock", "/tmp/bu-default.pid"]:
        if os.path.exists(f): os.unlink(f)
    ensure_daemon()

tabs = list_tabs()
for t in tabs:
    print(t["url"][:60])

tab = ensure_real_tab()
```

## Bringing Chrome to front

If Chrome is behind other windows or on another desktop:

```python
import subprocess
subprocess.run(["osascript", "-e", 'tell application "Google Chrome" to activate'])
```

## Navigating

Prefer navigating an existing tab over `new_tab()`. Tabs created via CDP's `Target.createTarget` are visible but may open behind the active tab.

```python
tab = ensure_real_tab()
goto("https://example.com")
```

## ✅ Auto self-heal (hardened 2026-06-28) — usually you do NOTHING

`ensure_daemon()` now self-heals the wedged-default-Chrome cases automatically. If the
daemon can't come up because the user's normal Chrome is unreachable for CDP — the
un-clickable "Allow remote debugging?" modal, a stale/missing `DevToolsActivePort`, or a
stale ws path (HTTP 404 on connect) — and no `BU_CDP_WS` is already set, it runs
`automation_session.sh` itself, points the daemon at the dedicated profile via `BU_CDP_WS`,
and retries once. So a plain `browser-harness <<'PY' ... PY` call recovers on its own; you
no longer need to remember the manual `eval "$(automation_session.sh)"`.

The matcher is `admin._wedge_signature()`; the fallback is `admin._automation_fallback()`.
The fallback fails gracefully (returns None → original error re-raised) when the dedicated
profile genuinely can't help (e.g. Chrome not installed). The manual `eval` still works and
is the right tool when you want a clean (`--no-auth`) or re-seeded (`--refresh-auth`) profile.
The manual steps below remain as the explanation / escape hatch.

## "DevTools is not live yet" — the restart fix (field-tested Jun 2026)

If `ensure_daemon()` fails with **"Chrome's remote-debugging page is open, but DevTools is not live yet on 127.0.0.1:9222"** AND `~/Library/Application Support/Google/Chrome/DevToolsActivePort` exists with the right port but `lsof -nP -iTCP:9222 -sTCP:LISTEN` shows nothing — the port file is **stale from a previous run**. The remote-debugging checkbox is sticky per profile but only takes effect on a fresh Chrome launch. The currently running Chrome was started before the setting (or before a sticky state could apply).

**Fix — no user interaction needed, do it yourself:**

```bash
osascript -e 'tell application "Google Chrome" to quit'   # graceful: session restores tabs
# wait for process to actually exit (up to ~8s)
while pgrep -x "Google Chrome" >/dev/null; do sleep 1; done
open -a "Google Chrome"
sleep 6
lsof -nP -iTCP:9222 -sTCP:LISTEN   # should now show Chrome LISTENing
```

Then the FIRST harness connect after restart may fail once with **"CDP WS handshake failed: timed out during opening handshake"** — that's Chrome's Allow dialog (or just slow startup). Retry every ~5s for up to 30s; it connects. Only if 9222 is still dead after a clean relaunch does the user actually need to tick the checkbox at `chrome://inspect/#remote-debugging` (then restart Chrome again).

Don't ask the user to click anything until you've tried the restart — the checkbox being sticky means most "not live" states are fixed by relaunch alone.

## The "Allow remote debugging?" dialog — click it yourself (field-tested Jun 2026)

If the WS handshake keeps timing out after a clean relaunch, Chrome is showing a native **"Allow remote debugging?"** sheet on the front window. You can click it via System Events without the user:

```applescript
tell application "System Events"
  tell process "Google Chrome"
    set sh to sheet 1 of window 1  -- the sheet may hang off any window; enumerate windows if needed
    repeat with el in (entire contents of sh)
      try
        if (role of el as string) is "AXButton" and (description of el as string) is "Allow" then
          click el
          exit repeat
        end if
      end try
    end repeat
  end tell
end tell
```

Notes: the buttons (`Turn off in settings`, `Cancel`, `Allow`) carry their labels in `description`, NOT `name`/`title` — `button "Allow" of window 1` does NOT find them; you must walk `entire contents` of the sheet. After clicking, wait ~8s before reconnecting (first attempt may still time out once).

## ⚠ UPDATE (field-tested 2026-06-19, Chrome 149): the Allow dialog is now UN-clickable by automation — use a dedicated profile instead

On Chrome 136+ (confirmed on 149) the "Allow remote debugging?" sheet became a **WebUI** dialog that **rejects ALL synthetic input by design** — the AppleScript snippet above no longer works. Every method lands dead-center on the Allow button (verified with `screencapture -C` showing the cursor on it) and is ignored:
- AppleScript `perform action "AXPress"` → returns success, dialog stays.
- `cliclick c:` / `dc:` / focus-click → no effect.
- System Events `click at {x,y}` → resolves to `button 3` but no effect.

The AX tree for the sheet is also flaky (buttons flicker in/out of `entire contents`; the matched button often has no `AXPosition`, so position-based clicks silently fail). **Do not burn time clicking it.** Also: Chrome 136+ **refuses `--remote-debugging-port` on the DEFAULT user-data-dir** (port never binds), and the *only* way the default profile exposes the port is the sticky chrome://inspect checkbox — which is exactly the path that triggers the un-clickable modal.

### The autonomous fix: a dedicated automation profile (no modal, ever)

A custom `--user-data-dir` + `--remote-debugging-port` **binds the port AND never shows the consent modal** (this is why Puppeteer/Selenium never hit it). Seed that dir with a copy of the real logged-in profile (same macOS user → same Chrome Safe Storage Keychain key → cookies/logins decrypt), so it boots already signed in. A custom-dir Chrome also serves `/json/version`, so resolve the WS endpoint there and pass it via `BU_CDP_WS`.

```bash
SRC="$HOME/Library/Application Support/Google/Chrome"
DST="$HOME/Library/Application Support/Google/Chrome-Automation"
# one-time (or when logins expire): seed auth — quit the normal Chrome first for a clean copy
cp -f "$SRC/Local State" "$DST/Local State"
rsync -a --delete --exclude 'Cache' --exclude 'Code Cache' --exclude 'GPUCache' \
  --exclude 'Service Worker/CacheStorage' --exclude '*.log' "$SRC/Default/" "$DST/Default/"
rm -f "$DST/SingletonLock"
# launch (separate instance; coexists with the user's normal default-profile Chrome)
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --user-data-dir="$DST" --remote-debugging-port=9222 --remote-allow-origins='*' \
  --no-first-run --no-default-browser-check >/dev/null 2>&1 &
# point the daemon at the right endpoint:
WS=$(curl -s http://127.0.0.1:9222/json/version | python3 -c "import sys,json;print(json.load(sys.stdin)['webSocketDebuggerUrl'])")
BU_CDP_WS="$WS" browser-harness < your_script.py
```

**Universal one-liner (use this first — it does everything above):** `browser-harness/automation_session.sh` is the site-agnostic, idempotent version. It reuses the shared `Chrome-Automation` profile, auto-bumps to a free port if a foreign Chrome holds the default, and prints `export BU_CDP_WS=...`:

```bash
eval "$(browser-harness/automation_session.sh)"   # boot + export BU_CDP_WS (reuses/seeds profile)
browser-harness <<'PY' ... PY                      # BU_CDP_WS now in env
# flags: --no-auth (clean profile, public sites) · --refresh-auth (re-seed logins) · --quit · --status
```
Re-run `eval "$(...automation_session.sh)"` in every shell that calls `browser-harness` (BU_CDP_WS must be in that process's env). It seeds auth from the real profile on first boot only (skip with `--no-auth` for sites needing no login). Field-proven on the Toshakhana MEA auction (2026-06-26) — connected with zero dialog after the default-profile path was wedged.

Reference / origin (YouTube-Studio-specific, auth + brand-account selection persisted): `client_analytics/masoom_minawala/tools/studio_session.sh`.
