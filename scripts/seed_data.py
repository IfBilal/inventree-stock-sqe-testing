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
    for rs in RuleSet.objects.filter(group=g):
        on = rs.name == 'stock'
        rs.can_view = on; rs.can_add = on and stock_rights.get('add', False)
        rs.can_change = on and stock_rights.get('change', False); rs.can_delete = on and stock_rights.get('delete', False)
        rs.save()
        if on:  # view for stock always; parts/locations are needed to render UI
            rs.can_view = True; rs.save()
    for rs in RuleSet.objects.filter(group=g, name__in=['part', 'stock_location', 'part_category']):
        rs.can_view = True; rs.save()
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
        StockItem.objects.create(part=p, location=loc, quantity=qty)
print('SEED_OK users=%d parts=%d items=%d' % (User.objects.count(), Part.objects.count(), StockItem.objects.count()))
