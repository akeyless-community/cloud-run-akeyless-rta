from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from akeyless_cloudrun_rta import auth
from akeyless_cloudrun_rta.config import config_from_env


def _gcp_config(**overrides):
    return config_from_env(
        gateway_input_url="https://gw.example.com:8000",
        access_id="p-gcp",
        **overrides,
    )


class _FakeCloudId:
    def __init__(self, calls: list):
        self._calls = calls

    def generateGcp(self, audience="akeyless.io"):  # noqa: N802
        self._calls.append(("gcp", audience))
        return "Z2NwLWlk"

    def generate(self, *args, **kwargs):
        self._calls.append(("aws",))
        raise AssertionError("AWS cloud ID must not be generated for gcp")


@pytest.fixture
def cloud_id_calls(monkeypatch):
    calls: list = []
    monkeypatch.setattr(auth, "CloudId", lambda: _FakeCloudId(calls))
    return calls


class TestGcpCloudId:
    def test_default_access_type_is_gcp(self, monkeypatch):
        monkeypatch.delenv("AKEYLESS_ACCESS_TYPE", raising=False)
        assert _gcp_config().access_type == "gcp"

    def test_uses_generate_gcp_with_default_audience(self, cloud_id_calls):
        assert auth.get_gcp_cloud_id(_gcp_config()) == "Z2NwLWlk"
        assert cloud_id_calls == [("gcp", "akeyless.io")]

    def test_custom_audience(self, cloud_id_calls):
        auth.get_gcp_cloud_id(_gcp_config(gcp_audience="my-aud"))
        assert cloud_id_calls == [("gcp", "my-aud")]

    def test_explicit_cloud_id_skips_metadata(self, cloud_id_calls):
        assert auth.get_gcp_cloud_id(_gcp_config(cloud_id="explicit")) == "explicit"
        assert cloud_id_calls == []

    def test_metadata_failure_is_actionable_and_hides_details(self, monkeypatch):
        class _Broken:
            def generateGcp(self, audience="akeyless.io"):  # noqa: N802
                raise RuntimeError("secret-ish internal detail")

        monkeypatch.setattr(auth, "CloudId", _Broken)
        with pytest.raises(ValueError) as ei:
            auth.get_gcp_cloud_id(_gcp_config())
        assert "service account" in str(ei.value)
        assert "secret-ish" not in str(ei.value)


class TestAuthenticate:
    def test_gcp_auth_body(self, cloud_id_calls):
        api = MagicMock()
        api.auth.return_value = SimpleNamespace(token="t-1", expiration=None)
        session = auth.authenticate(api, _gcp_config())
        body = api.auth.call_args[0][0]
        assert body.access_type == "gcp"
        assert body.access_id == "p-gcp"
        assert body.cloud_id == "Z2NwLWlk"
        assert body.gcp_audience == "akeyless.io"
        assert session.token == "t-1"

    def test_access_key_auth_body(self):
        api = MagicMock()
        api.auth.return_value = SimpleNamespace(token="t-2", expiration=None)
        cfg = _gcp_config(access_type="access_key", access_key="k")
        auth.authenticate(api, cfg)
        body = api.auth.call_args[0][0]
        assert body.access_type == "access_key"
        assert body.access_key == "k"

    def test_empty_token_rejected(self, cloud_id_calls):
        api = MagicMock()
        api.auth.return_value = SimpleNamespace(token="", expiration=None)
        with pytest.raises(ValueError, match="did not return a token"):
            auth.authenticate(api, _gcp_config())

    def test_ca_bundle_on_sdk_configuration(self, tmp_path):
        ca = tmp_path / "ca.pem"
        ca.write_text("x")
        api = auth.create_v2_api("https://gw.example.com:8000/api/v2", str(ca))
        assert api.api_client.configuration.ssl_ca_cert == str(ca)


class TestGatewayHeader:
    def test_bearer(self):
        assert auth.build_gateway_auth_header("abc") == {"Authorization": "Bearer abc"}

    def test_empty_rejected(self):
        with pytest.raises(ValueError):
            auth.build_gateway_auth_header("  ")
