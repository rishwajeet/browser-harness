# Hard UI automation — the loop to run BEFORE declaring anything impossible

Written 2026-06-19 after a session where I burned ~hundreds of steps and needed the
user to push me to solutions I could have reached alone (YouTube Studio: all-metrics
export + audience-retention curve). This is the process that would have gotten there
autonomously. Read it when a browser/UI task starts fighting back.

## The one belief that changes everything
**If a human can do it in the UI, a programmatic path provably exists.** So "I'm
stuck" is never "it's impossible" — it's "I haven't found the mechanism yet." Do NOT
reach for human-in-the-loop, "accept current," or "this is a hard limit" until you
have inspected the system AND run the loop below. Treat a declared wall as a bug in
your understanding.

## The loop (in order — don't skip)
1. **INSPECT FIRST, never blind-click.** Before any coordinate action: `screenshot()`
   AND dump the relevant DOM/geometry (`getBoundingClientRect`, ids, attributes,
   computed styles) and/or network. Every time you guess coordinates twice and fail,
   STOP and inspect — re-grounding finds the bug in one shot; permuting guesses loops.
2. **Drive the STATE MODEL, not the pixels.** Find where the state lives and set it
   there: URL query params (e.g. Studio columns = `t_metrics`, dimension = `dimension`),
   element ids/attributes (the checkbox `id` was the metric enum; `checked` attr = state),
   stable selectors (`[aria-label="Add metric to table"]`). Pixels are the last resort.
3. **Decompose into single-variable experiments with explicit verification.** Don't run
   end-to-end attempts that fail opaquely. Isolate: *does one click toggle it? does it
   register the underlying MODEL (not just a DOM attribute)? does `elementFromPoint(x,y)`
   actually land inside the element I think I'm clicking? does scrolling THIS element move
   the rows?* Verify each before scaling up.
4. **Trusted vs synthetic events.** Apps often ignore synthetic events (`isTrusted=false`):
   `el.click()`, `dispatchEvent`, setting `el.checked` may flip a DOM attribute but NOT the
   app's model. Real CDP compositor clicks (`click(x,y)`) are trusted and register. If a
   DOM attribute changes but "Apply" ignores it, you're firing synthetic — switch to a real click.
5. **Off-screen elements lie.** `getBoundingClientRect` for scrolled-out items returns stale/garbage
   coords. Only act on an element when `elementFromPoint(center)` is inside it. To reach others,
   find the real scroll container (`overflow-y:auto` ancestor with `scrollHeight>clientHeight`) and
   set its `scrollTop` / wheel over it — then re-read.
6. **Enumerate the artifact's full structure/states before automating.** Lists have collapsible
   sections; dialogs have tabs; tables virtualize columns. Map every state/affordance up front
   (e.g. the 13 collapsible metric categories — iterate them BY NAME, a scroll-scan skips edges).
7. **The data behind a chart is reachable even when the API isn't.** If you can't read the XHR
   (no requestId for `getResponseBody`), the rendered artifact still holds it: read the SVG
   `path` via `getPointAtLength()`+`getScreenCTM()` and calibrate to data using the axis tick
   labels; or inject a `fetch`/`XMLHttpRequest` wrapper (survives SPA nav, not full reload) and
   trigger a re-fetch. Canvas → fall back to the component's data property or the injected interceptor.

## Anti-patterns that cost me this session
- Declaring "export disabled / scroll impossible / curve unreadable" as hard limits — all were
  3 hypotheses away (the user just said "you can figure it out").
- Permuting assumed coordinates/bands instead of screenshotting (the y-band was wrong, the
  checkbox was at x≈567 not 304, the ⊕ was at y≈374 — all visible in one screenshot).
- Running the full pipeline and reading only the final failure, instead of a controlled
  single-element experiment that pinpoints the broken step.
- Letting a `dispatchEvent` that set an attribute convince me a click "worked" — it didn't
  reach the model; only the trusted click did.

## Worked proofs (this session)
- All-metrics export: columns = URL `t_metrics`; expand every category by name; trusted-click
  the left square of only-isBox-verified boxes; Apply→wait→export; redo per breakdown.
  (`masoom_minawala/tools/studio_allmetrics_per_breakdown.py`)
- Retention curve: read SVG `path.line-series` + axis ticks → (second, retention%) points.
  (`masoom_minawala/tools/studio_retention_curve.py`)
