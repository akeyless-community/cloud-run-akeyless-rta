"""Caller identity from the ID token that Cloud Run IAM already verified.

Cloud Run checks the invoker's Google ID token before the request reaches the
container and may strip its signature when forwarding, so the payload is only
decoded here, never verified. The result is audit metadata for the Gateway
(``original_user``), not an access-control decision: access control is Cloud Run
IAM (``roles/run.invoker``) plus the Akeyless role of the service account.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Mapping
from typing import Any

SERVERLESS_AUTH_HEADER = "x-serverless-authorization"
AUTH_HEADER = "authorization"
MAX_IDENTITY_LENGTH = 256


def _jwt_payload(token: str) -> dict[str, Any] | None:
    parts = token.split(".")
    if len(parts) < 2 or not parts[1]:
        return None
    segment = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        decoded = json.loads(base64.urlsafe_b64decode(segment.encode("ascii")))
    except (ValueError, UnicodeError):
        return None
    return decoded if isinstance(decoded, dict) else None


def _bearer(value: str | None) -> str | None:
    if not value:
        return None
    scheme, _, token = value.strip().partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def caller_identity_from_headers(headers: Mapping[str, str] | None) -> str | None:
    """Return the invoker's email (or subject) from the Cloud Run auth headers."""
    if not headers:
        return None
    lowered = {str(k).lower(): v for k, v in headers.items()}
    for header in (SERVERLESS_AUTH_HEADER, AUTH_HEADER):
        token = _bearer(lowered.get(header))
        if not token:
            continue
        payload = _jwt_payload(token)
        if not payload:
            continue
        identity = payload.get("email") or payload.get("sub")
        if isinstance(identity, str) and identity.strip():
            return identity.strip()[:MAX_IDENTITY_LENGTH]
    return None


def merge_original_user(agent_supplied: str | None, caller: str | None) -> str | None:
    """Combine the agent-reported end user with the IAM-verified caller for audit."""
    if caller and agent_supplied and agent_supplied != caller:
        return f"{agent_supplied} (via {caller})"
    return caller or agent_supplied
