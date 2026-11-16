#!/usr/bin/env bash
# Reproduces the Phase 1 empirical observations (roles, over-removal, zero quantity, overflow) from a clean reset.
set -uo pipefail
. "$(dirname "$0")/env.sh"; B=http://127.0.0.1:8000/api; H='Content-Type: application/json'
call(){ # user method path body
  curl -s -u "$1" -X "$2" "$B$3" -H "$H" ${4:+-d "$4"} -w "  -> HTTP %{http_code}\n"; }
qty(){ curl -s -u admin:admin12345 "$B/stock/$1/" | python3 -c "import sys,json;d=json.load(sys.stdin);print('  qty(pk=$1)=',d.get('quantity','<no quantity>'),d.get('detail',''))"; }
hist(){ $MANAGE shell -c "
from audit.models import AuditLogEntry
print('  audit entries (event_type,additional_data):', list(AuditLogEntry.objects.filter(event_type__in=[11,12]).values_list('event_type','additional_data')))" 2>&1 | tail -1; }
echo "## ROLES (add/remove on pk1 qty 1)"
for u in admin:admin12345 manager:manager12345 viewer:viewer12345; do echo "# $u"; call $u POST /stock/add/ '{"items":[{"pk":1,"quantity":1}]}'; call $u POST /stock/remove/ '{"items":[{"pk":1,"quantity":1}]}'; done
echo "# unauthenticated"; curl -s -X POST $B/stock/add/ -H "$H" -d '{"items":[{"pk":1,"quantity":1}]}' -w "  -> HTTP %{http_code}\n"
