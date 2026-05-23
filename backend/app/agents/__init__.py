"""Agent module — proactive AI agents for MostValuableClipper.

Exports:
  - content_agent (ContentAgent) — Source scanning, viral detection, proposals
  - source_agent (SourceAgent) — Source catalog management, health checks
"""

from app.agents.content_agent import ContentAgent, content_agent, ClipProposal
from app.agents.source_agent import SourceAgent, source_agent, SourceHealth

__all__ = [
    "ContentAgent",
    "content_agent",
    "ClipProposal",
    "SourceAgent",
    "source_agent",
    "SourceHealth",
]
