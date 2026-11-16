"""Critical module: complete MCC (all 32 rows) + MC/DC subset for BR-2 in StockAdjustmentItemSerializer.validate_pk.
Expected outcomes come from tools/mcdc.py (derived from the requirement), not from the code under test."""
import os, sys
import pytest
from rest_framework.exceptions import ValidationError

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'tools')))
import mcdc  # noqa: E402

pytestmark = pytest.mark.django_db
TABLE = mcdc.truth_table()
MCDC_SET, _ = mcdc.minimal_mcdc_set(TABLE)


def _id(n, row):
    return f"MCC{n:02d}-" + ''.join('T' if v else 'F' for v in row)


@pytest.mark.parametrize('n,row,expected_reject', TABLE, ids=[_id(n, r) for n, r, _ in TABLE])
@pytest.mark.req('BR-2', 'FR-04')
@pytest.mark.risk('PR-03')
def test_mcc_row(n, row, expected_reject, item, markers, monkeypatch):
    from stock.serializers import StockAdjustmentItemSerializer
    allow, so, bt, cu, cb = row
    monkeypatch.setattr('stock.serializers.get_global_setting', lambda *a, **k: allow)
    if so: item.sales_order = markers.sales_order
    if bt: item.belongs_to = markers.parent
    if cu: item.customer = markers.customer
    if cb: item.consumed_by = markers.build
    ser = StockAdjustmentItemSerializer(require_in_stock=True)
    if expected_reject:
        with pytest.raises(ValidationError, match='not in stock'):
            ser.validate_pk(item)
    else:
        assert ser.validate_pk(item) is item


def test_mcdc_set_is_a_subset_of_mcc_and_minimal():
    assert len(MCDC_SET) == len(mcdc.CONDITIONS) + 1 and set(MCDC_SET) <= {n for n, _, _ in TABLE}


def test_every_condition_has_an_independence_pair_in_the_mcdc_set():
    pairs = mcdc.independence_pairs(TABLE)
    s = set(MCDC_SET)
    for c in mcdc.CONDITIONS:
        assert any(a in s and b in s for a, b in pairs[c]), c


# --- six basis paths of V(G)=6 (docs/STATIC_ANALYSIS.md §2), one test each through the real function
@pytest.mark.parametrize('name,req_in_stock,allow,set_belongs_to,expect', [
    ('path1 p1F,p4F -> return',            None,  False, False, 'ok'),
    ('path2 p1F,p4T,p5F -> return',        False, False, False, 'ok'),   # item not in stock (qty 0) set below
    ('path3 p1F,p4T,p5T -> raise B',       False, False, False, 'raiseB'),
    ('path4 p1T,p2F -> return',            True,  True,  True,  'ok'),
    ('path5 p1T,p2T,p3F -> return',        True,  False, False, 'ok'),
    ('path6 p1T,p2T,p3T -> raise A',       True,  False, True,  'raiseA'),
])
@pytest.mark.risk('PR-03')
def test_basis_paths(name, req_in_stock, allow, set_belongs_to, expect, make_item, markers, monkeypatch):
    from stock.serializers import StockAdjustmentItemSerializer
    monkeypatch.setattr('stock.serializers.get_global_setting', lambda *a, **k: allow)
    # path2 needs is_in_stock() False with require_in_stock=False -> empty item; path3 needs True -> stocked item
    it = make_item(0 if name.startswith('path2') else 10)
    if set_belongs_to:
        it.belongs_to = markers.parent
    ser = StockAdjustmentItemSerializer(require_in_stock=req_in_stock)
    if expect == 'ok':
        assert ser.validate_pk(it) is it
    else:
        with pytest.raises(ValidationError, match='not in stock' if expect == 'raiseA' else 'already in stock'):
            ser.validate_pk(it)
