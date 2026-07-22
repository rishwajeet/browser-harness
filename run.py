import sys

from admin import (
    ensure_daemon,
    list_cloud_profiles,
    list_local_profiles,
    restart_daemon,
    start_remote_daemon,
    stop_remote_daemon,
    sync_local_profile,
)
from helpers import *

HELP = """Browser Harness

Read SKILL.md for the default workflow and examples.

Typical usage:
  uv run bh <<'PY'
  ensure_real_tab()
  print(page_info())
  PY

Helpers are pre-imported. The daemon auto-starts and connects to the running browser.
"""


def main():
    if len(sys.argv) > 1 and sys.argv[1] in {"-h", "--help"}:
        print(HELP)
        return
    if sys.stdin.isatty():
        sys.exit(
            "browser-harness reads Python from stdin. Use:\n"
            "  browser-harness <<'PY'\n"
            "  print(page_info())\n"
            "  PY"
        )
    ensure_daemon()
    # Use a single dict as both globals and locals so module-level assignments in the
    # user's block are visible inside functions they define. Without this, exec treats
    # top-level names as locals of main(), and nested functions' __globals__ can't see
    # them — a surprising pitfall when users define helpers like `studio_url()`.
    ns = dict(globals())
    exec(sys.stdin.read(), ns)


if __name__ == "__main__":
    main()
