"""Boundary value analysis (3-point: just below, at, just above) and equivalence partitions at serializer level (BR-1, FR-03, FR-05, FR-07)."""
from decimal import Decimal
import pytest
from rest_framework.exceptions import ValidationError
from conftest import REMOVE, history, reload
from test_adjustment_serializers import _add, _remove, payload

pytestmark = pytest.mark.django_db
AVAILABLE = 10   # quantity of the `item` fixture


# ---- BR-1 remove limit: just below / at / just above `available`
@pytest.mark.req('BR-1', 'FR-05')
@pytest.mark.risk('PR-01')
@pytest.mark.parametrize('q, remaining', [('9.99999', '0.00001'), ('10', '0')], ids=['just-below-limit', 'at-limit'])
def test_remove_below_and_at_limit_is_accepted(item, request_ctx, q, remaining):
    _remove(payload(item, q), request_ctx)
    assert reload(item).quantity == Decimal(remaining)


@pytest.mark.req('BR-1', 'FR-07')
@pytest.mark.risk('PR-01')
@pytest.mark.xfail(strict=True, raises=pytest.fail.Exception, reason='DEF-01: just-above-limit removal is clamped (baseline)')
def test_remove_just_above_limit_is_rejected(item, request_ctx):
    with pytest.raises(ValidationError):
        _remove(payload(item, '10.00001'), request_ctx)
    assert reload(item).quantity == AVAILABLE


# ---- BR-1 lower bound for add/remove: just below 0 (invalid), at 0 (invalid by A-2), just above 0 (valid)
@pytest.mark.parametrize('call', [_add, _remove], ids=['add', 'remove'])
def test_just_below_zero_is_rejected(item, request_ctx, call):
    with pytest.raises(ValidationError):
        call(payload(item, '-0.00001'), request_ctx)
    assert reload(item).quantity == AVAILABLE


@pytest.mark.parametrize('call, expected', [(_add, '10.00001'), (_remove, '9.99999')], ids=['add', 'remove'])
def test_just_above_zero_is_accepted(item, request_ctx, call, expected):
    call(payload(item, '0.00001'), request_ctx)
    assert reload(item).quantity == Decimal(expected)


# ---- BR-1 upper bound per request: 9 999 999 999.99999 (max_digits=15, decimal_places=5)
@pytest.mark.req('BR-1')
@pytest.mark.risk('PR-04')
@pytest.mark.parametrize('q', ['9999999999.99998', '9999999999.99999'], ids=['just-below-max', 'at-max'])
def test_add_at_and_below_max_is_accepted_on_empty_item(make_item, request_ctx, q):
    z = make_item(0)
    _add(payload(z, q), request_ctx)
    assert reload(z).quantity == Decimal(q)


@pytest.mark.req('BR-1')
@pytest.mark.risk('PR-04')
def test_add_just_above_max_is_rejected(make_item, request_ctx):
    z = make_item(0)
    with pytest.raises(ValidationError):
        _add(payload(z, '10000000000'), request_ctx)
    assert reload(z).quantity == 0


# ---- equivalence partitions of the `quantity` input (one invalid value per test)
@pytest.mark.req('FR-03a')
@pytest.mark.parametrize('bad', ['abc', '', None, '1.234567', '1e400', 'NaN'], ids=['text', 'blank', 'null', '6-decimals', 'huge-exponent', 'nan'])
@pytest.mark.parametrize('call', [_add, _remove], ids=['add', 'remove'])
def test_invalid_quantity_partitions_are_rejected(item, request_ctx, call, bad):
    with pytest.raises(ValidationError):
        call(payload(item, bad), request_ctx)
    assert reload(item).quantity == AVAILABLE and history(item, REMOVE) == []


@pytest.mark.parametrize('good', ['1', 1, 1.5, '2.50000', '0.5'], ids=['int-str', 'int', 'float', 'five-decimals', 'fraction'])
def test_valid_quantity_partitions_are_accepted(item, request_ctx, good):
    _add(payload(item, good), request_ctx)
    assert reload(item).quantity == Decimal(AVAILABLE) + Decimal(str(good))


# ---- BR-1 resulting-total bound on a NON-empty item (item = 10, max = 9 999 999 999.99999): just below / at / above
@pytest.mark.req('BR-1')
@pytest.mark.risk('PR-04')
@pytest.mark.parametrize('q, total', [('9999999989.99998', '9999999999.99998'), ('9999999989.99999', '9999999999.99999')],
                         ids=['total-just-below-max', 'total-at-max'])
def test_add_with_total_below_and_at_max_is_accepted(item, request_ctx, q, total):
    _add(payload(item, q), request_ctx)
    assert reload(item).quantity == Decimal(total)


@pytest.mark.req('BR-1')
@pytest.mark.risk('PR-04')
@pytest.mark.xfail(strict=True, raises=pytest.fail.Exception, reason='DEF-03: total just above the maximum is accepted (baseline)')
def test_add_with_total_just_above_max_is_rejected(item, request_ctx):
    with pytest.raises(ValidationError):
        _add(payload(item, '9999999990'), request_ctx)
    assert reload(item).quantity == AVAILABLE
