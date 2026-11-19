# Findings register: root cause, severity, risk and fix per finding
Covers every finding of the API, accessibility, security and performance activities (the functional defects DEF-01…06 have their own root-cause analysis in `docs/RCA.md`). Severity: Critical / High / Medium / Low; risk IDs refer to `docs/RISK_REGISTER.md`. Status "open" findings are deferred and listed in the completion report.

## 1. API findings (endpoint weaknesses, observed and asserted by tests in `tests/team/api/`)
| ID | Finding | Root cause | Severity | Risk | Fix / disposition |
|---|---|---|---|---|---|
| W-01 | 201 response only echoes the request; resulting balance not returned | Serializer `save()` returns the validated input; no output representation of the new quantity | Low | PR-07 | Return the resulting quantity per item. Open (upstream behaviour; client does a GET) |
| W-02 | Unknown top-level fields (typo `note`) silently accepted | DRF serializers ignore undeclared fields by default; no strict-mode check | Low | PR-04 | Reject unknown fields. Open |
| W-03 | No idempotency key: a retry after a lost response is applied twice | The endpoint is a non-idempotent delta (`quantity ± N`); no request identifier is stored | Medium | PR-06 | Accept an `Idempotency-Key`. Open; documented as residual risk |
| W-04 | `pk` as a numeric string accepted | DRF `PrimaryKeyRelatedField` coerces strings to int | Low | PR-04 | Strict typing. Accepted (cosmetic) |
| W-05 | 500 responses expose the Python exception class | Unhandled `TypeError` on malformed `items` reached the generic error handler (same cause as DEF-04) | Medium | PR-04 | Fixed with DEF-04 (PR #17): malformed input now yields 400 |
| W-06 | Audit endpoint ignores the `object_pk` filter | The filter name is not declared on the audit filter set, so it is dropped silently | Low | PR-07 | Support or reject the filter. Open |
| W-07 | Add/remove on a serialized or depleted item returns 201 although nothing changed | `save()` skips non-adjustable items without reporting an error | Medium | PR-05 | Return 400 with a message. Open |
| W-08 | Boolean field `merge` accepts integers 0/1 | DRF `BooleanField` accepts 0/1 and strings | Low | PR-04 | Strict typing. Accepted |
| W-09 | Audit query parameters are not validated | Query filters ignore unknown values instead of returning 400 | Low | PR-07 | Validate or reject. Accepted |
| W-10 | Quantity returned as a JSON float (`10.0`) although inputs are decimal strings | The item serializer renders the stored decimal as a JSON number (float) instead of a string | Low | PR-04 | Render decimals as strings. Accepted (precision hazard noted) |
| W-11 | Missing referenced item gives 400 where GET gives 404 | Body references are validated as field errors | Low | PR-07 | Document. Accepted |
| W-12 | Boolean `true` accepted as `pk` 1 | Python `bool` is an `int`; field does not reject it | Low | PR-04 | Strict typing. Accepted |
| W-13 | 201 echo has `pk: null` when removal deletes the depleted item | The item is deleted (BR-3) before the response is built | Low | PR-05 | Return the original pk. Accepted |

## 2. Accessibility findings (Lighthouse + axe-core; detail and element locators in `docs/ACCESSIBILITY.md`)
| ID | Finding (rule) | Root cause | Severity | Risk | Fix / disposition |
|---|---|---|---|---|---|
| A11Y-01a | `image-alt`: item pictures without a text alternative | The image component renders `<img>` without an `alt` attribute | Medium | PR-09 | Fixed (PR #15): `alt` added (empty for decorative thumbnails) |
| A11Y-01b | `landmark-one-main`: no `main` landmark | The routed page content is not wrapped in a `<main>` element | Medium | PR-09 | Fixed (PR #15) |
| A11Y-02a | `aria-required-children` (critical): tab list contains non-tab children | The tab list wrapped group boxes, labels, dividers and the collapse button inside the `tablist` | High (axe: critical) | PR-09 | Fixed (PR #19): wrappers are presentational and the collapse control sits outside the tab list; no longer reported on any screen |
| A11Y-02b | `button-name` (critical): icon-only buttons without a name | The panel collapse button, notification close button and modal close button had no `aria-label` | High (axe: critical) | PR-09 | Fixed (PR #19): accessible names added (collapse button directly, notification/modal close buttons through the theme defaults); no longer reported |
| A11Y-02c | `color-contrast` (serious): breadcrumb 4.32:1, badge 3.55:1 | Theme colours below the 4.5:1 AA ratio | Medium | PR-09 | Open: adjust theme colours (still reported) |
| A11Y-02d | `page-has-heading-one`, `region`, `aria-allowed-attr` (moderate) | Page title not rendered as `<h1>`; tip banner outside landmarks; a `Group` carries `aria-haspopup`/`aria-expanded` without a matching role | Low | PR-09 | Open |
| A11Y-02e | `meta-description`, `robots-txt` (SEO only) | Missing `<meta>` and `robots.txt` in the SPA shell | Low | PR-09 | Not applicable to a private application behind a login |
| UX-01 | Enter in the quantity field does not submit the dialog | The dialog form has no `<form>` submit handler for the Enter key | Low | PR-09 | Open (deferred) |

## 3. Security findings (access matrix, ZAP passive, pip-audit, yarn audit; detail in `docs/SECURITY.md`)
| ID | Finding | Root cause | Severity | Risk | Fix / disposition |
|---|---|---|---|---|---|
| SEC-01 | ZAP: Content-Security-Policy header not set | No middleware or setting emits the header | Medium | PR-02, PR-10 | Fixed (PR #18): `ContentSecurityPolicyMiddleware`, tests in `test_security_headers.py` |
| SEC-02 | ZAP: session cookie without SameSite | `COOKIE_MODE` default omits the attribute | Low | PR-02 | Fixed (PR #18): default `Lax` |
| SEC-03 | yarn audit: react-router 6.30.6 advisories in the shipped bundle | Dependency pinned to the 6.x line; no patched 6.x release exists (fix = major migration to 7.x) | Medium | PR-10 | Accepted risk (issue #9): exploitation narrowed by CSP and SameSite; re-evaluate on the next upstream release |
| SEC-04 | ZAP: `csrftoken` cookie not HttpOnly | By design: the SPA must read the CSRF token (double-submit pattern); `sessionid` is HttpOnly | Low | PR-02 | Accepted (by design) |
| SEC-05 | ZAP: Server header leaks version | Django development server banner | Low | PR-02 | Accepted: the production deployment (gunicorn behind a proxy) controls the header |
| SEC-06 | ZAP: Unix timestamp disclosure in login responses | Session expiry fields in the auth API JSON | Low | PR-02 | Accepted (informational) |
| SEC-07 | Role-based access (20 checks) | n/a: no finding, all decisions as expected | – | PR-02 | none needed; pip-audit: 166 packages, 0 known vulnerabilities |

## 4. Performance findings (k6, `docs/PERFORMANCE.md`)
| ID | Finding | Root cause | Severity | Risk | Fix / disposition |
|---|---|---|---|---|---|
| DEF-06 | Baseline: about 19.5 % of requests fail with HTTP 500 at 5 users | SQLite write lock contention: deferred transactions upgrade to a write lock, collide, and the default timeout expires ("database is locked") | High | PR-08 | Fixed (PR #18): `IMMEDIATE` transactions and a 30 s timeout; failures 0 % |
| PERF-01 | p95 of 545–556 ms at 5 users against the declared 500 ms (EC-3 not met) | Single-row decrement with an audit-history write on SQLite takes about 300 ms for one user; five concurrent writers are serialised by the single write lock, so queueing adds to latency | High | PR-08 | Open: HOLD decision. Options: PostgreSQL, a faster storage tier, or a relaxed target agreed with the stakeholders (the target was not changed) |
| PERF-02 | Basic authentication adds about 40 ms at 5 users | Every Basic-authenticated request re-verifies the password hash | Low | PR-08 | Use token authentication (measured separately, both reported) |
