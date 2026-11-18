import base64
import json
import ssl
from unittest.mock import MagicMock

import pytest

from akeyless_cloudrun_rta.client import AkeylessRtaClient
from akeyless_cloudrun_rta.config import config_from_env, validate_config
from akeyless_cloudrun_rta.http_ara import post_ara_json
from akeyless_cloudrun_rta.tools.mcp import (
    DEFAULT_PORT,
    create_mcp_server,
    handle_tool_call,
    resolve_port,
)
from akeyless_cloudrun_rta.tools.service import AraToolService


def _client() -> AkeylessRtaClient:
    return AkeylessRtaClient(
        gateway_input_url="https://gw.example.com:8000",
        token="t-fixed",
        access_id="p-test",
        _api=MagicMock(),
    )


class TestPort:
    def test_default(self, monkeypatch):
        monkeypatch.delenv("PORT", raising=False)
        assert resolve_port() == DEFAULT_PORT == 8080

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("PORT", "9090")
        assert resolve_port() == 9090

    @pytest.mark.parametrize("raw", ["abc", "0", "70000"])
    def test_invalid(self, raw):
        with pytest.raises(ValueError):
            resolve_port(raw)

    def test_server_binds_port_and_all_interfaces(self, monkeypatch):
        monkeypatch.setenv("PORT", "8123")
        server = create_mcp_server(service=AraToolService(client=_client()))
        assert server.settings.port == 8123
        assert server.settings.host == "0.0.0.0"
        assert server.settings.stateless_http is True
        assert server.settings.streamable_http_path == "/mcp"


class TestCallerAudit:
    def test_caller_merged_into_original_user(self):
        service = MagicMock()
        service.query_db.return_value = MagicMock(to_json=lambda: "{}")
        handle_tool_call(
            service,
            "query-db",
            {
                "secret-name": "/db",
                "payload": "SELECT 1",
                "agent-id": "a",
                "original-user": "alice",
                "original-prompt": "p",
            },
            caller="sa@p.iam.gserviceaccount.com",
        )
        kwargs = service.query_db.call_args.kwargs
        assert kwargs["original_user"] == "alice (via sa@p.iam.gserviceaccount.com)"

    def test_request_caller_from_headers(self):
        server = create_mcp_server(service=AraToolService(client=_client()))
        seg = base64.urlsafe_b64encode(json.dumps({"email": "a@x.com"}).encode()).decode()
        request = MagicMock(headers={"authorization": f"Bearer h.{seg}.s"})
        server.get_context = lambda: MagicMock(request_context=MagicMock(request=request))
        assert server._request_caller() == "a@x.com"

    def test_request_caller_outside_request(self):
        server = create_mcp_server(service=AraToolService(client=_client()))
        assert server._request_caller() is None


class TestCaBundle:
    def test_missing_file_rejected(self):
        cfg = config_from_env(
            gateway_input_url="https://gw.example.com:8000",
            access_id="p",
            ca_bundle="/does/not/exist.pem",
        )
        with pytest.raises(ValueError, match="AKEYLESS_CA_BUNDLE"):
            validate_config(cfg)

    def test_context_passed_with_verification(self, monkeypatch, tmp_path):
        ca = tmp_path / "ca.pem"
        ca.write_text("x")
        created = {}

        def fake_context(cafile=None):
            created["cafile"] = cafile
            ctx = MagicMock()
            ctx.verify_mode = ssl.CERT_REQUIRED
            return ctx

        monkeypatch.setattr(ssl, "create_default_context", fake_context)
        captured = {}

        class _Resp:
            status = 200

            def read(self):
                return b"{}"

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def opener(request, timeout=None, context=None):
            captured["context"] = context
            return _Resp()

        post_ara_json(
            "https://gw.example.com:8000",
            "/config/target_query",
            {"Authorization": "Bearer t"},
            {},
            "target query",
            opener=opener,
            ca_bundle=str(ca),
        )
        assert created["cafile"] == str(ca)
        assert captured["context"].verify_mode == ssl.CERT_REQUIRED

    def test_no_context_without_bundle(self):
        captured = {}

        class _Resp:
            status = 200

            def read(self):
                return b"{}"

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def opener(request, **kwargs):
            captured.update(kwargs)
            return _Resp()

        post_ara_json("https://gw:8000", "/x", {}, {}, "x", opener=opener)
        assert "context" not in captured


class TestNoSecretValues:
    def test_list_secrets_drops_value_fields(self):
        client = _client()
        client._api.list_items.return_value = MagicMock(
            items=[
                {
                    "item_name": "/db/pg",
                    "item_type": "dynamic-secret",
                    "client_permissions": ["ara_allow_access"],
                    "dynamic_secret_producer_details": {"producer_type": "postgres"},
                    "value": "hunter2",
                    "password": "hunter2",
                }
            ]
        )
        out = AraToolService(client=client).list_secrets().to_json()
        assert "hunter2" not in out
        assert json.loads(out)["secrets"][0]["name"] == "/db/pg"
