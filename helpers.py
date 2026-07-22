"""Browser control via CDP. Read, edit, extend -- this file is yours."""
import base64, json, os, socket, time, urllib.request
from pathlib import Path
from urllib.parse import urlparse


def _load_env():
    p = Path(__file__).parent / ".env"
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_env()

NAME = os.environ.get("BU_NAME", "default")
SOCK = f"/tmp/bu-{NAME}.sock"
INTERNAL = ("chrome://", "chrome-untrusted://", "devtools://", "chrome-extension://", "about:")


def _send(req):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(SOCK)
    s.sendall((json.dumps(req) + "\n").encode())
    data = b""
    while not data.endswith(b"\n"):
        chunk = s.recv(1 << 20)
        if not chunk: break
        data += chunk
    s.close()
    r = json.loads(data)
    if "error" in r: raise RuntimeError(r["error"])
    return r


def cdp(method, session_id=None, **params):
    """Raw CDP. cdp('Page.navigate', url='...'), cdp('DOM.getDocument', depth=-1)."""
    return _send({"method": method, "params": params, "session_id": session_id}).get("result", {})


def drain_events():  return _send({"meta": "drain_events"})["events"]


# --- navigation / page ---
def goto(url):
    r = cdp("Page.navigate", url=url)
    d = (Path(__file__).parent / "domain-skills" / (urlparse(url).hostname or "").removeprefix("www.").split(".")[0])
    return {**r, "domain_skills": sorted(p.name for p in d.rglob("*.md"))[:10]} if d.is_dir() else r

def page_info():
    """{url, title, w, h, sx, sy, pw, ph} — viewport + scroll + page size.

    If a native dialog (alert/confirm/prompt/beforeunload) is open, returns
    {dialog: {type, message, ...}} instead — the page's JS thread is frozen
    until the dialog is handled (see interaction-skills/dialogs.md)."""
    dialog = _send({"meta": "pending_dialog"}).get("dialog")
    if dialog:
        return {"dialog": dialog}
    r = cdp("Runtime.evaluate",
            expression="JSON.stringify({url:location.href,title:document.title,w:innerWidth,h:innerHeight,sx:scrollX,sy:scrollY,pw:document.documentElement.scrollWidth,ph:document.documentElement.scrollHeight})",
            returnByValue=True)
    return json.loads(r["result"]["value"])

# --- input ---
def click(x, y, button="left", clicks=1):
    cdp("Input.dispatchMouseEvent", type="mousePressed", x=x, y=y, button=button, clickCount=clicks)
    cdp("Input.dispatchMouseEvent", type="mouseReleased", x=x, y=y, button=button, clickCount=clicks)

def type_text(text):
    cdp("Input.insertText", text=text)

_KEYS = {  # key → (windowsVirtualKeyCode, code, text)
    "Enter": (13, "Enter", "\r"), "Tab": (9, "Tab", "\t"), "Backspace": (8, "Backspace", ""),
    "Escape": (27, "Escape", ""), "Delete": (46, "Delete", ""), " ": (32, "Space", " "),
    "ArrowLeft": (37, "ArrowLeft", ""), "ArrowUp": (38, "ArrowUp", ""),
    "ArrowRight": (39, "ArrowRight", ""), "ArrowDown": (40, "ArrowDown", ""),
    "Home": (36, "Home", ""), "End": (35, "End", ""),
    "PageUp": (33, "PageUp", ""), "PageDown": (34, "PageDown", ""),
}
def press_key(key, modifiers=0):
    """Modifiers bitfield: 1=Alt, 2=Ctrl, 4=Meta(Cmd), 8=Shift.
    Special keys (Enter, Tab, Arrow*, Backspace, etc.) carry their virtual key codes
    so listeners checking e.keyCode / e.key all fire."""
    vk, code, text = _KEYS.get(key, (ord(key[0]) if len(key) == 1 else 0, key, key if len(key) == 1 else ""))
    base = {"key": key, "code": code, "modifiers": modifiers, "windowsVirtualKeyCode": vk, "nativeVirtualKeyCode": vk}
    cdp("Input.dispatchKeyEvent", type="keyDown", **base, **({"text": text} if text else {}))
    if text and len(text) == 1:
        cdp("Input.dispatchKeyEvent", type="char", text=text, **{k: v for k, v in base.items() if k != "text"})
    cdp("Input.dispatchKeyEvent", type="keyUp", **base)

