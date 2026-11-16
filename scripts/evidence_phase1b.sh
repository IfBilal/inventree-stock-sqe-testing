#!/usr/bin/env bash
# Over-removal, zero quantity and overflow observations (run after a fresh reset; mutates state).
set -uo pipefail
. "$(dirname "$0")/env.sh"; B=http://127.0.0.1:8000/api; H='Content-Type: application/json'
call(){ curl -s -u manager:manager12345 -X POST "$B$1" -H "$H" -d "$2" -w "  -> HTTP %{http_code}\n"; }
qty(){ curl -s -u admin:admin12345 "$B/stock/$1/" -w "\n" | python3 -c "import sys,json
t=sys.stdin.read(); 
try:
  d=json.loads(t.rsplit('\n',2)[0] if t.strip().endswith('}') else t); print('  qty(pk=$1)=',d.get('quantity','<none>'),d.get('detail',''))
except Exception as e: print('  GET pk=$1 not JSON/err:',t[:120])"; }
echo "## OVER-REMOVAL: Keyboard pk1 qty 10, delete_on_deplete=False, remove 100"; qty 1; call /stock/remove/ '{"items":[{"pk":1,"quantity":100}]}'; qty 1
echo "## ZERO: Mouse pk2 qty 25, add 0 and remove 0"; call /stock/add/ '{"items":[{"pk":2,"quantity":0}]}'; call /stock/remove/ '{"items":[{"pk":2,"quantity":0}]}'; qty 2
echo "## NEGATIVE: add -1"; call /stock/add/ '{"items":[{"pk":2,"quantity":-1}]}'; qty 2
echo "## OVERFLOW: Mouse pk2 add 9999999999.99999 (max per request) twice"; call /stock/add/ '{"items":[{"pk":2,"quantity":9999999999.99999}]}'; qty 2; call /stock/add/ '{"items":[{"pk":2,"quantity":9999999999.99999}]}'; qty 2
