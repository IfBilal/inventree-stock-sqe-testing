"""Serializer-level business logic for WF-A/WF-B (FR-03, FR-04, FR-07, FR-09..FR-10, BR-1)."""
from decimal import Decimal
import pytest
from rest_framework.exceptions import ValidationError
from conftest import ADD, REMOVE, history, reload

pytestmark = pytest.mark.django_db


def _add(data, ctx):
    from stock.serializers import StockAddSerializer
    s = StockAddSerializer(data=data, context=ctx); s.is_valid(raise_exception=True); return s.save()


def _remove(data, ctx):
    from stock.serializers import StockRemoveSerializer
    s = StockRemoveSerializer(data=data, context=ctx); s.is_valid(raise_exception=True); return s.save()


def payload(item, q, **extra):
    return {'items': [{'pk': item.pk, 'quantity': q, **extra}]}


# ------------------------------------------------------------- validate_quantity (direct calls)
@pytest.mark.req('FR-03a')
def test_validate_quantity_negative_branch_directly():
    from stock.serializers import StockAdjustmentItemSerializer as S
    with pytest.raises(ValidationError):
        S().validate_quantity(Decimal('-1'))      # dead code via DRF (min_value) but reachable by direct call


def test_validate_quantity_require_non_zero_rejects_zero():
    from stock.serializers import StockAdjustmentItemSerializer as S
    with pytest.raises(ValidationError):
        S(require_non_zero=True).validate_quantity(Decimal('0'))


def test_validate_quantity_require_non_zero_accepts_positive():
    from stock.serializers import StockAdjustmentItemSerializer as S
    assert S(require_non_zero=True).validate_quantity(Decimal('1')) == 1


def test_validate_quantity_accepts_zero_when_not_required():
    from stock.serializers import StockAdjustmentItemSerializer as S
    assert S().validate_quantity(Decimal('0')) == 0


# validate_pk branches (require_in_stock True/False/None) are covered once, as the six basis paths, in test_validate_pk_mcc.py

# ------------------------------------------------------------- to_internal_value / validate
def test_empty_items_list_rejected(request_ctx):
    with pytest.raises(ValidationError, match='list of stock items'):
        _add({'items': []}, request_ctx)


@pytest.mark.req('FR-04')
def test_non_integer_pk_is_a_validation_error_not_a_crash(request_ctx):
    with pytest.raises(ValidationError):
        _add({'items': [{'pk': 'abc', 'quantity': 1}]}, request_ctx)


def test_missing_items_key_rejected(request_ctx):
    with pytest.raises(ValidationError):
        _add({}, request_ctx)


def test_unknown_pk_rejected(request_ctx):
    with pytest.raises(ValidationError):
        _add({'items': [{'pk': 999999, 'quantity': 1}]}, request_ctx)


def test_items_processed_in_pk_order(make_item, request_ctx):
    from stock.serializers import StockAddSerializer
    a, b = make_item(1), make_item(1)
    s = StockAddSerializer(data={'items': [{'pk': b.pk, 'quantity': 1}, {'pk': a.pk, 'quantity': 1}]}, context=request_ctx)
    s.is_valid(raise_exception=True)
    assert [i['pk'].pk for i in s.validated_data['items']] == sorted([a.pk, b.pk])


# ------------------------------------------------------------- save(): add
@pytest.mark.req('FR-01', 'FR-02')
def test_add_serializer_applies_and_records(item, request_ctx):
    _add(payload(item, 5) | {'notes': 'n'}, request_ctx)
    assert reload(item).quantity == 15 and len(history(item, ADD)) == 1


def _direct_save(cls, item, quantity, ctx):
    """Call save() with a pre-validated payload (bypasses validation), independent of how validation treats the value."""
    s = cls(data={}, context=ctx)
    s._validated_data = {'items': [{'pk': item, 'quantity': quantity}], 'notes': ''}
    s._errors = {}
    return s.save()


