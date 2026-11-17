#!/usr/bin/env bash
# Prepare an isolated working copy for mutmut: the backend source + our unit tests + a mutmut config (nothing in upstream/ is modified).
set -euo pipefail
. "$(dirname "$0")/env.sh"
W="$ROOT/mutation/work"; rm -rf "$W"; mkdir -p "$W"
rsync -a --exclude '__pycache__' --exclude '_testfolder' --exclude 'web/static' "$ROOT/upstream/src/backend/InvenTree/" "$W/"
mkdir -p "$W/tests_team" && rsync -a --exclude '__pycache__' "$ROOT/tests/team/unit/" "$W/tests_team/unit/" && cp "$ROOT/tests/team/conftest.py" "$W/tests_team/conftest.py"
cp -r "$ROOT/tools" "$W/tools"; rm -rf "$ROOT/mutation/tools"; cp -r "$ROOT/tools" "$ROOT/mutation/tools"
cat > "$W/pytest.ini" <<CFG
[pytest]
DJANGO_SETTINGS_MODULE = InvenTree.settings
pythonpath = .
addopts = -p no:cacheprovider --no-migrations -q
markers =
    req(ids): x
    risk(ids): x
    seq(name): x
    corrupts_db: x
CFG
# mutmut reads list options from setup.cfg ONE PER LINE (comma-separated values are taken as a single string; the first attempt, which used commas, copied nothing and made the coverage run fail with exit code 1)
ALSO=$(cd "$W" && ls -A | grep -v -E '^(mutants|setup.cfg|\.gitignore)$' | sed 's/^/    /')
{
  echo "[mutmut]"
  echo "source_paths ="
  echo "    stock/serializers.py"
  echo "    stock/models.py"
  echo "pytest_add_cli_args_test_selection ="
  echo "    tests_team/unit"
  echo "mutate_only_covered_lines = true"
  echo "also_copy ="
  echo "$ALSO"
} > "$W/setup.cfg"
echo "work dir ready: $W ($(du -sh "$W" | cut -f1))"
