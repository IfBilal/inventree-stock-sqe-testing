"""SEC-01 / SEC-02 fixes: Content-Security-Policy header and SameSite cookie default."""
from django.http import HttpResponse
from django.test import RequestFactory, override_settings


def _call(path, response=None):
    from InvenTree.middleware import ContentSecurityPolicyMiddleware
    mw = ContentSecurityPolicyMiddleware(lambda request: response or HttpResponse('ok'))
    return mw(RequestFactory().get(path))


def test_csp_header_is_added_with_the_default_policy():
    r = _call('/web/')
    csp = r.headers['Content-Security-Policy']
    assert "default-src 'self'" in csp and "script-src 'self'" in csp and "frame-ancestors 'self'" in csp and "object-src 'none'" in csp
    assert 'unsafe-inline' not in csp.split('script-src')[1].split(';')[0]          # no inline script


def test_csp_header_is_not_added_for_the_admin_and_api_documentation():
    for path in ('/admin/login/', '/api/schema/', '/api/docs/'):
        assert 'Content-Security-Policy' not in _call(path).headers


def test_an_existing_policy_of_the_response_is_kept():
    r = HttpResponse('ok')
    r.headers['Content-Security-Policy'] = "default-src 'none'"
    assert _call('/web/', r).headers['Content-Security-Policy'] == "default-src 'none'"


@override_settings(CONTENT_SECURITY_POLICY="default-src 'self' https://cdn.example")
def test_the_policy_can_be_replaced_by_a_setting():
    assert _call('/web/').headers['Content-Security-Policy'] == "default-src 'self' https://cdn.example"


def test_session_and_csrf_cookies_default_to_samesite_lax():
    from django.conf import settings
    assert settings.SESSION_COOKIE_SAMESITE == 'Lax' and settings.CSRF_COOKIE_SAMESITE == 'Lax'


def test_sqlite_uses_immediate_transactions_with_a_busy_timeout():
    """DEF-06 fix: concurrent writers wait for the write lock instead of failing with 'database is locked' (HTTP 500)."""
    from django.conf import settings
    db = settings.DATABASES['default']
    assert db['ENGINE'] == 'django.db.backends.sqlite3'
    assert db['OPTIONS']['transaction_mode'] == 'IMMEDIATE' and db['OPTIONS']['timeout'] >= 30
