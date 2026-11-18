"""Authenticate to Akeyless from Cloud Run (GCP service account first)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone

import akeyless
from akeyless_cloud_id import CloudId

from akeyless_cloudrun_rta.config import AkeylessRtaConfig

ACCESS_KEY_DEFAULT_TTL_SECONDS = 14 * 60
ENV_TOKEN_TTL_SECONDS = 50 * 60


@dataclass
class AuthSession:
    token: str
    expires_at: float


def _expiry_from_auth_output(auth_out: akeyless.AuthOutput, margin_seconds: float) -> float:
    now = time.monotonic()
    expiration = getattr(auth_out, "expiration", None)
    if not expiration:
        return now + ACCESS_KEY_DEFAULT_TTL_SECONDS - margin_seconds

    raw = str(expiration).strip()
    if not raw:
        return now + ACCESS_KEY_DEFAULT_TTL_SECONDS - margin_seconds

    try:
        as_num = float(raw)
        if as_num > 1e12:
            return (as_num / 1000.0) - time.time() + now - margin_seconds
    except ValueError:
        pass

    try:
        as_date = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if as_date.tzinfo is None:
            as_date = as_date.replace(tzinfo=timezone.utc)
        return as_date.timestamp() - time.time() + now - margin_seconds
    except ValueError:
        pass

    return now + ACCESS_KEY_DEFAULT_TTL_SECONDS - margin_seconds


def get_gcp_cloud_id(config: AkeylessRtaConfig) -> str:
    """Cloud ID from the service account's ID token (Cloud Run metadata server)."""
    if config.cloud_id and config.cloud_id.strip():
        return config.cloud_id.strip()

    try:
        cloud_id = CloudId().generateGcp(audience=config.gcp_audience)
    except Exception as exc:
        raise ValueError(
            "Could not obtain a GCP ID token for Akeyless authentication "
            f"({type(exc).__name__}). On Cloud Run, check that the service has a "
            "service account attached; locally, run `gcloud auth application-default login` "
            "with a service account or set AKEYLESS_CLOUD_ID."
        ) from exc
    if not cloud_id or not str(cloud_id).strip():
        raise ValueError("akeyless-cloud-id returned an empty GCP cloud ID")
    return str(cloud_id).strip()


def create_v2_api(sdk_gateway_url: str, ca_bundle: str | None = None) -> akeyless.V2Api:
    """Create V2Api pointed at the customer Gateway SDK base (…/api/v2)."""
    configuration = akeyless.Configuration(host=sdk_gateway_url.rstrip("/"))
    if ca_bundle:
        configuration.ssl_ca_cert = ca_bundle
    return akeyless.V2Api(akeyless.ApiClient(configuration))


def authenticate(api: akeyless.V2Api, config: AkeylessRtaConfig) -> AuthSession:
    now = time.monotonic()

    if config.token and config.token.strip():
        return AuthSession(
            token=config.token.strip(),
            expires_at=now + ENV_TOKEN_TTL_SECONDS,
        )

    access_type = config.access_type

    if access_type == "gcp":
        body = akeyless.Auth(
            access_id=config.access_id,
            access_type="gcp",
            cloud_id=get_gcp_cloud_id(config),
            gcp_audience=config.gcp_audience,
        )
    elif access_type in ("access_key", "api_key"):
        body = akeyless.Auth(
            access_id=config.access_id,
            access_type="access_key",
            access_key=config.access_key,
        )
    elif access_type == "universal_identity":
        body = akeyless.Auth(
            access_type="universal_identity",
            uid_token=config.uid_token,
        )
    elif access_type == "jwt":
        body = akeyless.Auth(
            access_id=config.access_id,
            access_type="jwt",
            jwt=config.jwt,
        )
    else:
        raise ValueError(f"Unsupported access type: {access_type}")

    auth_out = api.auth(body)
    token = getattr(auth_out, "token", None)
    if not token or not str(token).strip():
        raise ValueError("Akeyless authentication did not return a token")

    return AuthSession(
        token=str(token).strip(),
        expires_at=_expiry_from_auth_output(auth_out, config.token_expiry_margin_seconds),
    )


def build_gateway_auth_header(session: AuthSession | str) -> dict[str, str]:
    """Authorization header for Gateway ARA config-port calls."""
    token = session if isinstance(session, str) else session.token
    trimmed = token.strip()
    if not trimmed:
        raise ValueError("Unable to build gateway authorization header: empty token")
    return {"Authorization": f"Bearer {trimmed}"}
