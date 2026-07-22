# claude.ai/code — cloud environments, env vars, login

Map of the **Claude Code web** app (`https://claude.ai/code`, the "Cowork"/Routines surface), for tasks that configure cloud agents / routines.

## Login
- `https://claude.ai/code` requires a **web** login. A Chrome attached via CDP is often NOT logged in (the user may live in the Claude **Desktop app**). You'll land on `https://claude.ai/login?returnTo=%2Fcode`.
- **"Continue with Google"** one-clicks through IF a Google session is already active in that Chrome — it opens an `accounts.google.com/...accountchooser` popup (separate page target) that auto-completes and closes; the main tab then lands on `/code`. No password typed. If it asks for a password/2FA, stop and hand back.

## Cloud environment + env vars (where routine secrets go)
- Bottom of the composer: an environment chip (e.g. **"Default"** with a cloud icon) + "Select repo…". Click the chip → dropdown: **Local (Desktop only)**, **Cloud → Default** (with a **gear icon**), **+ Add cloud environment**, **Remote Control**.
- Click the **gear** next to the cloud env → **"Update cloud environment"** modal with: **Name**, **Network access** (Full/…), **Environment variables** (`.env` format textarea), **Setup script** (bash run before Claude Code launches), Archive / Cancel / **Save changes**.
- **Important trap:** the Environment variables field is labelled *"These are visible to anyone using this environment — don't add secrets or credentials."* There is **no separate secure secret store** — it's plaintext. If you must give a routine an API token, this is the only field, and it's plaintext-at-rest. Use a dedicated/rotatable token.
- The env-vars textarea is a React-controlled field: focus it (coordinate click), then `cdp("Input.insertText", text="KEY=value")` commits it (DOM value persists = React accepted it). Verify by reading `textarea.value.length` via `js(...)` — don't print the secret.

## Routines (scheduled cloud agents)
- Sidebar **"Routines"** lists them; also manageable via the `RemoteTrigger` API tool (`list/get/create/update/run`). Routines run in a chosen **cloud environment** and only see that environment's **Web** MCP connectors + env vars — NOT Desktop-only connectors (e.g. Apify, Claude-in-Chrome live under "Desktop" and are unreachable from cloud routines).
