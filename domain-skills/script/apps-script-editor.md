# script.google.com — Apps Script editor (run code in the user's Google account)

The fastest way to do bulk Google-product work (create Forms, Docs, Sheets, Drive ops)
is NOT clicking through the product UI — it's running an Apps Script in the user's
logged-in account. One script run = the whole artifact built server-side.

## Recipe (field-tested Jun 2026, built 2 Google Forms with ~60 items each)

1. `new_tab("https://script.new")` — instantly creates a new project and lands in the
   editor (`script.google.com/.../edit`). May show a "You're currently signed in as …"
   popup with an OK button — dismiss it first.

2. **Insert code into the Monaco editor**: click anywhere in the editor area, then
   select-all + insertText. `Input.insertText` is paste-like — it does NOT trigger
   Monaco auto-indent/auto-closing-bracket corruption. Do not type char-by-char.

   ```python
   click(700, 300)  # focus editor
   cdp("Input.dispatchKeyEvent", type="keyDown", key="a", code="KeyA",
       windowsVirtualKeyCode=65, nativeVirtualKeyCode=65, modifiers=4)
   cdp("Input.dispatchKeyEvent", type="keyUp", key="a", code="KeyA",
       windowsVirtualKeyCode=65, nativeVirtualKeyCode=65, modifiers=4)
   type_text(open("my_script.gs").read())
   ```

3. **Save** with raw Cmd+S key events (press_key("s", modifiers=4) computes the wrong
   virtual key code for letters — dispatch manually with vk 83 / code "KeyS").
   After save, the function dropdown in the toolbar populates — that's the signal the
   script parsed without syntax errors.

4. **Run**: the Run button is a `<button>` whose trimmed textContent is exactly
   `play_arrow\nRun` — find by text scan over `button,div[role=button]`, not by
   aria-label (none). The function dropdown next to it auto-selects the first function.

5. **First-run OAuth flow** (only once per project scope set):
   - "Authorization required" dialog → click button with text "Review permissions"
   - Opens a POPUP WINDOW (separate target) at `accounts.google.com/signin/oauth/...`
     → `switch_to(url_substr="accounts.google.com")`
   - Consent page button text is **"Continue"** (not "Allow") for own-account scripts.
     Personal scripts with limited scopes (e.g. only `forms`) skip the "unverified app"
     warning entirely.
   - Popup closes itself; `switch_to(url_substr="script.google.com")` to get back.
     The run proceeds automatically after consent — no need to click Run again.

6. **Read results**: have the script `Logger.log('KEY: ' + value)` greppable lines,
   then poll `js("document.body.innerText")` for "Execution completed" / your keys and
   regex them out. The execution-log panel has no stable class — body innerText works.
   A 2-form, ~60-item FormApp run took ~45s.

## Traps

- Screenshots may come back at 0.5x the CSS-px coordinate space on Retina — trust
  `getBoundingClientRect()` coordinates from `js()` for clicks, not screenshot pixels.
- `FormApp.create(...)` + `setCollectEmail(true)` produces the "Verified" email mode
  (respondents must be signed into Google). Switching to "Responder input" is
  UI-only — not exposed via FormApp.
- The editor body innerText includes the whole code listing — anchor your regexes on
  unique log prefixes, not generic words like "http".