@pytest.mark.parametrize('cls_name', ['StockAddSerializer', 'StockRemoveSerializer'])
def test_save_defensively_skips_non_positive_quantities(cls_name, item, request_ctx):
    """Covers the defensive `quantity <= 0: continue` branch directly (baseline-independent: still valid after the DEF-02 fix)."""
    import stock.serializers as ser
    _direct_save(getattr(ser, cls_name), item, Decimal(0), request_ctx)
    assert reload(item).quantity == 10 and history(item, ADD) == [] and history(item, REMOVE) == []


def test_add_serializer_passes_optional_fields(item, request_ctx):
    _add(payload(item, 1, batch='B5', packaging='tray'), request_ctx)
    got = reload(item)
    assert (got.batch, got.packaging) == ('B5', 'tray')


def test_add_serializer_blank_optional_fields_keep_existing_values(make_item, request_ctx):
    it = make_item(10, batch='KEEP', packaging='crate')
    _add(payload(it, 1, batch='', packaging=''), request_ctx)
    got = reload(it)
    assert (got.batch, got.packaging) == ('KEEP', 'crate')


@pytest.mark.req('FR-10')
def test_add_is_atomic_when_a_later_item_is_invalid(item, make_item, request_ctx):
    with pytest.raises(ValidationError):
        _add({'items': [{'pk': item.pk, 'quantity': 1}, {'pk': 999999, 'quantity': 1}]}, request_ctx)
    assert reload(item).quantity == 10


# ------------------------------------------------------------- save(): remove
@pytest.mark.req('FR-05', 'FR-06')
def test_remove_serializer_applies_and_records(item, request_ctx):
    _remove(payload(item, 4), request_ctx)
    assert reload(item).quantity == 6 and len(history(item, REMOVE)) == 1


def test_remove_serializer_passes_optional_fields(item, request_ctx):
    _remove(payload(item, 1, batch='B6', packaging='crate'), request_ctx)
    got = reload(item)
    assert (got.batch, got.packaging) == ('B6', 'crate')


def test_remove_serializer_blank_optional_fields_keep_existing_values(make_item, request_ctx):
    it = make_item(10, batch='KEEP', packaging='crate')
    _remove(payload(it, 1, batch='', packaging=''), request_ctx)
    got = reload(it)
    assert (got.batch, got.packaging) == ('KEEP', 'crate')


# ------------------------------------------------------------- DEF-01..04: EXPECTED behaviour (failed on the baseline; fixed in PRs #13 and the validation fix)
@pytest.mark.req('FR-07', 'BR-1')
@pytest.mark.risk('PR-01')
def test_expected_over_removal_is_rejected_and_quantity_unchanged(item, request_ctx):
    with pytest.raises(ValidationError):
        _remove(payload(item, 11), request_ctx)
    assert reload(item).quantity == 10 and history(item, REMOVE) == []


@pytest.mark.req('FR-03b')
@pytest.mark.risk('PR-04')
@pytest.mark.parametrize('call', [_add, _remove], ids=['add', 'remove'])
def test_expected_zero_quantity_is_rejected(item, request_ctx, call):
    with pytest.raises(ValidationError):
        call(payload(item, 0), request_ctx)


@pytest.mark.req('BR-1')
@pytest.mark.risk('PR-04')
def test_expected_add_exceeding_representable_total_is_rejected(item, request_ctx):
    with pytest.raises(ValidationError):
        _add(payload(item, '9999999999.99999'), request_ctx)


@pytest.mark.req('FR-03a')
@pytest.mark.risk('PR-04')
@pytest.mark.parametrize('bad', [None, 'abc', 5, {'a': 1}], ids=['null', 'string', 'int', 'dict'])
def test_expected_malformed_items_is_a_validation_error_not_a_crash(request_ctx, bad):
    with pytest.raises(ValidationError):
        _add({'items': bad}, request_ctx)
