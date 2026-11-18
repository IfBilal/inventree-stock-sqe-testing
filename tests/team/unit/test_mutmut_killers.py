"""Tests written after the real mutmut run (docs/MUTATION.md §2b): they kill survivors that exposed real weaknesses of the first suite —
the serializers' notes/actor/extra-field hand-over, the exact validation messages, the create-event of save(), serial_int and clean() boundaries."""
from decimal import Decimal
import pytest
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError
from conftest import ADD, REMOVE, history, reload
from test_adjustment_serializers import _add, _remove, payload

pytestmark = pytest.mark.django_db


# ------------------------------------------------------------------ serializer save(): notes, actor, entries after a skipped entry
@pytest.mark.parametrize('call,code,qty_after', [(_add, ADD, 15), (_remove, REMOVE, 5)])
@pytest.mark.req('FR-02', 'FR-06')
def test_serializer_save_records_notes_and_the_acting_user(call, code, qty_after, item, request_ctx, user):
    call(payload(item, 5) | {'notes': 'delivery 42'}, request_ctx)
    e = history(item, code)
    assert len(e) == 1 and e[0].notes == 'delivery 42' and e[0].actor_username == user.username
    assert reload(item).quantity == qty_after


@pytest.mark.parametrize('call,code', [(_add, ADD), (_remove, REMOVE)])
def test_serializer_save_without_notes_records_empty_notes(call, code, item, request_ctx):
    call(payload(item, 1), request_ctx)
    assert history(item, code)[0].notes in ('', None) and not history(item, code)[0].notes


@pytest.mark.parametrize('cls,code', [('StockAddSerializer', ADD), ('StockRemoveSerializer', REMOVE)])
def test_a_zero_quantity_entry_is_skipped_and_the_next_entry_is_still_processed(cls, code, make_item, request_ctx):
    """Defensive branch of save(): zero is rejected at validation (DEF-02 fix), but a zero entry that reaches save() is skipped without ending the loop."""
    import stock.serializers as S
    a, b = make_item(10), make_item(10)
    ser = getattr(S, cls)(context=request_ctx)
    ser._validated_data = {'items': [{'pk': a, 'quantity': Decimal(0)}, {'pk': b, 'quantity': Decimal(2)}], 'notes': ''}
    ser.save()
    assert reload(a).quantity == 10 and history(a, code) == []
    assert reload(b).quantity == (12 if cls == 'StockAddSerializer' else 8) and len(history(b, code)) == 1


def test_serializer_save_passes_the_optional_item_fields_and_user_on(item, request_ctx, user, monkeypatch):
    """The model method receives the acting user, the notes and exactly the optional fields that were supplied (falsy ones are not passed)."""
    from stock.models import StockItem
    seen = []
    monkeypatch.setattr(StockItem, 'add_stock', lambda self, q, u, **kw: seen.append(('add', q, u, kw)) or True)
    monkeypatch.setattr(StockItem, 'take_stock', lambda self, q, u, **kw: seen.append(('take', q, u, kw)) or True)
    _add(payload(item, 1) | {'status': 50, 'batch': 'B-9', 'notes': 'n'}, request_ctx)
    _remove(payload(item, 1), request_ctx)
    assert seen[0][0] == 'add' and seen[0][2] is user and seen[0][3]['notes'] == 'n'
    assert seen[1][0] == 'take' and seen[1][2] is user and seen[1][3] == {'notes': ''}     # no optional field supplied -> none passed


# ------------------------------------------------------------------ exact validation messages
def _text(exc):
    return str(exc.value.detail[0]) if isinstance(exc.value.detail, list) else str(exc.value.detail)


def test_validate_quantity_messages_are_exact():
    from stock.serializers import StockAdjustmentItemSerializer as S
    with pytest.raises(ValidationError) as e:
        S(require_non_zero=True).validate_quantity(Decimal(0))
    assert _text(e) == 'Quantity must be greater than zero'
    with pytest.raises(ValidationError) as e:
        S().validate_quantity(Decimal(-1))
    assert _text(e) == 'Quantity must not be negative'


