#!/usr/bin/env bash
# OWASP ZAP in SAFE mode (passive only: no spider, no active scan) as an intercepting proxy while the Playwright tests run BOTH workflows
# (UC-01 add and UC-02 remove, all flows). Saves the launch command, the mode, message counts, the POST requests of both workflows and all alerts to evidence/security/.
# Needs ZAP 2.17.0 in ~/tools/ZAP_2.17.0 and JDK 21 in ~/tools/jdk21 (see docs/TOOL_VERSIONS.md).
set -euo pipefail
. "$(dirname "$0")/env.sh"
OUT="$ROOT/evidence/security"; mkdir -p "$OUT"
export JAVA_HOME="$HOME/tools/jdk21" PATH="$HOME/tools/jdk21/bin:$PATH"
LAUNCH='./zap.sh -daemon -host 127.0.0.1 -port 8090 -config api.disablekey=true -config api.addrs.addr.name=127.0.0.1 -config api.addrs.addr.regex=false'
echo "$LAUNCH" > "$OUT/zap_launch_command.txt"
(cd "$HOME/tools/ZAP_2.17.0" && nohup $LAUNCH > "$OUT/zap_daemon.log" 2>&1 &)
for i in $(seq 1 60); do curl -s http://127.0.0.1:8090/JSON/core/view/version/ | grep -q version && break; sleep 3; done
Z=http://127.0.0.1:8090/JSON
curl -s "$Z/core/action/setMode/?mode=safe" > /dev/null
curl -s "$Z/core/view/mode/" > "$OUT/zap_mode.json"
curl -s "$Z/core/view/version/" > "$OUT/zap_version.json"
curl -s "$Z/core/action/newSession/?name=sqe&overwrite=true" > /dev/null
cd "$ROOT/tests/team"
E2E_PROXY=http://127.0.0.1:8090 npx playwright test e2e/uc01_add_stock.spec.ts e2e/uc02_remove_stock.spec.ts --reporter=json > "$OUT/zap_playwright_run.json"
for i in $(seq 1 60); do n=$(curl -s "$Z/pscan/view/recordsToScan/" | python3 -c "import sys,json;print(json.load(sys.stdin)['recordsToScan'])"); [ "$n" = "0" ] && break; sleep 3; done
curl -s "$Z/core/view/numberOfMessages/" > "$OUT/zap_number_of_messages.json"
curl -s "$Z/alert/view/alerts/?baseurl=http://127.0.0.1:8000&start=0&count=1000" > "$OUT/zap_alerts_raw.json"
curl -s "$Z/core/view/urls/?baseurl=http://127.0.0.1:8000" > "$OUT/zap_urls.json"
curl -s "$Z/core/view/messages/?baseurl=http://127.0.0.1:8000&start=0&count=5000" > "$OUT/zap_messages_raw.json"
"$PY" - <<PYEOF
import json, collections
m = json.load(open("$OUT/zap_messages_raw.json"))["messages"]
rows = []
for x in m:
    line = x["requestHeader"].split("\r\n")[0]
    if line.startswith("POST") and ("/api/stock/add/" in line or "/api/stock/remove/" in line):
        rows.append({"id": x["id"], "request": line, "status": x["responseHeader"].split("\r\n")[0]})
c = collections.Counter(r["request"].split(" ")[1] for r in rows)
json.dump({"messages_total": len(m), "post_requests_to_workflow_endpoints": dict(c), "samples": rows[:6]}, open("$OUT/zap_workflow_post_evidence.json", "w"), indent=1)
cookies = [h for x in m for h in x["responseHeader"].split("\r\n") if h.lower().startswith("set-cookie")][:6]
open("$OUT/zap_set_cookie_headers.txt", "w").write("\n".join(cookies) + "\n")
print("messages:", len(m), "POSTs to add/remove:", dict(c))
PYEOF
curl -s "$Z/core/action/shutdown/" > /dev/null
echo ZAP_DONE
