# Headless driven capture — clean screenshot files when the user's Chrome is unusable

Use this when EITHER is true:
- The user's Chrome CDP is wedged — repeated `no close frame received or sent` or `CDP WS handshake failed: timed out` that survives `restart_daemon()` and even a Chrome relaunch. (Field-tested: a session can leave the default daemon path unrecoverable while a *fresh* headless Chrome connects fine.)
- You need screenshot **files to send the user**. `claude-in-chrome`'s `save_to_disk` does NOT write a local file you can `SendUserFile` (it's sandboxed), and `browser-harness`'s `screenshot()` helper over `BU_CDP_WS` can return a **stale frame**. Raw `Page.captureScreenshot` is the reliable path.

## The pattern: drive a fresh headless Chrome via BU_CDP_WS

```bash
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
"$CHROME" --headless=new --disable-gpu --remote-debugging-port=9333 \
  --user-data-dir=/tmp/cap-profile about:blank >/tmp/hl.log 2>&1 &
# Chrome 149 DOES serve /json/version on an explicit --remote-debugging-port (the
# "no /json/version" gotcha is only chrome://inspect). Poll it for the WS url:
WS=$(curl -s http://127.0.0.1:9333/json/version | python3 -c "import sys,json;print(json.load(sys.stdin)['webSocketDebuggerUrl'])")
```

```bash
BU_CDP_WS="$WS" BU_NAME=cap browser-harness <<'PY'
import base64, time
new_tab("http://localhost:3000/whatever"); wait_for_load()
# emulate a real device so layout is correct (see pitfalls); persists across goto()
cdp("Emulation.setDeviceMetricsOverride", width=390, height=844, deviceScaleFactor=3, mobile=True)
goto("http://localhost:3000/whatever"); wait_for_load(); time.sleep(2)
r = cdp("Page.captureScreenshot", format="png", captureBeyondViewport=True)   # fresh, full-page
open("/tmp/shot.png","wb").write(base64.b64decode(r["data"]))
PY
```

Isolated (own profile + port), so it never touches the user's Chrome. Kill it after: `kill $(lsof -ti tcp:9333)`.

## Capture pitfalls that cost real time

- **Right-edge clipping.** `--screenshot` (or a too-narrow window) at a width below the page's `max-w-md`/container width clips the right side (scores, tabs — silently). Don't eyeball it. Use device emulation at a real mobile width (390) so a mobile-first layout renders full-width and nothing clips.
- **`position:fixed` bars float mid-image** in full-page captures (a bottom nav lands over the middle of a long list). Before capturing, inject `nav{position:static!important}` and zero any reserved padding so it flows to the bottom.
- **Next.js dev badge** shows up as a stray circle: hide `nextjs-portal{display:none!important}`.
- **Do NOT "settle" entrance animations with `*{opacity:1!important;transform:none!important}`** — it flattens every intended tilt/stamp/shadow and looks broken. Pop/scale animations (e.g. `animation: popIn 280ms both`) finish on their own; just `time.sleep(0.4)` and take a fresh raw-CDP shot.
- **Driving React:** controlled inputs need the native setter + a dispatched event, then a click:
  `var set=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set; set.call(inp,'1m'); inp.dispatchEvent(new Event('input',{bubbles:true}));`
  For click-driven games, click buttons by visible text / `aria-label`, and detect end-state by text (`/run it back/i`) rather than fixed waits.
- **To force a specific game outcome** (e.g. a non-zero streak for a clean demo), read the data from the DOM — YouTube thumbnail `src` carries the id (`.../vi/<ID>/...`), look it up in the local data file, and pick deterministically.

## The meta-rule

**`Read` every capture before you send it.** Shipping unexamined screenshots is how clipped/animation-broken/wrong-data shots reach the user. A wrong-looking screenshot is also a signal to check for a real bug — a board that rendered the wrong dataset turned out to be a genuine fetch race, not just a bad shot.
