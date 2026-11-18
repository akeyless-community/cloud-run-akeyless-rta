"""Akeyless Agentic Runtime Authority (RTA/ARA) for Google Cloud Run."""

from akeyless_cloudrun_rta.client import AkeylessRtaClient, get_default_client
from akeyless_cloudrun_rta.ara import AraSecretSummary, OAuthAuthorizationRequiredError

__all__ = [
    "AkeylessRtaClient",
    "AraSecretSummary",
    "OAuthAuthorizationRequiredError",
    "get_default_client",
]

__version__ = "0.1.0"
