# DEFENSIVE SECURITY ASSESSMENT (Phase 9) — local copy, synthetic data and test accounts, **passive inspection only**

Scope: the two workflows (Add / Remove stock). Tools: Playwright 1.65.1 (role checks), OWASP ZAP 2.17.0 in **safe mode** (passive scanners only, no spider, no active scan), pip-audit 2.10.1, `yarn audit` (frontend lockfile). No attack payloads were sent; the server is a throw-away local instance.

## 1. Attack surface: routes and data of both workflows
| Route | Method | Data | Purpose | Right required |
|---|---|---|---|---|
| `/api/stock/{id}/` | GET | `StockItem` (quantity, batch, status…) | read back the shared record | `stock` view |
| `/api/stock/add/` | POST | items[pk, quantity, batch, packaging, status, merge], notes | WF-A Add stock | `stock.add_stockitem` (Django permission from the group's `stock` RuleSet `can_add`) |
| `/api/stock/remove/` | POST | same | WF-B Remove stock | same |
| `/api/stock/{id}/` | PATCH / DELETE | StockItem fields | change / delete item (adjacent actions) | `can_change` / `can_delete` |
| `/api/audit/` | GET | history entries (actor, notes, deltas) | read back history | `stock` view |
| `/web/stock/item/{id}/details` | GET (UI) | React page; operations menu | browser access | session login; menu only if the add right exists |
| `/api/auth/v1/auth/login`, `/api/user/me/` | POST / GET | credentials, session cookie `sessionid`, `csrftoken` | authentication | — |

## 2. Access matrix — verified automatically with Playwright (`tests/team/e2e/access.spec.ts`, results `evidence/security/access_matrix_results.json`)
Expected decisions come from the role design (TEST_BASIS §4): `stock_manager` view/add/change/delete, `stock_viewer` view only, anonymous nothing. **20 decisions checked (allowed and denied), 20 match the matrix.**

| Role | Action | Route | Expected | Observed | Result | Evidence |
|---|---|---|---|---|---|---|
| manager | view item | `GET /api/stock/{id}/` | 200 | 200 | **ALLOWED as expected** | HTTP 200; item pk 4 |
| manager | add stock (WF-A) | `POST /api/stock/add/` | 201 | 201 | **ALLOWED as expected** | HTTP 201; quantity after = 11; item pk 5 |
| manager | remove stock (WF-B) | `POST /api/stock/remove/` | 201 | 201 | **ALLOWED as expected** | HTTP 201; quantity after = 9; item pk 6 |
| manager | edit item (change right) | `PATCH /api/stock/{id}/` | 200 | 200 | **ALLOWED as expected** | HTTP 200; item pk 7 |
| manager | delete item (delete right) | `DELETE /api/stock/{id}/` | 204 | 204 | **ALLOWED as expected** | HTTP 204; item pk 8 |
| manager | read history (audit) | `GET /api/audit/` | 200 | 200 | **ALLOWED as expected** | HTTP 200; item pk 9 |
| viewer | view item | `GET /api/stock/{id}/` | 200 | 200 | **ALLOWED as expected** | HTTP 200; item pk 10 |
| viewer | add stock (WF-A) | `POST /api/stock/add/` | 403 | 403 | **DENIED as expected** | HTTP 403; quantity after = 10; item pk 11 |
| viewer | remove stock (WF-B) | `POST /api/stock/remove/` | 403 | 403 | **DENIED as expected** | HTTP 403; quantity after = 10; item pk 12 |
| viewer | edit item (change right) | `PATCH /api/stock/{id}/` | 403 | 403 | **DENIED as expected** | HTTP 403; item pk 13 |
| viewer | delete item (delete right) | `DELETE /api/stock/{id}/` | 403 | 403 | **DENIED as expected** | HTTP 403; item pk 14 |
| viewer | read history (audit) | `GET /api/audit/` | 200 | 200 | **ALLOWED as expected** | HTTP 200; item pk 15 |
| anonymous | view item | `GET /api/stock/{id}/` | 401 | 401 | **DENIED as expected** | HTTP 401; item pk 16 |
| anonymous | add stock (WF-A) | `POST /api/stock/add/` | 401 | 401 | **DENIED as expected** | HTTP 401; quantity after = 10; item pk 17 |
| anonymous | remove stock (WF-B) | `POST /api/stock/remove/` | 401 | 401 | **DENIED as expected** | HTTP 401; quantity after = 10; item pk 18 |
| anonymous | edit item (change right) | `PATCH /api/stock/{id}/` | 401 | 401 | **DENIED as expected** | HTTP 401; item pk 19 |
| anonymous | delete item (delete right) | `DELETE /api/stock/{id}/` | 401 | 401 | **DENIED as expected** | HTTP 401; item pk 20 |
| anonymous | read history (audit) | `GET /api/audit/` | 401 | 401 | **DENIED as expected** | HTTP 401; item pk 21 |
| viewer | stock operations menu in the UI | `/web/stock/item/{id}/details` | 0 | 0 | **ALLOWED as expected** | menu elements = 0; item pk 22 |
| manager | stock operations menu in the UI | `/web/stock/item/{id}/details` | 1 | 1 | **ALLOWED as expected** | menu elements = 1; item pk 23 |

Denied add **and remove** requests additionally assert that **no side effect occurred** (quantity unchanged, no history entry) — asserted in `access.spec.ts` for both actions. Verdict: **no access-control weakness found** (control working: RuleSet → Django permission → `ModelPermission` on `StockItem`).

## 3. OWASP ZAP passive scan while the Playwright tests run both workflows
Script: `scripts/zap_passive_run.sh` (launch command saved in `evidence/security/zap_launch_command.txt`; **mode queried from the ZAP API: `safe`** — passive scanners only, no spider, no active scan, `zap_mode.json`). The Playwright specs UC-01 (add) and UC-02 (remove) — 13 tests, 0 unexpected results — ran through the proxy: **1599 HTTP messages** recorded (236 distinct URLs), including **10 POST requests to the workflow endpoints** (/api/stock/add/: 5, /api/stock/remove/: 5; `zap_workflow_post_evidence.json`), passive queue drained before export. Raw alerts: `zap_alerts_raw.json`; raw `Set-Cookie` headers: `zap_set_cookie_headers.txt`.

| Risk | Alert | Instances | Evidence (first) | Component | Likely impact | Recommended correction |
|---|---|---|---|---|---|---|
| Medium | Content Security Policy (CSP) Header Not Set | 12 | `` | Web pages (`/web/*`); no CSP in `InvenTree/settings.py` | No browser-enforced restriction on script/style sources: a successful XSS (none found) would face no second line of defence. | Send a `Content-Security-Policy` header (e.g. `default-src 'self'`) from the reverse proxy / Django CSP middleware. |
| Low | Cookie No HttpOnly Flag | 14 | `Set-Cookie: csrftoken` | `csrftoken` cookie (14 instances); `sessionid` **is** HttpOnly (not flagged) | Low: the CSRF token must be readable by the SPA (double-submit pattern), so this is by design; the session cookie is protected. | No change needed for `csrftoken`; keep `SESSION_COOKIE_HTTPONLY` true. Dismiss as accepted risk. |
| Low | Cookie without SameSite Attribute | 15 | `Set-Cookie: csrftoken` | `csrftoken` (14) and `sessionid` (1); `COOKIE_MODE` default `'False'` omits the attribute (`settings.py` L958-975) | Without an explicit attribute, cross-site requests rely on the browser default (Lax in current browsers); older browsers may send the cookie cross-site (CSRF exposure). | Set `INVENTREE_COOKIE_SAMESITE=Lax` (or Strict) in the deployment configuration. |
| Low | Server Leaks Version Information via "Server" HTTP Response Header Field | 169 | `WSGIServer/0.2 CPython/3.12.3` | Django development server `WSGIServer/0.2 CPython/3.12.3` (all responses) | Reveals server and Python version to an attacker (fingerprinting). Specific to `runserver`, which must not be used in production. | Deploy behind gunicorn + a reverse proxy and strip/replace the `Server` header. |
| Low | Timestamp Disclosure - Unix | 5 | `1794852572` | Authentication API responses (e.g. `/api/auth/v1/auth/login`) | Unix timestamps in JSON (session/expiry data): benign, may help correlate server time. | Accept (informational); no action. |
| Informational | Authentication Request Identified | 3 | `password` | Login request `/api/auth/v1/auth/login` | Informational: ZAP identified the login form (used for context). | None. |
| Informational | Modern Web Application | 11 | `<noscript>       <!-- fallback if javascript is blocked` | SPA front end | Informational: single-page app detected. | None. |
| Informational | Session Management Response Identified | 16 | `csrftoken` | Session/CSRF cookies | Informational. | None. |

### 3.1 Security controls reviewed (≥ 2 required) — corroborated with source/configuration and live headers
| Control | Observation (ZAP / live) | Source / config corroboration | Verdict |
|---|---|---|---|
| **Session cookie attributes** | raw header (`zap_set_cookie_headers.txt`): `sessionid=…; HttpOnly; Max-Age=1209600; Path=/` — HttpOnly present, SameSite absent, Secure absent (HTTP dev server) | `settings.py` L958-993: `SESSION_COOKIE_SAMESITE = COOKIE_MODE` (default `False` → attribute omitted); `SESSION_COOKIE_SECURE` default false (true behind HTTPS); HttpOnly is Django's default | **Partially met**: HttpOnly ✔; SameSite and Secure need deployment settings (finding F-2) |
| **Role-based access checks** | Viewer / anonymous denied on add and remove, no side effect (§2) | `ModelPermission` (DRF `DjangoModelPermissions`) on `StockItem` queryset + `update_group_roles` (see TEST_BASIS §4 BR-4) | **Met** (no findings) |
| **CSRF protection** | `POST /api/auth/v1/auth/login` without a CSRF token → **403** (live check, saved: `evidence/security/csrf_login_check.txt`); `csrftoken` cookie + `X-CSRFToken` header used by the SPA | `CSRF_HEADER_NAME`, `CSRF_COOKIE_NAME` in `settings.py` L970-975; `django.middleware.csrf` enabled | **Met** |
| **Clickjacking / MIME-sniffing / referrer headers** | Responses carry `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin`, `Cross-Origin-Opener-Policy: same-origin` | `SecurityMiddleware`, `XFrameOptionsMiddleware` in `settings.py` | **Met** (CSP missing: finding F-1) |
| **Authentication endpoint** | Login via allauth headless API; wrong credentials → 401 (UC05, API tests) | — | **Met** (note DEF-05: first login after restart silently fails — usability) |

## 4. Dependency audit
### 4.1 Backend — `pip-audit` on `upstream/src/backend/requirements.txt` (pinned, hash-locked)
Packages checked: **166** (full list with versions: `evidence/security/pip_audit_packages.txt`; raw `evidence/security/pip_audit.json`; includes Django 5.2.19, djangorestframework, gunicorn 26.2.0, requests, cryptography…). Result: **0 packages with known vulnerabilities** — *documented control with no findings* (checked 2026-11-16 against the PyPI/OSV advisory databases).

### 4.2 Frontend — `yarn audit` on `upstream/src/frontend/yarn.lock`
875 dependencies checked; advisories: {'moderate': 8, 'high': 1} (raw `evidence/security/yarn_audit.jsonl`). The 9 advisory lines are **5 unique advisories**: the remaining 4 are the same `glob`/`minimatch` advisories reported through additional dependency paths (e.g. via `nyc`).

| Package (version) | Severity | Advisory | Dependency path | Runtime or build-time | Likely impact | Recommended correction |
|---|---|---|---|---|---|---|
| react-router@6.30.6 | moderate | React Router: Open redirect via backslash in <Link> and useNavigate (CVE-2025-68 | `react-router-dom>react-router` | runtime (shipped bundle) | Open redirect / unsafe deserialisation in client routing — relevant to the shipped UI | upgrade to >=7.18.0 |
| react-router@6.30.6 | moderate | React Router: Arbitrary Constructor Injection via deserializeErrors() in React R | `react-router-dom>react-router` | runtime (shipped bundle) | Open redirect / unsafe deserialisation in client routing — relevant to the shipped UI | upgrade to >=7.18.0 |
| glob@13.0.6 | moderate | Glob: AbortSignal cancellation bypass allows post-timeout filesystem traversal | `@lingui/cli>glob` | build tooling only | Developer/CI machine only (not in the served bundle) | upgrade to >=14.0.2 |
| minimatch@10.2.6 | moderate | minimatch has potential denial of service via globparts amplification | `@lingui/cli>glob>minimatch` | build tooling only | Developer/CI machine only (not in the served bundle) | upgrade to >=11.0.1 |
| zod@3.25.76 | high | Zod can exhaust memory while validating oversized constrained collections | `@codecov/vite-plugin>@codecov/bundler-plugin-core>zod` | build tooling only | Developer/CI machine only (not in the served bundle) | upgrade to >=4.6.6 |

## 5. Findings and links to the risk register
| ID | Finding | Component | Evidence | Likely impact | Correction | Risk |
|---|---|---|---|---|---|---|
| F-1 | No Content-Security-Policy header | web server config | ZAP (12 pages) | Medium | add CSP | PR-02 / PR-10 (defence in depth) |
| F-2 | Session cookie without SameSite/Secure by default | `settings.py` | ZAP + source | Low | set `INVENTREE_COOKIE_SAMESITE`, enable secure cookies over HTTPS | PR-02 |
| F-3 | `Server` header discloses version (dev server) | deployment | ZAP (168) | Low | production server + header filtering | PR-10 |
| F-4 | Frontend dependency `react-router@6.30.6` has 2 moderate advisories in the shipped bundle | `yarn.lock` | yarn audit | Moderate | upgrade to ≥ 7.18 (major) or apply backport | PR-10 |
| F-5 | Build-tool advisories (glob, minimatch, zod high) | dev dependencies | yarn audit | Low (not served) | upgrade tooling | PR-10 |
| — | **No access-control, injection or authentication weakness found** in the two workflows; backend dependencies clean | — | §2, §4.1 | — | — | EC-2 met on the tested scope |


## 6. Remediation after the first assessment (pull request #18)
| Finding | Fix | Verification |
|---|---|---|
| F-1 / SEC-01 no CSP | `ContentSecurityPolicyMiddleware` (`InvenTree/middleware.py`): `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; …; frame-ancestors 'self'` (the admin and API-documentation pages are excluded) | the response header is present (`evidence/security/after_fix_headers.txt`), 5 unit tests, and the **whole Playwright suite (57 tests) passes with the policy**, so the UI works under it |
| F-2 / SEC-02 cookies without SameSite | the default of `INVENTREE_COOKIE_SAMESITE` changed from `False` to `Lax` | `Set-Cookie: csrftoken=…; SameSite=Lax` in the same evidence file; unit test |
| F-4 / SEC-03 `react-router` advisories | **accepted risk, not fixed:** there is no patched 6.x release (fixed in ≥ 7.18, a major migration of the whole UI). Impact: an open redirect through a crafted `<Link>` with a backslash and a deserialisation of server errors that the app does not use; the new CSP and `SameSite=Lax` narrow the exploitation | disposition recorded in `docs/DEFECTS.md` (Accepted) |
| F-5 build-tool advisories | accepted: development-time packages that are not part of the served bundle | — |
A repeated ZAP passive scan was not possible after the fixes (ZAP was removed from the disk to make room for the other tools); the header evidence and the unit and browser tests above replace it, and the first scan stays the baseline.

