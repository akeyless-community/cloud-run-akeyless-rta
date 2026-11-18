"""ADK agent that calls the Akeyless RTA MCP server hosted on Cloud Run.

Env:
  RTA_SERVICE_URL  Cloud Run URL of the RTA service, e.g. https://akeyless-rta-xxxx.a.run.app
The agent's identity (its service account, or your gcloud ADC user locally)
needs roles/run.invoker on that service.
"""

from __future__ import annotations

import os

import google.auth.transport.requests
from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.oauth2 import id_token

SERVICE_URL = os.environ["RTA_SERVICE_URL"].rstrip("/")


def _invoker_headers() -> dict[str, str]:
    # Google ID tokens last about an hour; restart (or rebuild the toolset) before then
    # for long-lived processes.
    token = id_token.fetch_id_token(google.auth.transport.requests.Request(), SERVICE_URL)
    return {"Authorization": f"Bearer {token}"}


root_agent = Agent(
    name="akeyless_rta_mcp",
    model="gemini-2.5-flash",
    instruction=(
        "You run database queries and cloud actions through the Akeyless Runtime Authority "
        "MCP tools. Call list-secrets first, then query-db for databases or service-execute "
        "for everything else. Ask the user before any write or delete. Never ask for or "
        "print credentials."
    ),
    tools=[
        MCPToolset(
            connection_params=StreamableHTTPConnectionParams(
                url=f"{SERVICE_URL}/mcp",
                headers=_invoker_headers(),
            ),
        )
    ],
)
