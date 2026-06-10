"""
Backend tests for Phase 2.5 — Rate Expiry and Retention module
Tests: GET /api/retention/cases, PATCH /api/retention/cases/{id}/status, GET /api/retention/alerts
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s

@pytest.fixture(scope="module")
def auth_session(session):
    resp = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@brokeros.com",
        "password": "Admin123!"
    })
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return session

@pytest.fixture(scope="module")
def test_case_id(auth_session):
    """Create a client + case in completion stage with rate_expiry_date ~60 days from now."""
    # Create client
    expiry_date = (datetime.utcnow() + timedelta(days=60)).strftime("%Y-%m-%d")
    client_resp = auth_session.post(f"{BASE_URL}/api/clients", json={
        "first_name": "TEST_Retention",
        "last_name": "Client",
        "email": "test_retention@example.com",
        "phone": "07700900001",
    })
    assert client_resp.status_code == 200, f"Client create failed: {client_resp.text}"
    client_id = client_resp.json()["data"]["id"]

    # Create case in completion stage with rate_expiry_date
    case_resp = auth_session.post(f"{BASE_URL}/api/cases", json={
        "client_id": client_id,
        "mortgage_type": "residential",
        "loan_amount": 250000,
        "stage": "completion",
        "rate_expiry_date": expiry_date,
        "rate_type": "fixed",
        "rate_percent": 3.5,
    })
    assert case_resp.status_code == 200, f"Case create failed: {case_resp.text}"
    case_id = case_resp.json()["data"]["id"]
    yield case_id, client_id

    # Cleanup
    auth_session.delete(f"{BASE_URL}/api/cases/{case_id}")
    auth_session.delete(f"{BASE_URL}/api/clients/{client_id}")


# ── Auth guard tests ──────────────────────────────────────────────────────────

class TestRetentionAuth:
    """All 3 endpoints must require authentication"""

    def test_cases_no_auth(self, session):
        r = requests.get(f"{BASE_URL}/api/retention/cases")
        assert r.status_code in [401, 403], f"Expected 401/403, got {r.status_code}"
        print("PASS: GET /retention/cases returns 401 without auth")

    def test_patch_no_auth(self, session):
        r = requests.patch(f"{BASE_URL}/api/retention/cases/fake-id/status", json={"retention_status": "contacted"})
        assert r.status_code in [401, 403], f"Expected 401/403, got {r.status_code}"
        print("PASS: PATCH /retention/cases/{id}/status returns 401 without auth")

    def test_alerts_no_auth(self, session):
        r = requests.get(f"{BASE_URL}/api/retention/alerts")
        assert r.status_code in [401, 403], f"Expected 401/403, got {r.status_code}"
        print("PASS: GET /retention/alerts returns 401 without auth")


# ── GET /retention/cases ──────────────────────────────────────────────────────

class TestRetentionCases:
    """Tests for GET /api/retention/cases"""

    def test_response_envelope(self, auth_session, test_case_id):
        r = auth_session.get(f"{BASE_URL}/api/retention/cases")
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert "data" in body
        assert "cases" in body["data"]
        assert "summary" in body["data"]
        print("PASS: Response envelope correct")

    def test_summary_fields(self, auth_session, test_case_id):
        r = auth_session.get(f"{BASE_URL}/api/retention/cases")
        summary = r.json()["data"]["summary"]
        assert "total_monitored" in summary
        assert "expiring_90_days" in summary
        assert "expiring_180_days" in summary
        assert "already_expired" in summary
        assert summary["total_monitored"] >= 1
        print(f"PASS: Summary fields present, total_monitored={summary['total_monitored']}")

    def test_case_fields(self, auth_session, test_case_id):
        case_id, _ = test_case_id
        r = auth_session.get(f"{BASE_URL}/api/retention/cases")
        cases = r.json()["data"]["cases"]
        case = next((c for c in cases if c["id"] == case_id), None)
        assert case is not None, f"Test case {case_id} not in retention list"
        assert "client_name" in case
        assert "lender_name" in case
        assert "days_until_expiry" in case
        assert "retention_status" in case
        assert "rate_expiry_date" in case
        print(f"PASS: Case fields present, days_until_expiry={case['days_until_expiry']}")

    def test_window_90_filter(self, auth_session, test_case_id):
        case_id, _ = test_case_id
        r = auth_session.get(f"{BASE_URL}/api/retention/cases?window=90")
        assert r.status_code == 200
        cases = r.json()["data"]["cases"]
        # Test case expires in 60 days — should appear
        case = next((c for c in cases if c["id"] == case_id), None)
        assert case is not None, "60-day case should appear in window=90 filter"
        # All days_until_expiry should be <= 90
        for c in cases:
            if c["days_until_expiry"] is not None:
                assert c["days_until_expiry"] <= 90, f"Case with {c['days_until_expiry']} days returned in window=90"
        print("PASS: window=90 filter works correctly")

    def test_window_minus1_expired(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/retention/cases?window=-1")
        assert r.status_code == 200
        cases = r.json()["data"]["cases"]
        for c in cases:
            if c["days_until_expiry"] is not None:
                assert c["days_until_expiry"] < 0, f"Non-expired case in window=-1: {c['days_until_expiry']}"
        print(f"PASS: window=-1 returns only expired cases (count={len(cases)})")

    def test_status_filter(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/retention/cases?status=contacted")
        assert r.status_code == 200
        cases = r.json()["data"]["cases"]
        for c in cases:
            assert c["retention_status"] == "contacted", f"Non-contacted case in status=contacted filter"
        print(f"PASS: status=contacted filter works (count={len(cases)})")

    def test_default_retention_status_none(self, auth_session, test_case_id):
        case_id, _ = test_case_id
        r = auth_session.get(f"{BASE_URL}/api/retention/cases")
        cases = r.json()["data"]["cases"]
        case = next((c for c in cases if c["id"] == case_id), None)
        assert case is not None
        assert case["retention_status"] == "none"
        print("PASS: Default retention_status is 'none'")


# ── PATCH /retention/cases/{id}/status ───────────────────────────────────────

class TestPatchRetentionStatus:
    """Tests for PATCH /api/retention/cases/{case_id}/status"""

    def test_mark_contacted(self, auth_session, test_case_id):
        case_id, _ = test_case_id
        r = auth_session.patch(f"{BASE_URL}/api/retention/cases/{case_id}/status", json={"retention_status": "contacted"})
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        print("PASS: PATCH to 'contacted' succeeds")

    def test_verify_status_persisted(self, auth_session, test_case_id):
        case_id, _ = test_case_id
        r = auth_session.get(f"{BASE_URL}/api/retention/cases")
        cases = r.json()["data"]["cases"]
        case = next((c for c in cases if c["id"] == case_id), None)
        assert case is not None
        assert case["retention_status"] == "contacted"
        print("PASS: Status persisted correctly in DB")

    def test_valid_statuses(self, auth_session, test_case_id):
        case_id, _ = test_case_id
        for status in ["none", "flagged", "contacted", "new_case_created"]:
            r = auth_session.patch(f"{BASE_URL}/api/retention/cases/{case_id}/status", json={"retention_status": status})
            assert r.status_code == 200, f"Status '{status}' should be valid, got {r.status_code}"
        print("PASS: All 4 valid statuses accepted")

    def test_invalid_status_422(self, auth_session, test_case_id):
        case_id, _ = test_case_id
        r = auth_session.patch(f"{BASE_URL}/api/retention/cases/{case_id}/status", json={"retention_status": "invalid_status"})
        assert r.status_code == 422, f"Expected 422, got {r.status_code}"
        print("PASS: Invalid status returns 422")

    def test_nonexistent_case_404(self, auth_session):
        r = auth_session.patch(f"{BASE_URL}/api/retention/cases/nonexistent-id-123/status", json={"retention_status": "contacted"})
        assert r.status_code == 404
        print("PASS: Nonexistent case returns 404")


# ── GET /retention/alerts ─────────────────────────────────────────────────────

class TestRetentionAlerts:
    """Tests for GET /api/retention/alerts"""

    def test_alerts_envelope(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/retention/alerts")
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert "data" in body
        assert "alerts" in body["data"]
        print("PASS: Alerts response envelope correct")

    def test_alerts_only_within_30_days(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/retention/alerts")
        alerts = r.json()["data"]["alerts"]
        for a in alerts:
            days = a["days_until_expiry"]
            assert days <= 30, f"Alert case has {days} days — should only show <=30"
        print(f"PASS: All alerts within 30 days (count={len(alerts)})")

    def test_alerts_fields(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/retention/alerts")
        alerts = r.json()["data"]["alerts"]
        for a in alerts:
            assert "id" in a
            assert "client_name" in a
            assert "lender_name" in a
            assert "rate_expiry_date" in a
            assert "days_until_expiry" in a
        print("PASS: Alert fields are correct")


# ── Regression: existing endpoints ───────────────────────────────────────────

class TestRegression:
    """Regression checks for existing features"""

    def test_login(self, session):
        r = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@brokeros.com", "password": "Admin123!"
        })
        assert r.status_code == 200
        print("PASS: Login still works")

    def test_dashboard_stats(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/dashboard/stats")
        assert r.status_code == 200
        print("PASS: Dashboard stats endpoint works")

    def test_cases_list(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/cases")
        assert r.status_code == 200
        print("PASS: Cases list endpoint works")
