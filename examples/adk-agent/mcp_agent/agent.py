"""ADK agent that calls the Akeyless RTA MCP server hosted on Cloud Run.

Env:
  RTA_SERVICE_URL  Cloud Run URL of the RTA service, e.g. https://akeyless-rta-xxxx.a.run.app
  GEMINI_MODEL     Gemini model enabled in your project (default: gemini-4-neon)
The agent's identity (its service account, or your gcloud user locally)
needs roles/run.invoker on that service.
"""

from __future__ import annotations

import os
import subprocess

import google.auth.exceptions
import google.auth.transport.requests
from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.oauth2 import id_token

SERVICE_URL = os.environ["RTA_SERVICE_URL"].rstrip("/")
MODEL = os.environ.get("GEMINI_MODEL", "gemini-4-neon")


def _fetch_token() -> str:
    try:
        return id_token.fetch_id_token(google.auth.transport.requests.Request(), SERVICE_URL)
    except google.auth.exceptions.DefaultCredentialsError:
        # User ADC (gcloud auth application-default login) cannot mint ID tokens;
        # only the metadata server or a service account key can.
        return subprocess.run(
            ["gcloud", "auth", "print-identity-token"], capture_output=True, text=True, check=True
        ).stdout.strip()


def _invoker_headers() -> dict[str, str]:
    # Google ID tokens last about an hour; restart (or rebuild the toolset) before then
    # for long-lived processes.
    return {"Authorization": f"Bearer {_fetch_token()}"}


root_agent = Agent(
    name="akeyless_rta_mcp",
    model=MODEL,
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