def scroll(x, y, dy=-300, dx=0):
    cdp("Input.dispatchMouseEvent", type="mouseWheel", x=x, y=y, deltaX=dx, deltaY=dy)


# --- visual ---
def screenshot(path="/tmp/shot.png", full=False):
    r = cdp("Page.captureScreenshot", format="png", captureBeyondViewport=full)
    open(path, "wb").write(base64.b64decode(r["data"]))
    return path


# --- tabs ---
def list_tabs(include_chrome=True):
    out = []
    for t in cdp("Target.getTargets")["targetInfos"]:
        if t["type"] != "page": continue
        url = t.get("url", "")
        if not include_chrome and url.startswith(INTERNAL): continue
        out.append({"targetId": t["targetId"], "title": t.get("title", ""), "url": url})
    return out

def current_tab():
    t = cdp("Target.getTargetInfo").get("targetInfo", {})
    return {"targetId": t.get("targetId"), "url": t.get("url", ""), "title": t.get("title", "")}

def _mark_tab():
    """Prepend 🟢 to tab title so the user can see which tab the agent controls."""
    try: cdp("Runtime.evaluate", expression="if(!document.title.startsWith('\U0001F7E2'))document.title='\U0001F7E2 '+document.title")
    except Exception: pass

def switch_tab(target_id):
    # Unmark old tab
    try: cdp("Runtime.evaluate", expression="if(document.title.startsWith('\U0001F7E2 '))document.title=document.title.slice(2)")
    except Exception: pass
    cdp("Target.activateTarget", targetId=target_id)
    sid = cdp("Target.attachToTarget", targetId=target_id, flatten=True)["sessionId"]
    _send({"meta": "set_session", "session_id": sid})
    # Enable event domains on the new session so console_messages() / network_requests() see activity.
    # The daemon only enables these on the first attached session; new tabs need it too.
    for d in ("Page", "DOM", "Runtime", "Network"):
        try: cdp(f"{d}.enable")
        except Exception: pass
    _mark_tab()
    return sid

def new_tab(url="about:blank"):
    # Always create blank, then goto: passing url to createTarget races with
    # attach, so the brief about:blank is "complete" by the time the caller
    # polls and wait_for_load() returns before navigation actually starts.
    tid = cdp("Target.createTarget", url="about:blank")["targetId"]
    switch_tab(tid)
    if url != "about:blank":
        goto(url)
    return tid

def ensure_real_tab():
    """Switch to a real user tab if current is chrome:// / internal / stale."""
    tabs = list_tabs(include_chrome=False)
    if not tabs:
        return None
    try:
        cur = current_tab()
        if cur["url"] and not cur["url"].startswith(INTERNAL):
            return cur
    except Exception:
        pass
    switch_tab(tabs[0]["targetId"])
    return tabs[0]

def iframe_target(url_substr):
    """First iframe target whose URL contains `url_substr`. Use with js(..., target_id=...)."""
    for t in cdp("Target.getTargets")["targetInfos"]:
        if t["type"] == "iframe" and url_substr in t.get("url", ""):
            return t["targetId"]
    return None


# --- utility ---
def wait(seconds=1.0):
    time.sleep(seconds)

