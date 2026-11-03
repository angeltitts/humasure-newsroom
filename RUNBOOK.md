# Newsroom runbook (for the person, not the agent)

## One-time setup so the newsroom can do real research
The scheduled task "Humasure Newsroom (GitHub)" runs in a sandbox that blocks most websites. On 3 November 2026 `humasure.org`, regulator sites and news sites all failed to resolve, so no news could be verified. Fix at claude.ai/code: edit the scheduled task's environment, set network access to **Full** (or a custom allowlist) and include at least:

- humasure.org
- Regulators and standards: eur-lex.europa.eu, digital-strategy.ec.europa.eu, www.gov.uk, www.nist.gov, www.ftc.gov, www.cpsc.gov, www.nhtsa.gov, www.iso.org, www.etsi.org, governor.ny.gov, leginfo.legislature.ca.gov
- Asia-Pacific: www.meti.go.jp, www.msit.go.kr, www.meity.gov.in, www.imda.gov.sg, www.industry.gov.au, www.miit.gov.cn, www.cac.gov.cn
- Outlets: www.reuters.com, www.bbc.com, apnews.com, techcrunch.com, www.theverge.com, www.scmp.com, www.nikkei.com, arxiv.org
- Docs: claude.ai (Operations Hub log)

Then run the task once and check `tools/preflight.sh` output shows 200s.

## Other checks
- The task's repository must be `angeltitts/humasure-newsroom` and the Claude GitHub App must have write access (otherwise push gets 403).
- The Operations Hub log needs the Claude Docs connector enabled for the task; otherwise the agent cannot log runs.
- Posts before 2026-11-03 lack the `incident` field; the website treats a missing field as incident (needs approval), which is the safe default.
- `python3 tools/validate_posts.py` checks every story file.
