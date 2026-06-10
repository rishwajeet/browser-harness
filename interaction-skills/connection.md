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
