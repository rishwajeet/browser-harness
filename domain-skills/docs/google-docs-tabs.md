# Google Docs — programmatic tabs (create / fill / rename)

Google Docs **tabs are UI-only** — no Drive/Docs API support for create/rename/delete (as of 2026-06). Apps Script can read tabs but not create them. So tab management = drive the editor UI.

## The mechanics that actually work

- **The editor body is canvas (Kix)** — text is NOT in the DOM, can't be selected via JS. But the **tabs sidebar is real DOM** (aria-labels), and **`Input.insertText` writes into the canvas**.

- **Insert text via `type_text` (CDP `Input.insertText`), NOT paste.** Synthetic `Cmd/Ctrl+V` does **nothing** (synthetic keys can't read the clipboard). `Input.insertText` inserts at the cursor and **converts `\n` to real paragraph breaks**. Handles large inserts fine (18 KB / 3000 words tested in one call).

- **Clear a tab's body:** click into body → `press_key("a", modifiers=4)` (Cmd+A) → `press_key("Delete")`. Cmd+A scopes to the active tab's body only.

- **Switch tabs:** click the tab in the sidebar, or navigate `?tab=t.0` (first tab) / `?tab=t.<id>`.

## Opening the tabs panel + "Add tab"

- Toggle is **"Show tabs & outlines"** (find by `aria-label`), distinct from the **"Menus"** search which sits right next to it — don't confuse them.
- **TRAP: `getBoundingClientRect` / `checkVisibility` LIE for Closure panel elements** — "Add tab" reports a non-zero rect and "visible" even when the panel is **collapsed and unclickable**. You must actually open the panel first (click the toggle), then the Add-tab button works. The one-time failures all traced to clicking Add-tab while the panel was collapsed.
- **"Add tab" is a `jfk-button` (`role=button`)** — needs a **hover before the press**: dispatch `mouseMoved` to its center, *then* `mousePressed`+`mouseReleased`. A plain press/release (no preceding move) misses. Verify success: a new `Tab 2` aria-label appears and the URL `?tab=` changes to a new id.

## Rename a tab

Hover the tab → click its **"Tab options"** (⋮, aria-label) → click the **"Rename"** `[role=menuitem]` → an **`<input type=text>` receives focus** → `Cmd+A`, `type_text(name)`, `Enter`.
**GUARD:** only type if `document.activeElement.tagName === 'INPUT'`. If the rename field didn't focus, typing would overwrite the document body.

## Coordinate gotcha

Screenshots render at ~half scale (Retina 2×). **Use CSS coords from `getBoundingClientRect`, never coords eyeballed off a screenshot** — reading visual `[25,82]` as CSS lands on the wrong control (e.g. Menus instead of the tabs toggle).

## Connection note

The automation Chrome may run a separate `--user-data-dir` (e.g. `Chrome-Automation`) while a stale `DevToolsActivePort` sits in the default profile dir → daemon connects to a dead browser GUID → `HTTP 404` handshake. Fix: `curl -s http://127.0.0.1:9222/json/version` for the live `webSocketDebuggerUrl`, then `BU_CDP_WS=<that> restart_daemon()`.

## Formatting a tab (headings / italic) — no API, no paste

You cannot paste HTML/rich text via automation, and there's no formatting API. The only path is driving **paragraph-style keyboard shortcuts** through the editor:

- **Apply paragraph style:** `Cmd+Opt+0/1/2/3` = Normal / H1 / H2 / H3 (macOS). Send as a **`rawKeyDown`** (NOT the helper `press_key`, which also fires a `char` event and would insert the digit). Example: `cdp("Input.dispatchKeyEvent", type="rawKeyDown", windowsVirtualKeyCode=ord("2"), modifiers=5, key="2", code="Digit2")` then a matching `keyUp`. (`modifiers=5` = Meta(4)+Alt(1).)
- **Build pattern (deterministic):** clear the tab (`Cmd+A`+`Delete`), then for each block: set its style, `type_text(text)`, `Enter`. Setting the style *before typing each block* (incl. Normal for body) is robust — no need to rely on what Enter inherits. Italic for visual cues: `Cmd+I` (rawKeyDown) on, type, `Cmd+I` off.
- **`type_text` (`Input.insertText`) converts `\n` to paragraph breaks** and handles 18 KB in one call.

### The focus trap (cost a full debug cycle)
**Do NOT `goto()`/reload the doc inside a format build** — after a reload the editor canvas isn't focused, so every keystroke/`insertText` **silently no-ops** (build "completes" but the doc is unchanged, not corrupted). Instead operate on the **already-loaded** doc: `switch_to(url_substr=<docId>)` to bring an open tab to front, or for a fresh tab `new_tab` + `wait_for_load` + `wait(6)` + a **double `click` into the body** to lock focus before typing. Verify by typing a throwaway marker first if unsure.
