#!/usr/bin/env python3
"""Create the GES M&A agents on Claude Managed Agents (beta).

Source of truth for each agent's role/prompt is .claude/agents/*.md, so the
Claude Code subagents and the platform agents never drift apart.

  python managed-agents/setup.py --dry-run   # print payloads, no network
  python managed-agents/setup.py             # create agents + environment

Needs ANTHROPIC_API_KEY. Writes IDs to managed-agents/ids.json.
Endpoints/headers per https://platform.claude.com/docs/en/managed-agents/
"""
import argparse, json, os, re, sys, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENT_DIR = ROOT / ".claude" / "agents"
IDS_FILE = Path(__file__).resolve().parent / "ids.json"
API = "https://api.anthropic.com/v1"
HEADERS = {
    "anthropic-version": "2026-10-21",
    "anthropic-beta": "managed-agents-2026-04-01",
    "content-type": "application/json",
}

LEAD = "ges-ma-strategy-director"
# Model per agent. Lead and red team get the strongest model.
MODELS = {"ges-ma-strategy-director": "claude-opus-5-5", "ges-red-team": "claude-opus-5-5"}
DEFAULT_MODEL = "claude-sonnet-5-5"

# Claude Code tool name -> Managed Agents built-in tool name
TOOL_MAP = {
    "Read": "read", "Grep": "grep", "Glob": "glob", "Bash": "bash",
    "WebSearch": "web_search",
    "mcp__firecrawl__firecrawl_search": "web_search",
    "mcp__firecrawl__firecrawl_scrape": "web_fetch",
}
# People/company enrichment (Firecrawl MCP) has no built-in equivalent: attach an MCP server later.

COORDINATOR_ADDENDUM = """

## Coordinating the team
You lead a team of specialist subagents: ges-industry-strategist, ges-deal-sourcing,
ges-valuation-analyst, ges-financial-diligence, ges-contract-organizer-analyst,
ges-labor-specialist, and ges-red-team. Delegate work to them, run independent
analyses in parallel, reconcile conflicts, and always send your draft recommendation
to ges-red-team before presenting it. Return one decision-ready memo to the user:
recommendation, top reasons, valuation range, key risks, walk-away conditions,
and open questions."""


def parse(path: Path):
    text = path.read_text()
    m = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S)
    meta = dict(l.split(": ", 1) for l in m.group(1).splitlines() if ": " in l)
    return meta, m.group(2).strip()


def toolset(claude_tools: str):
    wanted = sorted({TOOL_MAP[t.strip()] for t in claude_tools.split(",") if t.strip() in TOOL_MAP})
    return {
        "type": "agent_toolset_20260401",
        "default_config": {"enabled": False},
        "configs": [{"name": n, "enabled": True} for n in wanted],
    }


def payload(meta, body, name, subagent_ids=None):
    p = {
        "name": name,
        "description": meta["description"],
        "model": MODELS.get(name, DEFAULT_MODEL),
        "system": body + (COORDINATOR_ADDENDUM if subagent_ids else ""),
        "tools": [toolset(meta["tools"])],
    }
    if subagent_ids:
        p["multiagent"] = {
            "type": "multiagent_20261001",
            "subagents": {
                "type": "enabled",
                "inline_agents": {"type": "disabled"},
                "predefined_agents": [{"type": "agent", "id": i} for i in subagent_ids],
            },
            "workflows": {"type": "disabled"},
        }
    return p


def post(path, body):
    req = urllib.request.Request(f"{API}{path}", data=json.dumps(body).encode(), method="POST",
                                 headers={**HEADERS, "x-api-key": os.environ["ANTHROPIC_API_KEY"]})
    try:
        return json.load(urllib.request.urlopen(req))
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code} on {path}: {e.read().decode()}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if not a.dry_run and not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("Set ANTHROPIC_API_KEY (or use --dry-run).")

    agents = {p.stem: parse(p) for p in sorted(AGENT_DIR.glob("ges-*.md"))}
    ids = {}
    # specialists first (the lead references them by id), lead last
    for name, (meta, body) in agents.items():
        if name == LEAD:
            continue
        pl = payload(meta, body, name)
        ids[name] = "dry-run" if a.dry_run else post("/agents", pl)["id"]
        print(f"specialist {name}: {ids[name]}")
    meta, body = agents[LEAD]
    lead_pl = payload(meta, body, LEAD, [i for n, i in ids.items()])
    if a.dry_run:
        print(json.dumps(lead_pl, indent=2)[:3500])
        return
    ids[LEAD] = post("/agents", lead_pl)["id"]
    env = post("/environments", {"name": "ges-ma-env", "config": {
        "type": "cloud", "networking": {"type": "limited", "allow_package_managers": True}}})
    ids["_environment"] = env["id"]
    IDS_FILE.write_text(json.dumps(ids, indent=2))
    print(f"lead {LEAD}: {ids[LEAD]}\nenvironment: {env['id']}\nsaved -> {IDS_FILE}")


if __name__ == "__main__":
    main()
