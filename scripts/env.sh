# Source me: shared environment for all scripts (repo-relative, reproducible)
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export ROOT
export INVENTREE_DB_ENGINE=sqlite3
export INVENTREE_DB_NAME="$ROOT/data/inventree.sqlite3"
export INVENTREE_MEDIA_ROOT="$ROOT/data/media"
export INVENTREE_STATIC_ROOT="$ROOT/data/static"
export INVENTREE_BACKUP_DIR="$ROOT/data/backup"
export INVENTREE_CONFIG_FILE="$ROOT/data/config.yaml"
export INVENTREE_SECRET_KEY_FILE="$ROOT/data/secret_key.txt"
export INVENTREE_SITE_URL="http://127.0.0.1:8000"
export INVENTREE_DEBUG=False
export INVENTREE_LOG_LEVEL=WARNING
export INVENTREE_PLUGINS_ENABLED=False
export INVENTREE_PLUGIN_FILE="$ROOT/data/plugins.txt"
export INVENTREE_ADMIN_USER=admin
export INVENTREE_ADMIN_PASSWORD=admin12345
export INVENTREE_ADMIN_EMAIL=admin@example.test
export PY="${PYTHON:-$ROOT/.venv/bin/python}"
export MANAGE="$PY $ROOT/upstream/src/backend/InvenTree/manage.py"
