# Baseline (upstream reference)
- Upstream repository: https://github.com/inventree/InvenTree
- Licence: MIT
- Pinned commit: `1f51dfe64bf4717fd95df51f1055ffb7a991a01d` (2026-11-16, "[UI] Warn before closing the template editor with unsaved changes (#13280)")
- Version at pin: 1.8.0 dev, API version 580
- Upstream source is vendored unmodified in `upstream/` (its own `.git` removed; the hash above identifies it). Our changes are only in commits after tag `baseline`.
- Own tests live in `tests/team/`. Upstream tests earn no marks.

## Commands
- Reset to seeded baseline: `scripts/reset.sh`
- Environment: `source scripts/env.sh` (sqlite DB at `data/inventree.sqlite3`)
- Start server: `$MANAGE runserver 127.0.0.1:8000 --noreload`
