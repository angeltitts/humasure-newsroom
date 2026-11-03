#!/usr/bin/env bash
# Run at the start of every newsroom run. Reports which research hosts are reachable and whether push works.
cd "$(dirname "$0")/.." || exit 1
echo "== push access"; git push --dry-run origin main 2>&1 | tail -1
echo "== network (HTTP code; 000 = blocked)"
for h in humasure.org eur-lex.europa.eu www.nist.gov www.reuters.com www.bbc.com www.gov.uk digital-strategy.ec.europa.eu www.cac.gov.cn www.meti.go.jp www.msit.go.kr www.meity.gov.in www.imda.gov.sg www.industry.gov.au www.ftc.gov www.cpsc.gov www.nhtsa.gov www.iso.org www.etsi.org www.theverge.com techcrunch.com arxiv.org; do
  printf '%-34s %s\n' "$h" "$(curl -s -o /dev/null -w '%{http_code}' --max-time 6 https://$h/)"
done
