"""Deterministic synthetic seed data. Run via: manage.py shell < scripts/seed_data.py"""
from django.contrib.auth.models import Group, User
from part.models import Part, PartCategory
from stock.models import StockItem, StockLocation
from users.models import Owner, RuleSet, UserProfile
from users.tasks import update_group_roles

def mk_user(name, password, group=None, superuser=False):
    u, _ = User.objects.get_or_create(username=name, defaults={'email': f'{name}@example.test'})
    u.set_password(password); u.is_superuser = superuser; u.is_staff = superuser; u.is_active = True; u.save()
    UserProfile.objects.get_or_create(user=u); Owner.create(obj=u)  # 'shell' is treated as read-only: signal skips profile
    if group: u.groups.add(group)
    return u

def mk_group(name, stock_rights):
    g, _ = Group.objects.get_or_create(name=name)
    Owner.create(obj=g)
    # Explicit RuleSet rows (the 'shell' command skips the signals that normally create them)
    for role in ('stock', 'part', 'stock_location', 'part_category'):
        rs, _ = RuleSet.objects.get_or_create(group=g, name=role)
        rs.can_view = True
        is_stock = role == 'stock'
        rs.can_add = is_stock and stock_rights.get('add', False)
        rs.can_change = is_stock and stock_rights.get('change', False)
        rs.can_delete = is_stock and stock_rights.get('delete', False)
        rs.save()
    update_group_roles(g)
    return g

mgr = mk_group('stock_manager', {'add': True, 'change': True, 'delete': True})
viewer = mk_group('stock_viewer', {})
mk_user('admin', 'admin12345', superuser=True)
mk_user('manager', 'manager12345', group=mgr)
mk_user('viewer', 'viewer12345', group=viewer)

cat, _ = PartCategory.objects.get_or_create(name='Peripherals', defaults={'description': 'Synthetic category'})
loc, _ = StockLocation.objects.get_or_create(name='Main Warehouse', defaults={'description': 'Synthetic location'})
for name, qty in [('Keyboard', 10), ('Mouse', 25), ('Monitor', 0)]:
    p, _ = Part.objects.get_or_create(name=name, defaults={'description': f'{name} (synthetic)', 'category': cat, 'component': True, 'purchaseable': True})
    if not StockItem.objects.filter(part=p).exists():
        StockItem.objects.create(part=p, location=loc, quantity=qty, delete_on_deplete=False)  # explicit: deterministic baseline
print('SEED_OK users=%d parts=%d items=%d' % (User.objects.count(), Part.objects.count(), StockItem.objects.count()))
