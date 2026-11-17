# GES M&A team on Claude Managed Agents

The 8 role definitions in `.claude/agents/` are deployed to the Claude platform
(https://platform.claude.com/docs/en/managed-agents/overview) as one coordinated team.

**Design**
- Lead: `ges-ma-strategy-director` (Opus 5.5) with `multiagent` enabled; it delegates to 7 subagents.
- Subagents: industry strategist, deal sourcing, valuation, financial diligence, contract/organizer, labor (Sonnet 5.5), red team (Opus 5.5).
- Delegation is one level deep (platform rule); the lead must route through red team before answering.
- Prompts come from `.claude/agents/*.md`; edit there, re-run setup.
- Tools are restricted per role (read/grep/glob/web_search/web_fetch/bash only where needed).

**Use**
```bash
export ANTHROPIC_API_KEY=...
python managed-agents/setup.py --dry-run   # inspect payloads
python managed-agents/setup.py             # create agents + environment -> ids.json
pip install anthropic
python managed-agents/run.py "Screen <target company> as an acquisition for GES"
```

**Known gaps (not yet done)**
- Untested against the live API (no key in this session); payloads follow the beta docs.
- Firecrawl people/company enrichment has no built-in equivalent; attach it as an MCP server on `ges-deal-sourcing`.
- Data-room files must be uploaded into the environment sandbox for the diligence, contract, and labor agents to read them.
- Managed Agents is beta, not ZDR/HIPAA eligible, and transcripts persist: keep that in mind for confidential deal data.
- Pricing/rate limits not reviewed (see the platform Reference page).
