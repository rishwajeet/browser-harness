#!/usr/bin/env bash
# automation_session.sh — bring up an AUTONOMOUS, dialog-free Chrome session for
# browser-harness, with NO "Allow remote debugging?" consent modal. UNIVERSAL.
#
# WHY THIS EXISTS (field-tested 2026-06-19, generalized 2026-06-26):
#   Chrome 136+ hardened the "Allow remote debugging?" consent modal against ALL
#   synthetic input — cliclick, AppleScript AXPress, System Events `click at`, and
#   raw CGEvent all land dead-center on Allow but are rejected by design. AND newer
#   Chrome refuses --remote-debugging-port on the DEFAULT user-data-dir for security.
#   So attaching the harness to the user's normal Chrome now hangs on a modal that
#   cannot be clicked programmatically.
#
#   The fix the automation world uses: a DEDICATED user-data-dir. A custom profile
#   dir + --remote-debugging-port binds the port AND never shows the modal. We seed
#   that dir once with a copy of the real logged-in profile (same macOS user → same
#   Chrome Safe Storage Keychain key → cookies/logins decrypt fine), so it comes up
#   already signed in. The daemon is pointed at the endpoint via BU_CDP_WS, which a
#   custom-dir Chrome serves at /json/version (the daemon prefers BU_CDP_WS over
#   local DevToolsActivePort discovery — see daemon.py get_ws_url()).
#
#   Generalized from masoom_minawala/tools/studio_session.sh — same mechanism, but
#   site-agnostic, auto-picks a free port, and lives in the universal harness so
#   EVERY browser task can skip the dialog, not just YouTube Studio.
#
# USAGE:
#   eval "$(browser-harness/automation_session.sh)"   # boot + export BU_CDP_WS, then:
#   browser-harness <<'PY' ... PY                      #   (BU_CDP_WS now in env)
#
#   automation_session.sh --no-auth      # first boot WITHOUT seeding (clean profile,
#                                         #   fast, for public sites needing no login)
#   automation_session.sh --refresh-auth # re-seed auth from the real profile
#                                         #   (run when logins expire; quit normal Chrome first)
#   automation_session.sh --quit         # quit ONLY the automation Chrome
#   automation_session.sh --status       # human-readable status to stderr
#
# ENV OVERRIDES:
#   BH_PORT        preferred CDP port (default 9222; auto-bumps if a FOREIGN
#                  process holds it, so the user's own Chrome is never disturbed)
#   BH_PROFILE_DIR automation profile dir (default ~/.../Chrome-Automation; shared
#                  with studio_session.sh so one seeded profile serves every task)
#
# Everything except the final `export BU_CDP_WS=...` line goes to stderr, so the
# default action is safe to `eval`.

set -euo pipefail

PREF_PORT="${BH_PORT:-9222}"
SRC="$HOME/Library/Application Support/Google/Chrome"
DST="${BH_PROFILE_DIR:-$HOME/Library/Application Support/Google/Chrome-Automation}"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
MARKER="user-data-dir=$DST"

log() { echo "[automation_session] $*" >&2; }

port_listening() { lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1; }

automation_pids() { pgrep -f "$MARKER" 2>/dev/null || true; }

# The port our automation Chrome is actually bound to (read from its profile dir).
automation_port() {
  [ -f "$DST/DevToolsActivePort" ] || return 1
  head -1 "$DST/DevToolsActivePort" 2>/dev/null
}

resolve_ws() {
  curl -s --max-time 5 "http://127.0.0.1:$1/json/version" \
    | python3 -c "import sys,json;print(json.load(sys.stdin)['webSocketDebuggerUrl'])" 2>/dev/null
}

# Pick PREF_PORT if free or already ours; otherwise bump to the next free port so
# we never collide with (or hijack) the user's normal Chrome on the default port.
pick_port() {
  local p="$PREF_PORT"
  for _ in $(seq 1 20); do
    if ! port_listening "$p"; then echo "$p"; return 0; fi
    # port is up — is it OURS? (automation Chrome already running on it)
    if [ "$(automation_port 2>/dev/null || true)" = "$p" ] && [ -n "$(automation_pids)" ]; then
      echo "$p"; return 0
    fi
    p=$((p + 1))
  done
  log "FATAL: no free port found in range $PREF_PORT-$((PREF_PORT + 19))"; return 1
}

quit_automation() {
  local pids; pids="$(automation_pids)"
  if [ -n "$pids" ]; then
    log "quitting automation Chrome (pids: $pids)"
    # shellcheck disable=SC2086
    kill $pids 2>/dev/null || true
    for _ in $(seq 1 10); do [ -z "$(automation_pids)" ] && break; sleep 1; done
    # shellcheck disable=SC2046
    [ -n "$(automation_pids)" ] && kill -9 $(automation_pids) 2>/dev/null || true
  fi
}

