# claude.ai — exporting a Project (files, memory, all chats) via internal API

Full export of a claude.ai Project — knowledge docs, project-scoped memory, and every conversation with complete message content — without DOM scraping. Everything goes through the same-origin internal JSON API, called with `fetch()` in page context so session cookies apply. Verified 2026-07-13 (Roshan Kotla project, 26 conversations, ~26MB).

## Login trap

A CDP-attached Chrome is often logged OUT of claude.ai even when the user uses Claude daily (they may live in the Desktop app). `https://claude.ai/login?from=logout` → click **Continue with Google**: it opens an accounts.google.com popup as a separate page target that auto-completes and closes if a Google session exists in that Chrome profile. After clicking, don't watch the login tab — poll `Target.getTargets` until a `claude.ai/new` page appears. No password typed; if one is requested, stop and hand back.

## Endpoints (all GET, same-origin, cookie-authed)

```
/api/organizations
    → [{uuid, name}, ...]  — personal org is the one matching the user's name; a second org may 403 on /projects.

/api/organizations/{org}/projects
    → all projects incl. archived. NOTE: project.updated_at is METADATA update time —
      it does NOT reflect chat activity. A project "untouched since 2025" can have chats from yesterday.

/api/organizations/{org}/projects/{proj}
    → detail. prompt_template = custom project instructions. docs_count / files_count.

/api/organizations/{org}/projects/{proj}/docs
    → project knowledge docs, FULL text in .content (file_name, content). This is the whole payload, no pagination seen.

/api/organizations/{org}/projects/{proj}/conversations_v2
    → {data: [...], pagination: {total, limit: 30, offset, has_more}} — paginate with ?offset= if has_more.
      (Legacy /conversations also 200s.)

/api/organizations/{org}/chat_conversations/{uuid}?tree=True&rendering_mode=messages&render_all_tools=true
    → full conversation: chat_messages[] with sender, content[] blocks (text / tool_use / tool_result),
      attachments[] (uploaded files with .extracted_content — full text), files[].
      Artifacts are tool_use blocks named "artifacts" with input.command = create/update/rewrite and the
      content in input.content / input.new_str. Scripts and documents authored in chats live HERE.

/api/organizations/{org}/memory                     → org/user-level memory: {memory, controls, updated_at}
/api/organizations/{org}/memory?project_uuid={proj} → PROJECT-scoped memory (distinct, often the richest
      single artifact — a distilled operating manual of the project). /projects/{proj}/memory 404s; the
      query-param form is the real one.
```

## Big-payload pattern

Conversations can be 5MB+. `Runtime.evaluate` returnByValue chokes on huge strings — stash then chunk:

```python
def fetch_text(path):
    n = js(f"fetch('{path}').then(r=>r.text()).then(t=>{{window.__x=t; return t.length}})")
    return "".join(js(f"window.__x.slice({i},{i+400000})") for i in range(0, n, 400000))
```

~0.4s sleep between conversation pulls was enough; no rate limiting hit at 26 conversations.

## Converting chats to readable transcripts

chat_messages[] → markdown: keep text blocks; render artifact create/rewrite in full (that's the authored work product); truncate tool_result blocks (search dumps); skip thinking blocks; inline attachments' extracted_content (user-uploaded source material — often the only copy of client feedback docs).