def wait_for_load(timeout=15.0):
    """Poll document.readyState == 'complete' or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if js("document.readyState") == "complete": return True
        time.sleep(0.3)
    return False

def js(expression, target_id=None):
    """Run JS in the attached tab (default) or inside an iframe target (via iframe_target())."""
    sid = cdp("Target.attachToTarget", targetId=target_id, flatten=True)["sessionId"] if target_id else None
    r = cdp("Runtime.evaluate", session_id=sid, expression=expression, returnByValue=True, awaitPromise=True)
    return r.get("result", {}).get("value")


_KC = {"Enter": 13, "Tab": 9, "Escape": 27, "Backspace": 8, " ": 32, "ArrowLeft": 37, "ArrowUp": 38, "ArrowRight": 39, "ArrowDown": 40}


def dispatch_key(selector, key="Enter", event="keypress"):
    """Dispatch a DOM KeyboardEvent on the matched element.

    Use this when a site reacts to synthetic DOM key events on an element more reliably
    than to raw CDP input events.
    """
    kc = _KC.get(key, ord(key) if len(key) == 1 else 0)
    js(
        f"(()=>{{const e=document.querySelector({json.dumps(selector)});if(e){{e.focus();e.dispatchEvent(new KeyboardEvent({json.dumps(event)},{{key:{json.dumps(key)},code:{json.dumps(key)},keyCode:{kc},which:{kc},bubbles:true}}));}}}})()"
    )

def upload_file(selector, path):
    """Set files on a file input via CDP DOM.setFileInputFiles. `path` is an absolute filepath (use tempfile.mkstemp if needed)."""
    doc = cdp("DOM.getDocument", depth=-1)
    nid = cdp("DOM.querySelector", nodeId=doc["root"]["nodeId"], selector=selector)["nodeId"]
    if not nid: raise RuntimeError(f"no element for {selector}")
    cdp("DOM.setFileInputFiles", files=[path] if isinstance(path, str) else list(path), nodeId=nid)

def http_get(url, headers=None, timeout=20.0):
    """Pure HTTP — no browser. Use for static pages / APIs. Wrap in ThreadPoolExecutor for bulk."""
    import urllib.request, gzip
    h = {"User-Agent": "Mozilla/5.0", "Accept-Encoding": "gzip"}
    if headers: h.update(headers)
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout) as r:
        data = r.read()
        if r.headers.get("Content-Encoding") == "gzip": data = gzip.decompress(data)
        return data.decode()


# --- window / viewport ---
def resize_window(width, height):
    """Resize the actual browser window (CSS px). Persists across tabs on the same window."""
    w = cdp("Browser.getWindowForTarget")
    cdp("Browser.setWindowBounds", windowId=w["windowId"], bounds={"width": int(width), "height": int(height)})


# --- events (console + network) ---
# The daemon buffers all CDP events (max 500) and drain_events() clears the buffer.
# These helpers drain once and filter, so calling console_messages() + network_requests()
# in the same browser-harness invocation both see the same batch. Within the same Python
# process (same `browser-harness <<PY` block), subsequent calls only see NEW events.

_events_cache: list = []

def _refresh_events():
    _events_cache.extend(drain_events())
    return _events_cache

def console_messages(pattern=None, level=None, clear=False):
    """Console output captured since daemon started / last clear.

    pattern: regex filtered against the stringified message
    level: one of 'log','info','warn','error','debug' (the CDP 'type' field)
    clear: drop cached events after returning (fresh slate for next call)
    """
    import re
    _refresh_events()
    out = []
    for e in _events_cache:
        if e.get("method") != "Runtime.consoleAPICalled": continue
        p = e.get("params", {})
        if level and p.get("type") != level: continue
        args = p.get("args", [])
        text = " ".join(str(a.get("value", a.get("description", ""))) for a in args)
        if pattern and not re.search(pattern, text): continue
        out.append({"level": p.get("type"), "text": text, "timestamp": p.get("timestamp"),
                    "stack": p.get("stackTrace")})
    if clear: _events_cache.clear()
    return out

def network_requests(pattern=None, types=None, status=None, clear=False):
    """Network requests since daemon started. Pairs requestWillBeSent + responseReceived.

    pattern: regex filtered against URL
    types: iterable of resource types ('Document','Fetch','XHR','Image','Script',...)
    status: int or iterable of HTTP status codes
    clear: drop cached events after returning
    """
    import re
    _refresh_events()
    reqs: dict = {}
    for e in _events_cache:
        m = e.get("method", "")
        p = e.get("params", {})
        if m == "Network.requestWillBeSent":
            reqs[p["requestId"]] = {
                "url": p["request"]["url"],
                "method": p["request"]["method"],
                "type": p.get("type", "Other"),
                "initiator": p.get("initiator", {}).get("type"),
            }
        elif m == "Network.responseReceived" and p["requestId"] in reqs:
            resp = p["response"]
            reqs[p["requestId"]].update({"status": resp["status"], "mimeType": resp["mimeType"]})
        elif m == "Network.loadingFailed" and p["requestId"] in reqs:
            reqs[p["requestId"]]["failed"] = p.get("errorText")
    out = list(reqs.values())
    if pattern: out = [r for r in out if re.search(pattern, r["url"])]
    if types: out = [r for r in out if r.get("type") in set(types)]
    if status is not None:
        wanted = {status} if isinstance(status, int) else set(status)
        out = [r for r in out if r.get("status") in wanted]
    if clear: _events_cache.clear()
    return out


# --- SPA-safe waits ---
def wait_for_xhr(url_pattern, timeout=15.0, status=None, poll=0.2):
    """Wait until a network response whose URL matches url_pattern (regex) arrives.

    Returns the request record (dict with url/status/method/type/...) or None on timeout.
    Use before querying the DOM on SPA pages — readyState='complete' only covers the
    outer shell, the data XHR comes later. Enables Network domain on the current
    session if not already (daemon enables it on initial attach + switch_tab).
    """
    import re
    try: cdp("Network.enable")
    except Exception: pass
    deadline = time.time() + timeout
    while time.time() < deadline:
        for r in network_requests(pattern=url_pattern):
            if r.get("status") is None: continue
            if status is not None and r["status"] != status: continue
            return r
        time.sleep(poll)
    return None

def wait_for_network_idle(timeout=10.0, idle_ms=500, poll=0.15):
    """Wait until no new `Network.requestWillBeSent` fires for idle_ms, or timeout.

    Good for 'wait for the SPA to finish its burst of fetches'. Returns True on idle,
    False on timeout.
    """
    try: cdp("Network.enable")
    except Exception: pass
    deadline = time.time() + timeout
    last_activity = time.time()
    while time.time() < deadline:
        fresh = drain_events()
        _events_cache.extend(fresh)
        if any(e.get("method") == "Network.requestWillBeSent" for e in fresh):
            last_activity = time.time()
        if (time.time() - last_activity) * 1000 >= idle_ms:
            return True
        time.sleep(poll)
    return False


# --- shadow-DOM-piercing selectors ---
# document.querySelector stops at shadow-root boundaries. Many modern apps (YT Studio,
# Gmail, any Polymer/LitElement app) bury their interactive elements inside nested
# shadow roots. These helpers traverse through them.

_DEEP_QUERY_JS = r"""
(selector) => {
  function walk(root) {
    if (!root) return null;
    try {
      const hit = root.querySelector ? root.querySelector(selector) : null;
      if (hit) return hit;
    } catch (e) {}
    const all = (root.querySelectorAll ? root.querySelectorAll('*') : []);
    for (const el of all) {
      if (el.shadowRoot) {
        const f = walk(el.shadowRoot);
        if (f) return f;
      }
    }
    return null;
  }
  const el = walk(document);
  if (!el) return null;
  el.scrollIntoView({block: 'center', inline: 'center'});
  const r = el.getBoundingClientRect();
  const cs = getComputedStyle(el);
  return JSON.stringify({
    x: r.x + r.width/2, y: r.y + r.height/2,
    w: r.width, h: r.height,
    text: (el.innerText || el.textContent || '').trim().slice(0, 200),
    tag: el.tagName.toLowerCase(),
    visible: r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none'
  });
}
"""

def query_deep(selector):
    """document.querySelector that pierces shadow DOM. Returns {x,y,w,h,text,tag,visible} or None."""
    r = js(f"({_DEEP_QUERY_JS})({json.dumps(selector)})")
    if not r: return None
    return json.loads(r) if isinstance(r, str) else r

def wait_for_element(selector, timeout=15.0, visible=True, poll=0.25):
    """Poll query_deep() until an element is found (and visible if visible=True) or timeout. Returns the hit or None."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        hit = query_deep(selector)
        if hit and (not visible or hit.get("visible")):
            return hit
        time.sleep(poll)
    return None

