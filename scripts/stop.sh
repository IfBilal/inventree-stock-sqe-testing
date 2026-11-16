#!/usr/bin/env bash
# Stop the dev server if it is running (no error when it is not).
if pgrep -f "[m]anage.py runserver" >/dev/null; then pkill -f "[m]anage.py runserver"; fi
exit 0
