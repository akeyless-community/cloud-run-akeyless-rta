"""ADK agent that embeds the Akeyless RTA client (no MCP hop).

Run it on Cloud Run with a service account bound to the Akeyless GCP auth
method. The agent gets query results only; credentials stay in the Gateway.
Set GEMINI_MODEL to a Gemini model enabled in your project (default: gemini-4-neon).
"""

from __future__ import annotations

import os

from google.adk.agents import Agent

from akeyless_cloudrun_rta.tools.service import AraToolService

_service = AraToolService()


def list_secrets(path: str = "") -> str:
    """List Akeyless secrets enabled for Runtime Authority (names and types only)."""
    return _service.list_secrets(path=path or None).to_json()


def query_db(secret_name: str, payload: str, original_prompt: str) -> str:
    """Run a database query through Akeyless Runtime Authority and return the rows as JSON."""
    return _service.query_db(
        payload,
        secret_name=secret_name,
        agent_id="adk-embedded",
        original_prompt=original_prompt,
    ).to_json()


def service_execute(secret_name: str, payload: str, original_prompt: str) -> str:
    """Run a cloud, Kubernetes, GitHub or remote-host action through Akeyless Runtime Authority."""
    return _service.service_execute(
        payload,
        secret_name=secret_name,
        agent_id="adk-embedded",
        original_prompt=original_prompt,
    ).to_json()


def list_sub_tools(secret_name: str) -> str:
    """List the sub-tools a service secret exposes (optional before service_execute)."""
    return _service.list_sub_tools(secret_name=secret_name, agent_id="adk-embedded").to_json()


root_agent = Agent(
    name="akeyless_rta_embedded",
    model=os.environ.get("GEMINI_MODEL", "gemini-4-neon"),
    instruction=(
        "You run database queries and cloud actions through Akeyless Runtime Authority. "
        "Call list_secrets first to pick a secret. Use query_db for database secrets and "
        "service_execute for everything else. Ask the user before any write or delete. "
        "Never ask for or print credentials; you only ever see results."
    ),
    tools=[list_secrets, query_db, service_execute, list_sub_tools],
)
