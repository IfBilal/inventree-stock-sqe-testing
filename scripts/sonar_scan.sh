#!/usr/bin/env bash
# Re-run SonarQube analysis and export measures. Needs the SonarQube server running (see docs/STATIC_ANALYSIS.md) and a token in $SONAR_TOKEN (or /dev/shm/sonar/token.txt).
set -euo pipefail
cd "$(dirname "$0")/.."
S=${SONAR_HOST:-http://127.0.0.1:9000}; TOK=${SONAR_TOKEN:-$(cat /dev/shm/sonar/token.txt)}
SCANNER=${SONAR_SCANNER:-$HOME/tools/sonar-scanner-6.2.1.4610-linux-x64/bin/sonar-scanner}
SONAR_SCANNER_JAVA_OPTS="-Xmx1g" "$SCANNER" -Dsonar.host.url="$S" -Dsonar.token="$TOK"
for i in $(seq 1 40); do st=$(curl -s -u "$TOK:" "$S/api/ce/component?component=inventree-stock" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('current',{}).get('status'),len(d.get('queue',[])))"); [ "$st" = "SUCCESS 0" ] && break; sleep 3; done
M=ncloc,lines,files,functions,classes,complexity,cognitive_complexity,duplicated_lines_density,duplicated_blocks,duplicated_files,code_smells,bugs,vulnerabilities,security_hotspots,coverage,line_coverage,branch_coverage,sqale_index,sqale_debt_ratio,sqale_rating,reliability_rating,security_rating,security_review_rating,violations,alert_status
mkdir -p evidence/sonar
curl -s -u "$TOK:" "$S/api/measures/component?component=inventree-stock&metricKeys=$M" | python3 -m json.tool > evidence/sonar/project_measures.json
curl -s -u "$TOK:" "$S/api/issues/search?componentKeys=inventree-stock&ps=500" | python3 -m json.tool > evidence/sonar/issues.json
echo "SONAR_EXPORT_OK"
