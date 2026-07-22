# GoDaddy — DNS record management (field-tested Jun 2026)

## URLs
- DNS records for a domain: `https://dcc.godaddy.com/control/portfolio/<domain>/settings?tab=dns`
- Login wall redirects to `sso.godaddy.com`. **Google SSO works**: the sign-in page has Apple/Facebook/Google buttons at the bottom; clicking the G button → Google account chooser → done. The chooser rows do NOT respond to JS `.click()` — use a **coordinate click** on the account row.

## Structure
- Records live in a `<table>`; rows have per-row `Delete` and `Edit` buttons (aria/text accessible).
- "Add New Record" opens a "New Records" form section with NATIVE elements:
  - type: `select[name='select-input-dns-record-type']` (set value + dispatch `change`)
  - name: `#nameDnsFieldInput` (placeholder `@ or www`)
  - value: `input[placeholder='XX.XX.XX.XX']` for A records
- React-controlled: set values via the native setter + `dispatchEvent(new Event("input"/"change", {bubbles:true}))`.
- With ONE pending row the submit button is labeled **"Save"**; after "Add More Records" it becomes **"Save All Records"** — match both.

## Traps
- **Conflicts with default records**: fresh domains ship with `A @ → Parked` and `CNAME www → <domain>.` Adding a new `A @` or anything named `www` errors with "Record name X conflicts with another record". **Edit the existing record instead of adding** (pencil icon → inline form below the table → Save).
- `CNAME www → <domain>.` is usually fine to keep when pointing the apex elsewhere (www inherits the apex resolution) — e.g. Vercel verifies it.
- Canceling a dirty form raises a "You have unsaved changes" modal — confirm with the "Yes, Cancel" button.
- A cookie banner (Accept/Decline/Manage) blocks bottom-of-page clicks on first load — dismiss it first.
- The "Add New Record" button is disabled while a new-record form is open.
- Default TTL on the parked record is 600s — edits propagate in ~1-2 min.
