"""Shared fixtures for own unit tests (tests/team/unit). Uses the real InvenTree models against a throw-away test DB."""
import os
import pytest

# Environment for a hermetic run (never touches data/inventree.sqlite3)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
os.environ.setdefault('INVENTREE_DB_ENGINE', 'sqlite3')
os.environ.setdefault('INVENTREE_DB_NAME', os.path.join(ROOT, 'data', 'unit_test.sqlite3'))
os.environ.setdefault('INVENTREE_MEDIA_ROOT', os.path.join(ROOT, 'data', 'media'))
os.environ.setdefault('INVENTREE_STATIC_ROOT', os.path.join(ROOT, 'data', 'static'))
os.environ.setdefault('INVENTREE_BACKUP_DIR', os.path.join(ROOT, 'data', 'backup'))
os.environ.setdefault('INVENTREE_CONFIG_FILE', os.path.join(ROOT, 'data', 'config.yaml'))
os.environ.setdefault('INVENTREE_SECRET_KEY_FILE', os.path.join(ROOT, 'data', 'secret_key.txt'))
os.environ.setdefault('INVENTREE_PLUGINS_ENABLED', 'False')
os.environ.setdefault('INVENTREE_PLUGIN_FILE', os.path.join(ROOT, 'data', 'plugins.txt'))
os.environ.setdefault('INVENTREE_LOG_LEVEL', 'WARNING')
os.environ.setdefault('TESTING', '1')


# --------------------------------------------------------------------------- fixtures
from decimal import Decimal
from types import SimpleNamespace

ADD, REMOVE = 11, 12  # StockHistoryCode.STOCK_ADD / STOCK_REMOVE


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user('tester', password='pw')


@pytest.fixture
def request_ctx(user):
    """Minimal DRF-style serializer context."""
    return {'request': SimpleNamespace(user=user)}


@pytest.fixture
def part(db):
    from part.models import Part, PartCategory

    cat = PartCategory.objects.create(name='Peripherals')
    return Part.objects.create(name='Keyboard', description='Synthetic keyboard', category=cat)


@pytest.fixture
def make_item(part):
    """Factory for StockItems (delete_on_deplete False unless stated: deterministic like the seed)."""
    from stock.models import StockItem

    def _make(quantity=10, **kw):
        kw.setdefault('delete_on_deplete', False)
        return StockItem.objects.create(part=part, quantity=Decimal(str(quantity)), **kw)

    return _make


@pytest.fixture
def item(make_item):
    return make_item(10)


@pytest.fixture
def markers(db, part, make_item):
    """Real related objects used to make an item non-adjustable (BR-2 conditions)."""
    from build.models import Build
    from company.models import Company
    from order.models import SalesOrder
    from part.models import Part

    asm = Part.objects.create(name='Assembly', description='asm', category=part.category, assembly=True)
    cust = Company.objects.create(name='Customer', is_customer=True)
    return SimpleNamespace(
        sales_order=SalesOrder.objects.create(customer=cust, reference='SO-0001'),
        customer=cust,
        build=Build.objects.create(part=asm, quantity=1, reference='BO-0001', title='b'),
        parent=make_item(1),
    )


def history(item, code):
    """Audit-log entries (STOCK_ADD=11 / STOCK_REMOVE=12) for an item."""
    from audit.models import AuditLogEntry

    return list(AuditLogEntry.objects.filter(object_pk=str(item.pk), event_type=code).order_by('pk'))


def reload(item):
    from stock.models import StockItem

    return StockItem.objects.filter(pk=item.pk).first()
