import base64
import json

from akeyless_cloudrun_rta.caller import caller_identity_from_headers, merge_original_user


def _jwt(payload: dict) -> str:
    def seg(obj):
        return base64.urlsafe_b64encode(json.dumps(obj).encode()).decode().rstrip("=")

    return f"{seg({'alg': 'RS256'})}.{seg(payload)}.sig"


class TestCallerIdentity:
    def test_email_from_authorization(self):
        headers = {"Authorization": f"Bearer {_jwt({'email': 'agent@p.iam.gserviceaccount.com'})}"}
        assert caller_identity_from_headers(headers) == "agent@p.iam.gserviceaccount.com"

    def test_serverless_header_preferred(self):
        headers = {
            "X-Serverless-Authorization": f"Bearer {_jwt({'email': 'a@x.com'})}",
            "Authorization": f"Bearer {_jwt({'email': 'b@x.com'})}",
        }
        assert caller_identity_from_headers(headers) == "a@x.com"

    def test_signature_stripped_token(self):
        token = _jwt({"email": "a@x.com"}).rsplit(".", 1)[0] + "."
        assert caller_identity_from_headers({"authorization": f"Bearer {token}"}) == "a@x.com"

    def test_falls_back_to_sub(self):
        headers = {"authorization": f"Bearer {_jwt({'sub': '1234'})}"}
        assert caller_identity_from_headers(headers) == "1234"

    def test_garbage_and_missing(self):
        assert caller_identity_from_headers(None) is None
        assert caller_identity_from_headers({}) is None
        assert caller_identity_from_headers({"authorization": "Basic abc"}) is None
        assert caller_identity_from_headers({"authorization": "Bearer not-a-jwt"}) is None
        assert caller_identity_from_headers({"authorization": "Bearer a.!!!.c"}) is None

    def test_length_capped(self):
        headers = {"authorization": f"Bearer {_jwt({'email': 'x' * 1000})}"}
        assert len(caller_identity_from_headers(headers)) == 256


class TestMergeOriginalUser:
    def test_both(self):
        assert merge_original_user("alice", "sa@p") == "alice (via sa@p)"

    def test_same(self):
        assert merge_original_user("sa@p", "sa@p") == "sa@p"

    def test_one_side(self):
        assert merge_original_user(None, "sa@p") == "sa@p"
        assert merge_original_user("alice", None) == "alice"
        assert merge_original_user(None, None) is None
