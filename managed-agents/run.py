#!/usr/bin/env python3
"""Run a task against the GES M&A team.  python managed-agents/run.py "Screen <target> for GES"
Requires: pip install anthropic, ANTHROPIC_API_KEY, and managed-agents/ids.json from setup.py."""
import json, sys
from pathlib import Path
import anthropic

ids = json.loads((Path(__file__).parent / "ids.json").read_text())
client = anthropic.Anthropic()
session = client.beta.sessions.create(
    agent=ids["ges-ma-strategy-director"], environment_id=ids["_environment"],
    title=sys.argv[1][:80])
with client.beta.sessions.events.stream(session.id) as stream:
    client.beta.sessions.events.send(session.id, events=[
        {"type": "user.message", "content": [{"type": "text", "text": sys.argv[1]}]}])
    for event in stream:
        if event.type == "agent.message":
            for block in event.content:
                if getattr(block, "text", None):
                    print(block.text)
        elif event.type == "session.status_idle":
            break
