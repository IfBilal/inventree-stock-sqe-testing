# Baseline (upstream reference) and reproducible setup

## Upstream reference
- Repository: https://github.com/inventree/InvenTree
- Licence: MIT
- Pinned commit: `1f51dfe64bf4717fd95df51f1055ffb7a991a01d` (2026-11-16, "[UI] Warn before closing the template editor with unsaved changes (#13280)")
- Version at pin: 1.8.0 dev, API version 580
- Upstream source is vendored unmodified in `upstream/` (its own `.git` removed; the hash above identifies it).

## Git tags
| Tag | Meaning |
|---|---|
| `baseline-source` | Pure vendored upstream source at the pinned commit (nothing else) |
| `baseline` | First reproducible-setup commit (scripts, seed, docs). Superseded by `baseline-v2` after review fixes (seed `delete_on_deplete`, corrected docs). Kept unmodified (published tags are not rewritten) |
| `baseline-v2` | **The official baseline**: upstream source + corrected reproducible setup, **before any change to upstream code or any test**. All later commits (tests, documented fix) come after this tag |

Own tests live in `tests/team/` (upstream tests earn no marks and are never counted).

## Prerequisites
Linux, Python 3.12, Node ≥ 20 (24 used), npm/yarn (yarn is fetched via `npx yarn@1` if missing), ~3 GB free disk (frontend build ≈ 1.5 GB), Chromium via Playwright. Docker is not needed for the application itself.

## Commands (run from the repository root)
| Step | Command | What it does |
|---|---|---|
| Install (once) | `scripts/install.sh` | venv + backend deps + test deps, builds the React UI, collects static files, seeds the DB, installs Playwright Chromium |
| Start | `scripts/start.sh` | `runserver` on http://127.0.0.1:8000 in the background; waits until `/api/` answers (prints `SERVER_UP`) |
| Stop | `scripts/stop.sh` | stops the server |
| Seed + reset | `scripts/reset.sh` | **deletes** `data/inventree.sqlite3`, migrates, and re-seeds `scripts/seed_data.py` (deterministic). Run with the server stopped, then start again |
| Environment | `source scripts/env.sh` | all paths/env vars (SQLite DB under `data/`); defines `$MANAGE` |

Reset determinism was verified: mutate via API → reset → seed state identical (`evidence/phase0/reset_determinism.txt`).

## Seeded state (synthetic)
| Item | Value |
|---|---|
| URL | http://127.0.0.1:8000 (UI at `/web/`, API at `/api/`) |
| Users | `admin` / `admin12345` (superuser, setup only), `manager` / `manager12345` (group `stock_manager`: stock view/add/change/delete), `viewer` / `viewer12345` (group `stock_viewer`: stock view only) |
| Category / location | Peripherals / Main Warehouse |
| Stock items (pk order) | pk 1 Keyboard qty 10, pk 2 Mouse qty 25, pk 3 Monitor qty 0 — all `delete_on_deplete = False` (explicit) |