def click_deep(selector, timeout=10.0):
    """Wait for an element (shadow-DOM-piercing), scroll it into view, and click its center.

    Raises RuntimeError if not found within timeout.
    """
    hit = wait_for_element(selector, timeout=timeout, visible=True)
    if not hit:
        raise RuntimeError(f"click_deep: {selector!r} not found or not visible within {timeout}s")
    click(hit["x"], hit["y"])
    return hit


# --- multi-window tab handling ---
def find_tab(url_substr=None, title_substr=None):
    """Find a tab (across all Chrome windows) by URL or title substring. Returns first match or None."""
    for t in list_tabs(include_chrome=False):
        if url_substr and url_substr in t.get("url", ""): return t
        if title_substr and title_substr in t.get("title", ""): return t
    return None

def focus_browser():
    """Bring the Chrome application to the macOS foreground. No-op on other OSes.

    Target.activateTarget activates a tab within its window, but on macOS that doesn't
    raise Chrome above other apps. Many sites throttle rendering when Chrome isn't the
    frontmost app (IntersectionObserver stalls, requestAnimationFrame slows). Call this
    before running a flow on a virtualized/lazy-rendered page.
    """
    import subprocess
    try:
        subprocess.run(
            ["osascript", "-e", 'tell application "Google Chrome" to activate'],
            timeout=2, check=False, capture_output=True,
        )
    except Exception: pass