seed_auth() {
  # Copy the real logged-in profile's auth state into the automation dir.
  # Excludes caches for speed. Source Chrome should be CLOSED for a clean SQLite copy.
  if pgrep -f "user-data-dir=$SRC" >/dev/null 2>&1 || \
     ( pgrep -x "Google Chrome" >/dev/null 2>&1 && [ -z "$(automation_pids)" ] ); then
    log "WARNING: your normal Chrome appears to be running — cookies may copy stale/locked."
    log "         For a clean refresh, quit your normal Chrome first."
  fi
  mkdir -p "$DST"
  log "seeding auth from real profile (copies ~0.6GB, excluding caches)…"
  cp -f "$SRC/Local State" "$DST/Local State"
  rsync -a --delete \
    --exclude 'Cache' --exclude 'Code Cache' --exclude 'GPUCache' --exclude 'DawnGraphiteCache' \
    --exclude 'DawnWebGPUCache' --exclude 'GrShaderCache' --exclude 'ShaderCache' \
    --exclude 'Service Worker/CacheStorage' --exclude 'Service Worker/ScriptCache' \
    --exclude 'component_crx_cache' --exclude 'extensions_crx_cache' --exclude '*.log' \
    "$SRC/Default/" "$DST/Default/" 2>/dev/null
  rm -f "$DST/SingletonLock" "$DST/SingletonCookie" "$DST/SingletonSocket"
  log "auth seeded."
}

launch() {
  local port="$1"
  rm -f "$DST/SingletonLock" "$DST/SingletonCookie" "$DST/SingletonSocket"
  log "launching automation Chrome (profile: $(basename "$DST"), port $port)…"
  # LaunchServices owns the new app instance after this short-lived shell exits.
  # Starting the Mach-O directly (even under nohup) can leave it tied to the
  # bootstrap process: the first harness call works, then Chrome and its CDP
  # websocket disappear as soon as automation_session.sh returns.
  open -na "Google Chrome" --args \
    --user-data-dir="$DST" --remote-debugging-port="$port" \
    --remote-allow-origins='*' --no-first-run --no-default-browser-check \
    >/dev/null 2>&1
  for _ in $(seq 1 30); do port_listening "$port" && break; sleep 1; done
  port_listening "$port" || { log "FATAL: port $port did not come up"; exit 1; }
}

NO_AUTH=0
case "${1:-}" in
  --quit)
    quit_automation; log "done."; exit 0 ;;
  --refresh-auth)
    quit_automation; seed_auth; log "re-seeded. Re-run without args to boot."; exit 0 ;;
  --status)
    if [ -n "$(automation_pids)" ]; then
      p="$(automation_port || echo '?')"
      log "automation Chrome UP on port $p; ws=$(resolve_ws "$p")"
    else
      log "automation Chrome DOWN"
    fi
    [ -d "$DST/Default" ] && log "automation profile present ($(du -sh "$DST/Default" 2>/dev/null | cut -f1))" || log "no automation profile yet (will seed on first boot)"
    exit 0 ;;
  --no-auth) NO_AUTH=1 ;;
  ""|--boot) ;;
  *) log "unknown arg: $1"; exit 2 ;;
esac

# 1. Ensure the automation profile exists (seed from real profile unless --no-auth).
if [ ! -d "$DST/Default" ]; then
  if [ "$NO_AUTH" = "1" ]; then
    log "creating clean automation profile (no auth seed)…"
    mkdir -p "$DST/Default"
  else
    seed_auth
  fi
fi

# 2. Ensure automation Chrome is up; reuse if already running, else launch on a free port.
if [ -n "$(automation_pids)" ]; then
  PORT="$(automation_port || echo "$PREF_PORT")"
  port_listening "$PORT" || { quit_automation; PORT="$(pick_port)"; launch "$PORT"; }
else
  PORT="$(pick_port)"
  launch "$PORT"
fi

# 3. Resolve the websocket endpoint and export it for the daemon.
WS="$(resolve_ws "$PORT" || true)"
if [ -z "$WS" ]; then
  log "could not resolve ws endpoint; relaunching once…"
  quit_automation; PORT="$(pick_port)"; launch "$PORT"; WS="$(resolve_ws "$PORT" || true)"
fi
[ -z "$WS" ] && { log "FATAL: no ws endpoint on port $PORT"; exit 1; }

log "session ready on port $PORT. ws=$WS"
echo "export BU_CDP_WS=$WS"