def test_validate_pk_in_stock_messages_are_exact(item, markers):
    from stock.serializers import StockAdjustmentItemSerializer as S
    out = item
    out.customer = markers.customer                  # not in stock (BR-2)
    with pytest.raises(ValidationError) as e:
        S(require_in_stock=True).validate_pk(out)
    assert _text(e) == 'Stock item is not in stock'
    item.customer = None
    with pytest.raises(ValidationError) as e:
        S(require_in_stock=False).validate_pk(item)
    assert _text(e) == 'Stock item is already in stock'


def test_empty_items_list_message_is_exact(request_ctx):
    with pytest.raises(ValidationError) as e:
        _add({'items': []}, request_ctx)
    assert str(e.value.detail['non_field_errors'][0]) == 'A list of stock items must be provided'


# ------------------------------------------------------------------ model: save() create event, serial_int, validate_unique, delete, is_in_stock
def test_creating_an_item_records_a_created_event(part, user):
    from audit.models import AuditLogEntry
    from stock.models import StockItem
    s = StockItem(part=part, quantity=Decimal('7'), status=10)
    s.save(user=user, notes='first')
    e = AuditLogEntry.objects.filter(object_pk=str(s.pk)).order_by('pk').first()
    assert e is not None and e.event_type == 1 or 'Created' in str(e)
    assert e.actor_username == user.username or e.actor_username is None


def test_a_save_with_only_notes_or_only_user_records_an_update_but_a_bare_save_does_not(item, user):
    from audit.models import AuditLogEntry
    n = lambda: AuditLogEntry.objects.filter(object_pk=str(item.pk)).count()
    base = n()
    item.save()                         # neither user nor notes -> no entry
    assert n() == base
    item.quantity = Decimal('11')
    item.save(notes='only notes')       # notes without user -> entry
    assert n() == base + 1
    item.quantity = Decimal('12')
    item.save(user=user)                # user without notes -> entry
    assert n() == base + 2


@pytest.mark.parametrize('serial,expected', [('1', 1), ('0', 0), ('-5', 5), ('12', 12), ('abc', 0), ('', 0), (None, 0)])
def test_serial_int_boundaries(part, serial, expected):
    from stock.models import StockItem
    s = StockItem(part=part, quantity=1 if serial else 5, serial=serial)
    s.update_serial_number()
    assert s.serial_int == expected


def test_duplicate_serial_error_is_reported_on_the_serial_field(part):
    from stock.models import StockItem
    StockItem.objects.create(part=part, quantity=1, serial='D9')
    with pytest.raises(DjangoValidationError) as e:
        StockItem.objects.create(part=part, quantity=1, serial='D9')
    assert 'serial' in e.value.message_dict


def test_deleting_a_serialized_item_is_refused_with_the_exact_message(make_item):
    from test_mutation_killers import _set_raw
    _set_raw('STOCK_ALLOW_DELETE_SERIALIZED', False)
    s = make_item(1, serial='DEL-1')
    with pytest.raises(DjangoValidationError) as e:
        s.delete()
    assert e.value.messages == ['Serialized stock items cannot be deleted']


def test_a_single_unit_is_in_stock(make_item):
    assert make_item(1).is_in_stock() is True


def test_item_cannot_belong_to_itself_error_names_the_field(item):
    item.belongs_to = item
    with pytest.raises(DjangoValidationError) as e:
        item.clean()
    assert e.value.message_dict == {'belongs_to': ['Item cannot belong to itself']}


def test_clean_strips_serial_and_batch_and_serial_quantity_rules(part):
    from stock.models import StockItem
    s = StockItem(part=part, quantity=1, serial='  A1  ', batch='  B7 ')
    s.clean()
    assert s.serial == 'A1' and s.batch == 'B7'
    s2 = StockItem(part=part, quantity=2, serial='A2')
    with pytest.raises(DjangoValidationError):
        s2.clean()                      # serialized items must have quantity 1
    s3 = StockItem(part=part, quantity=1, serial='A3', delete_on_deplete=True)
    s3.clean()
    assert s3.delete_on_deplete is False        # serialized items are never deleted on deplete


