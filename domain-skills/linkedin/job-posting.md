# LinkedIn — posting jobs (field-tested Jun 2026)

## Flow map

`linkedin.com/job-posting/` → title → AI-drafted description (`step=job-details`) →
`step=job-settings` → qualifications/custom-targeting (paid, skippable) →
`/job-posting/form/budget/` → "Post without promoting" → confirm dialog (same button
text inside `[role=dialog]`) → lands on `/hiring/plan/?jobId=<id>`.
Public URL: `linkedin.com/jobs/view/<jobId>/`.

## Traps

- **Draft carry-over**: the title field and ALL job details (company, workplace,
  job type) pre-fill from the user's last abandoned draft — including a possibly
  WRONG COMPANY. Always open "Edit job details" (pencil, `aria-label="Edit job
  details"`) and verify company/type before continuing.
- **Company is a typeahead**: clearing via Cmd+A is unreliable — use
  `inp.focus(); inp.setSelectionRange(0, inp.value.length)` then `Input.insertText`.
  Pick the option from the dropdown (`[role=option]`/li) so it binds to a real
  company page; the top row with an arrow icon is free-text "no LinkedIn page".
- **1 free job limit**: the second job's budget page offers ONLY "Promote job"
  (banner: "You've reached your 1 free job post limit"). The job survives as a
  draft; post free again only after the first closes/pauses. Free jobs auto-pause
  after 14 days or 16 applicants.
- **External apply**: `step=job-settings` → `aria-label="Edit applicant collection"`
  → dropdown "On LinkedIn" → "On an external website" → URL input has placeholder
  containing `yourcompany`. Screening questions are unavailable with external apply.
- **The preload-iframe rerender**: after `goto()` navigations within LinkedIn, the
  whole app may re-render inside a full-page same-origin
  `iframe[src*="/preload/?_bprMode=vanilla"]` — top-document querySelector finds
  NOTHING (not even shadow-DOM piercing helps; it's an iframe boundary). Query/edit
  via `f.contentDocument` + `f.contentWindow.getSelection()` + `d.execCommand`, and
  offset click coords by the iframe rect (full-page → offset 0). Pages reached by
  in-app clicks stay in the top document; goto-navigated ones may not.
- **Description editor** is `.ql-editor[contenteditable=true]` (same as posts) —
  `execCommand('selectAll')` + `Input.insertText` replaces cleanly; surgical-replace
  pattern from editing-profile-and-posts.md works for appending lines.
- **Editing a live free job** re-runs the same flow (Edit job post →
  details/settings/budget) and re-hits the promote upsell — finish with "Not now"
  to save without paying. Qualifications on a live free job are NOT editable
  (modal says promote to edit); put requirements in the description instead.
