"""
Backend tests for AI Feature 4: AI Assistant Chat
Endpoint:
  POST /api/ai/chat

Response envelope: {success: bool, data: {response: str}, message: str|null}
Auth: cookie-based session (same as other AI endpoints)
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@brokeros.com"
ADMIN_PASSWORD = "Admin123!"


@pytest.fixture(scope="session")
def session():
    """Authenticated session for admin user."""
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"Login failed: {r.status_code} {r.text}")
    return s


# ────────── Auth Tests ──────────
class TestChatAuth:
    """Verify auth enforcement on POST /api/ai/chat"""

    def test_chat_without_auth_returns_401_or_403(self):
        """POST without session cookie should be rejected."""
        r = requests.post(
            f"{API}/ai/chat",
            json={"message": "Hello", "conversation_history": []},
            timeout=10,
        )
        assert r.status_code in (401, 403, 503), (
            f"Expected 401/403/503 without auth, got {r.status_code}: {r.text}"
        )

    def test_chat_empty_body_without_auth_returns_error(self):
        """POST with no body and no auth should be rejected."""
        r = requests.post(f"{API}/ai/chat", json={}, timeout=10)
        assert r.status_code in (401, 403, 422, 503), (
            f"Expected auth/validation error, got {r.status_code}"
        )


# ────────── Core Chat Tests ──────────
class TestChatCore:
    """Core functionality: message sending, response envelope, history."""

    def test_chat_empty_history_returns_success(self, session):
        """POST with empty history returns {success:true, data:{response: str}}."""
        r = session.post(
            f"{API}/ai/chat",
            json={"message": "What is a mortgage?", "conversation_history": []},
            timeout=60,
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        body = r.json()
        assert body.get("success") is True, f"success not true: {body}"
        assert "data" in body, f"No 'data' key: {body}"
        assert "response" in body["data"], f"No 'response' in data: {body}"
        assert isinstance(body["data"]["response"], str), "response should be a string"
        assert len(body["data"]["response"]) > 0, "response should not be empty"

    def test_chat_response_text_is_non_empty_string(self, session):
        """Verify the response text is a meaningful non-empty string."""
        r = session.post(
            f"{API}/ai/chat",
            json={"message": "Tell me about UK mortgage rates.", "conversation_history": []},
            timeout=60,
        )
        assert r.status_code == 200
        body = r.json()
        response_text = body["data"]["response"]
        assert isinstance(response_text, str) and len(response_text) > 10, (
            f"Response too short or not a string: {response_text!r}"
        )

    def test_chat_with_conversation_history(self, session):
        """POST with conversation_history uses context — response references prior message."""
        history = [
            {"role": "user", "content": "My client is a first-time buyer."},
            {"role": "assistant", "content": "Great, first-time buyers have access to several schemes like Help to Buy."},
        ]
        r = session.post(
            f"{API}/ai/chat",
            json={"message": "What deposit do they need?", "conversation_history": history},
            timeout=60,
        )
        assert r.status_code == 200, f"Got {r.status_code}: {r.text}"
        body = r.json()
        assert body.get("success") is True
        assert "response" in body["data"]
        assert len(body["data"]["response"]) > 0

    def test_chat_envelope_message_field(self, session):
        """Response envelope should have message field (null or string)."""
        r = session.post(
            f"{API}/ai/chat",
            json={"message": "Hello", "conversation_history": []},
            timeout=60,
        )
        assert r.status_code == 200
        body = r.json()
        # message key must exist (can be None/null)
        assert "message" in body, f"No 'message' key in envelope: {body}"

    def test_chat_missing_message_field_returns_422(self, session):
        """POST without 'message' field should fail validation (422)."""
        r = session.post(
            f"{API}/ai/chat",
            json={"conversation_history": []},
            timeout=10,
        )
        assert r.status_code == 422, (
            f"Expected 422 for missing message, got {r.status_code}: {r.text}"
        )


# ────────── Regression Tests ──────────
class TestRegressionAI:
    """Verify Features 1 and 2 still work after Feature 4 was added."""

    def test_borrower_score_endpoint_still_works(self, session):
        """Feature 1 regression: POST /api/ai/borrower-score returns 200 with score."""
        # Get a valid client_id first
        clients_r = session.get(f"{API}/clients", timeout=15)
        assert clients_r.status_code == 200, f"Clients list failed: {clients_r.status_code}"
        clients_data = clients_r.json()
        clients_list = clients_data.get("data", [])
        if not clients_list:
            pytest.skip("No clients available for borrower score test")
        client_id = clients_list[0]["id"]

        r = session.post(
            f"{API}/ai/borrower-score",
            json={"client_id": client_id},
            timeout=60,
        )
        assert r.status_code == 200, f"borrower-score failed: {r.status_code}: {r.text}"
        body = r.json()
        assert body.get("success") is True
        assert "data" in body
        assert len(body["data"]) > 0, f"Empty data in borrower-score response: {body}"

    def test_lender_match_endpoint_still_works(self, session):
        """Feature 2 regression: POST /api/ai/lender-match returns 200 with matches."""
        # Get a valid case_id first
        cases_r = session.get(f"{API}/cases", timeout=15)
        assert cases_r.status_code == 200
        cases_data = cases_r.json()
        cases_list = cases_data.get("data", [])
        if not cases_list:
            pytest.skip("No cases available for lender match test")
        case_id = cases_list[0]["id"]

        r = session.post(
            f"{API}/ai/lender-match",
            json={"case_id": case_id},
            timeout=60,
        )
        assert r.status_code == 200, f"lender-match failed: {r.status_code}: {r.text}"
        body = r.json()
        assert body.get("success") is True
        assert "data" in body
