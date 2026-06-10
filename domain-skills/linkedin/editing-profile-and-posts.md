# LinkedIn — editing your own profile and posts (field-tested Jun 2026)

## The spinner trap (automation protection)

`goto("https://www.linkedin.com/feed/update/urn:li:activity:<id>/")` can hang on an **infinite spinner** — the SPA route never resolves when navigated via CDP. A human refresh fixes it, which means the self-serve fix is a real reload, not a re-goto:

```python
cdp("Page.reload", ignoreCache=False)   # mimics a user refresh; resolves the hung route
wait_for_load(); import time; time.sleep(6)
```

Better: **avoid direct permalink navigation entirely** — reach posts by clicking through the UI (profile → Featured/Activity card → post overlay). Click-through never triggered the protection; goto did.

Also: `linkedin.com/in/<user>/` profile URLs and `/details/experience/` etc. load fine via goto. Only the `feed/update/urn:li:activity` permalinks hung.

## URL patterns

- Own profile: `/in/me/` redirects to the real handle (handles may be hyphenated — don't guess from a name).
- Experience editor is a full-page route: `/in/<user>/details/experience/edit/forms/<id>/`.
- After saving an experience edit, LinkedIn redirects to a `next-action/people-you-may-know` follow-up page — that redirect IS the save confirmation.

## Editing mechanics — everything is contenteditable

There are **no `<textarea>`s** in About/experience/post editors — all `[contenteditable=true]` (posts use `.ql-editor`). React/Ember-controlled, so setting `.innerText` directly breaks state. The reliable surgical-replace pattern (fires proper input events):

```js
const ed = document.querySelector('.ql-editor[contenteditable=true], [contenteditable=true]');
ed.focus();
const walker = document.createTreeWalker(ed, NodeFilter.SHOW_TEXT);
let node;
while ((node = walker.nextNode())) {
  const idx = node.textContent.indexOf(TARGET);
  if (idx !== -1) {
    const range = document.createRange();
    range.setStart(node, idx); range.setEnd(node, idx + TARGET.length);
    const sel = window.getSelection();
    sel.removeAllRanges(); sel.addRange(range);
    document.execCommand('insertText', false, REPLACEMENT);
    break;
  }
}
```

Surgical replace > retyping the whole field: rendered innerText from a scrape can differ subtly (quotes, breaks) from the stored text.

## Stable selectors

- Section editors: `button[aria-label="Edit about"]`, `aria-label="Edit <role> at <company>"` on `/details/experience/`.
- Post menu: `button[aria-label*="control menu" i]` → dropdown has "Edit post" / "Delete post" items. DOM `.click()` on the menu *item* sometimes doesn't register — coordinate-click the item instead.
- Save buttons: DOM-click `button` with exact text `Save` works in About modal and post editor; in the post editor verify via the "Changes saved." toast + post gains "• Edited" marker.
- Modal-presence checks are unreliable mid-animation — verify outcomes by toast text / URL change / re-reading the rendered profile, not by "modal gone".

## Traps

- The Featured-section card has no post permalink in its DOM (links inside are @-mentions) — click the card itself to open the post.
- After About save, a Premium upsell modal appears — close via the X before doing anything else.
- LinkedIn marks edited posts with "• Edited" — expected, not an error.
