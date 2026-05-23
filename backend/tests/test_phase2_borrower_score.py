"""
BrokerOS Phase 2 — AI Borrower Strength Score
Covers POST /api/ai/borrower-score
- Auth required
- 404 for invalid client
- Valid client returns deterministic score + Claude summary
- Score breakdown structure + classification thresholds
"""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@brokeros.com"
ADMIN_PASSWORD = "Admin123!"

VALID_CASE_ID = "09ecdc6c-828e-4134-b316-9c112ccd2848"  # quick reference from main agent


@pytest.fixture(scope="module")
def auth_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def valid_client_id(auth_session):
    """Resolve the client_id from a known test case."""
    r = auth_session.get(f"{API}/cases/{VALID_CASE_ID}")
    if r.status_code != 200:
        # Fallback: grab any client from the list endpoint
        rc = auth_session.get(f"{API}/clients")
        assert rc.status_code == 200, f"clients list failed: {rc.text}"
        data = rc.json()
        items = data.get("clients") or data.get("items") or data
        assert items, "No clients found to test borrower score"
        return items[0]["id"]
    case = r.json()
    cid = case.get("client", {}).get("id") or case.get("client_id")
    assert cid, f"No client_id resolved from case: {case}"
    return cid


# ---------- Auth ----------
class TestBorrowerScoreAuth:
    def test_no_auth_returns_401_or_403(self):
        r = requests.post(f"{API}/ai/borrower-score", json={"client_id": "anything"})
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}: {r.text}"


# ---------- Invalid client ----------
class TestBorrowerScoreInvalidClient:
    def test_unknown_client_returns_404(self, auth_session):
        bogus = str(uuid.uuid4())
        r = auth_session.post(f"{API}/ai/borrower-score", json={"client_id": bogus})
        assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text}"


# ---------- Valid client ----------
class TestBorrowerScoreValid:
    def test_returns_200(self, auth_session, valid_client_id):
        r = auth_session.post(f"{API}/ai/borrower-score", json={"client_id": valid_client_id})
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"

    def test_response_envelope(self, auth_session, valid_client_id):
        r = auth_session.post(f"{API}/ai/borrower-score", json={"client_id": valid_client_id})
        body = r.json()
        assert body.get("success") is True, f"success!=True: {body}"
        assert "data" in body
        d = body["data"]
        for k in ("score", "classification", "colour", "summary", "breakdown"):
            assert k in d, f"missing key {k} in data"

    def test_score_range_and_types(self, auth_session, valid_client_id):
        r = auth_session.post(f"{API}/ai/borrower-score", json={"client_id": valid_client_id})
        d = r.json()["data"]
        assert isinstance(d["score"], int), f"score not int: {type(d['score'])}"
        assert 0 <= d["score"] <= 100, f"score out of range: {d['score']}"

    def test_classification_valid(self, auth_session, valid_client_id):
        r = auth_session.post(f"{API}/ai/borrower-score", json={"client_id": valid_client_id})
        d = r.json()["data"]
        assert d["classification"] in ("Strong", "Good", "Fair", "Weak")

    def test_classification_matches_score_threshold(self, auth_session, valid_client_id):
        r = auth_session.post(f"{API}/ai/borrower-score", json={"client_id": valid_client_id})
        d = r.json()["data"]
        s = d["score"]
        expected = (
            "Strong" if s >= 80 else
            "Good"   if s >= 60 else
            "Fair"   if s >= 40 else
            "Weak"
        )
        assert d["classification"] == expected, f"classification {d['classification']} doesn't match score {s}"

    def test_summary_nonempty_string(self, auth_session, valid_client_id):
        r = auth_session.post(f"{API}/ai/borrower-score", json={"client_id": valid_client_id})
        d = r.json()["data"]
        assert isinstance(d["summary"], str), "summary is not a string"
        assert len(d["summary"].strip()) > 0, "summary is empty"

    def test_breakdown_has_five_components(self, auth_session, valid_client_id):
        r = auth_session.post(f"{API}/ai/borrower-score", json={"client_id": valid_client_id})
        bd = r.json()["data"]["breakdown"]
        for key in ("employment", "income", "credit", "gdpr", "documents"):
            assert key in bd, f"missing breakdown key {key}"
            row = bd[key]
            assert "points" in row and "max" in row and "label" in row, f"row malformed: {row}"

    def test_breakdown_max_values(self, auth_session, valid_client_id):
        r = auth_session.post(f"{API}/ai/borrower-score", json={"client_id": valid_client_id})
        bd = r.json()["data"]["breakdown"]
        assert bd["employment"]["max"] == 30
        assert bd["income"]["max"] == 25
        assert bd["credit"]["max"] == 30
        assert bd["gdpr"]["max"] == 10
        assert bd["documents"]["max"] == 5

    def test_breakdown_points_sum_equals_score(self, auth_session, valid_client_id):
        r = auth_session.post(f"{API}/ai/borrower-score", json={"client_id": valid_client_id})
        d = r.json()["data"]
        bd = d["breakdown"]
        total = sum(bd[k]["points"] for k in ("employment", "income", "credit", "gdpr", "documents"))
        assert total == d["score"], f"sum {total} != score {d['score']}"

    def test_breakdown_points_within_max(self, auth_session, valid_client_id):
        r = auth_session.post(f"{API}/ai/borrower-score", json={"client_id": valid_client_id})
        bd = r.json()["data"]["breakdown"]
        for k, row in bd.items():
            assert 0 <= row["points"] <= row["max"], f"{k} points out of range: {row}"

    def test_deterministic_score(self, auth_session, valid_client_id):
        """Same input => same numeric score (summary may differ)."""
        r1 = auth_session.post(f"{API}/ai/borrower-score", json={"client_id": valid_client_id}).json()["data"]
        r2 = auth_session.post(f"{API}/ai/borrower-score", json={"client_id": valid_client_id}).json()["data"]
        assert r1["score"] == r2["score"]
        assert r1["classification"] == r2["classification"]