def switch_to(url_substr=None, title_substr=None):
    """find_tab + switch_tab + focus_browser, in one call. Returns the tab dict or None."""
    t = find_tab(url_substr=url_substr, title_substr=title_substr)
    if not t: return None
    switch_tab(t["targetId"])
    focus_browser()
    return t


# --- downloads ---
def wait_for_download(before_files=None, dir=None, timeout=60.0, poll=0.5, stable_seconds=1.0):
    """Wait for a new file to appear in `dir` (default ~/Downloads) and finish writing.

    `before_files` is an optional snapshot of the directory taken *before* the click
    that triggers the download — prevents matching an older file. If omitted, this
    function snapshots now (only works if the download truly starts after this call).

    Waits for any *.crdownload partial to finalize, plus stable_seconds of no size change
    for safety. Returns the absolute path of the new file, or None on timeout.
    """
    import os
    dir = os.path.expanduser(dir or "~/Downloads")
    if before_files is None:
        before_files = set(os.listdir(dir))
    deadline = time.time() + timeout
    while time.time() < deadline:
        current = set(os.listdir(dir))
        new = [f for f in (current - before_files) if not f.endswith(".crdownload") and not f.startswith(".")]
        if new:
            path = os.path.join(dir, max(new, key=lambda f: os.path.getmtime(os.path.join(dir, f))))
            # Wait for size to stabilize
            last_size = -1
            stable_start = time.time()
            while time.time() - stable_start < stable_seconds:
                s = os.path.getsize(path)
                if s != last_size:
                    last_size = s
                    stable_start = time.time()
                time.sleep(0.1)
            return path
        time.sleep(poll)
    return None

def snapshot_downloads(dir=None):
    """Snapshot the Downloads dir — pass result as `before_files` to wait_for_download."""
    import os
    return set(os.listdir(os.path.expanduser(dir or "~/Downloads")))


# --- recording ---
def record_gif(duration=5.0, fps=4, out="/tmp/recording.gif"):
    """Capture screenshots at fps for duration seconds, encode GIF via ffmpeg.

    Blocks for `duration`. Runs synchronously — no concurrent actions. Requires ffmpeg.
    For recording a specific interaction, kick this off in a thread:
        from threading import Thread
        t = Thread(target=record_gif, kwargs={"duration": 8, "out": "/tmp/flow.gif"})
        t.start(); click(...); type_text(...); t.join()
    """
    import subprocess, tempfile
    with tempfile.TemporaryDirectory() as tmp:
        n = int(duration * fps)
        interval = 1.0 / fps
        for i in range(n):
            t0 = time.time()
            screenshot(f"{tmp}/{i:04d}.png")
            elapsed = time.time() - t0
            if elapsed < interval: time.sleep(interval - elapsed)
        palette = f"{tmp}/palette.png"
        subprocess.run(
            ["ffmpeg", "-y", "-framerate", str(fps), "-i", f"{tmp}/%04d.png",
             "-vf", "palettegen=reserve_transparent=0", palette],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["ffmpeg", "-y", "-framerate", str(fps), "-i", f"{tmp}/%04d.png",
             "-i", palette, "-lavfi", f"fps={fps}[x];[x][1:v]paletteuse", out],
            check=True, capture_output=True,
        )
    return out