def test_clean_zero_quantity_serial_and_negative_quantity(part):
    from stock.models import StockItem
    with pytest.raises(DjangoValidationError):
        StockItem(part=part, quantity=-1).clean()
    s = StockItem(part=part, quantity=0, serial='Z1')
    s.clean()
    assert s.quantity == 1                      # a serialized item with quantity 0 is corrected to 1


# ---- StockItem.save(): who and what is recorded on create and on update (mutmut survivors #33, #34, #47, #49)
def test_create_entry_has_the_created_type_the_notes_and_the_actor(part, user):
    from audit.models import AuditLogEntry
    from stock.models import StockItem
    s = StockItem(part=part, quantity=Decimal('7'))
    s.save(user=user, notes='first')
    e = AuditLogEntry.objects.filter(object_pk=str(s.pk), event_type=1).get()
    assert e.notes == 'first' and e.actor_username == user.username


def test_update_entry_records_notes_without_user_and_user_without_notes(item, user):
    from audit.models import AuditLogEntry
    q = lambda: list(AuditLogEntry.objects.filter(object_pk=str(item.pk)).order_by('pk'))
    n0 = len(q())
    item.quantity = Decimal('11')
    item.save(notes='only notes')
    last = q()[-1]
    assert len(q()) == n0 + 1 and last.notes == 'only notes' and last.actor_username is None
    item.quantity = Decimal('12')
    item.save(user=user)
    last = q()[-1]
    assert last.actor_username == user.username and not last.notes
    item.quantity = Decimal('13')
    item.save(user=user, notes='both')
    last = q()[-1]
    assert last.actor_username == user.username and last.notes == 'both'


# ---- StockItem.clean(): exact error keys and messages; the serial-edit rule; trackable parts need integer quantities
def test_clean_negative_quantity_error_key_and_message(part):
    from stock.models import StockItem
    with pytest.raises(DjangoValidationError) as e:
        StockItem(part=part, quantity=-1).clean()
    assert e.value.message_dict == {'quantity': ['Quantity must be greater than zero']}


def test_clean_serial_with_quantity_above_one_error_keys_and_messages(part):
    from stock.models import StockItem
    with pytest.raises(DjangoValidationError) as e:
        StockItem(part=part, quantity=2, serial='S-2').clean()
    assert e.value.message_dict == {'quantity': ['Quantity must be 1 for item with a serial number'],
                                    'serial': ['Serial number cannot be set if quantity greater than 1']}


def test_clean_trackable_part_needs_an_integer_quantity(part):
    from stock.models import StockItem
    part.trackable = True
    part.save()
    StockItem(part=part, quantity=Decimal('3')).clean()                          # integer: accepted
    with pytest.raises(DjangoValidationError) as e:
        StockItem(part=part, quantity=Decimal('2.5')).clean()
    assert e.value.message_dict == {'quantity': ['Quantity must be integer value for trackable parts']}


def test_clean_blocks_editing_an_existing_serial_unless_the_setting_allows_it(part):
    from stock.models import StockItem
    from test_mutation_killers import _set_raw
    s = StockItem.objects.create(part=part, quantity=1, serial='ED-1')
    _set_raw('STOCK_ALLOW_EDIT_SERIAL', False)
    s.serial = 'ED-2'
    with pytest.raises(DjangoValidationError) as e:
        s.clean()
    assert 'serial' in e.value.message_dict and 'already been assigned' in e.value.message_dict['serial'][0]
    s.serial = 'ED-1'
    s.clean()                                                                    # unchanged serial: fine
    _set_raw('STOCK_ALLOW_EDIT_SERIAL', True)
    s.serial = 'ED-3'
    s.clean()                                                                    # allowed by the setting
    new = StockItem(part=part, quantity=1, serial='NEW-1')
    _set_raw('STOCK_ALLOW_EDIT_SERIAL', False)
    new.clean()                                                                  # a new item (no pk) is never blocked


def test_saving_an_existing_serialized_item_again_does_not_conflict_with_itself(part):
    """validate_unique passes the instance so the item is excluded from its own duplicate check."""
    from stock.models import StockItem
    s = StockItem.objects.create(part=part, quantity=1, serial='RS-1')
    s.save()                                    # must not raise "duplicate serial"
    s.refresh_from_db()
    assert s.serial == 'RS-1'
