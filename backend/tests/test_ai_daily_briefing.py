"""
Backend tests for AI Feature 3: Daily Briefing (Phase 2)
Endpoints:
  GET    /api/ai/daily-briefing            (generates + caches)
  GET    /api/ai/daily-briefing?probe=true (returns cache without Claude)
  DELETE /api/ai/daily-briefing            (clears today's cache)

All responses are wrapped: {success: bool, data: {...}, message: str|null}
"""
import os
import time
import uuid
import pytest
import requests
from datetime import datetime, timezone

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@brokeros.com"
ADMIN_PASSWORD = "Admin123!"


@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"Login failed: {r.status_code} {r.text}")
    return s


@pytest.fixture(scope="session", autouse=True)
def clear_cache_at_start(session):
    """Ensure no cached briefing before tests begin."""
    session.delete(f"{API}/ai/daily-briefing", timeout=10)
    yield
    # cleanup: leave cache intact (tests will populate)


# ────────── Auth ──────────
class TestAuth:
    def test_get_without_auth(self):
        r = requests.get(f"{API}/ai/daily-briefing", timeout=10)
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"

    def test_delete_without_auth(self):
        r = requests.delete(f"{API}/ai/daily-briefing", timeout=10)
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"

    def test_probe_without_auth(self):
        r = requests.get(f"{API}/ai/daily-briefing?probe=true", timeout=10)
        assert r.status_code in (401, 403)


# ────────── Probe behaviour ──────────
class TestProbe:
    def test_probe_with_no_cache_is_fast_and_returns_null(self, session):
        # ensure cache cleared
        session.delete(f"{API}/ai/daily-briefing", timeout=10)
        start = time.time()
        r = session.get(f"{API}/ai/daily-briefing?probe=true", timeout=10)
        elapsed_ms = (time.time() - start) * 1000
        assert r.status_code == 200, r.text
        body = r.json()
        # Top-level response shape
        assert body.get("success") is True, f"Expected success:true, got: {body}"
        data = body.get("data", {})
        assert data.get("cached") is False, f"Expected cached:false in data, got: {data}"
        assert data.get("briefing") is None, f"Expected briefing:null, got: {data}"
        assert data.get("generated_at") is None, f"Expected generated_at:null, got: {data}"
        # Should be very fast — no Claude call. Allow 1500ms network jitter.
        assert elapsed_ms < 1500, f"Probe took {elapsed_ms:.0f}ms — Claude may have been called"

    def test_probe_response_envelope_shape(self, session):
        """Probe must return success/data/message envelope."""
        session.delete(f"{API}/ai/daily-briefing", timeout=10)
        r = session.get(f"{API}/ai/daily-briefing?probe=true", timeout=10)
        assert r.status_code == 200
        body = r.json()
        # Envelope keys
        assert "success" in body and "data" in body, f"Missing envelope keys: {body.keys()}"
        data = body["data"]
        # Data keys
        assert set(data.keys()) >= {"briefing", "generated_at", "cached"}, \
            f"Unexpected data keys: {data.keys()}"


# ────────── Generation + cache ──────────
class TestGenerateAndCache:
    def test_first_call_generates_then_second_call_uses_cache(self, session):
        # clear cache first
        session.delete(f"{API}/ai/daily-briefing", timeout=10)

        # First call → generates via Claude
        r1 = session.get(f"{API}/ai/daily-briefing", timeout=90)
        assert r1.status_code == 200, r1.text
        body1 = r1.json()
        assert body1.get("success") is True, f"Expected success:true, got: {body1}"
        b1 = body1["data"]
        assert "briefing" in b1 and "generated_at" in b1 and "cached" in b1, \
            f"Missing data fields: {b1.keys()}"
        assert isinstance(b1["briefing"], str) and len(b1["briefing"]) > 20, \
            "Briefing should be non-empty string"
        assert b1["cached"] is False, f"First call should have cached:false, got: {b1}"
        assert b1["generated_at"] is not None
        # generated_at should parse as ISO
        datetime.fromisoformat(b1["generated_at"].replace("Z", "+00:00"))

        # Second call → cached
        start = time.time()
        r2 = session.get(f"{API}/ai/daily-briefing", timeout=10)
        elapsed_ms = (time.time() - start) * 1000
        assert r2.status_code == 200
        body2 = r2.json()
        assert body2.get("success") is True
        b2 = body2["data"]
        assert b2["cached"] is True, f"Second call should have cached:true, got: {b2}"
        assert b2["briefing"] == b1["briefing"], "Cached briefing should be identical"
        assert b2["generated_at"] == b1["generated_at"], "Cached generated_at should match"
        assert elapsed_ms < 1500, f"Cached call took {elapsed_ms:.0f}ms — should be fast"

    def test_probe_with_existing_cache_returns_cached(self, session):
        # Cache should exist from previous test
        r = session.get(f"{API}/ai/daily-briefing?probe=true", timeout=10)
        assert r.status_code == 200
        body = r.json()
        assert body.get("success") is True
        data = body["data"]
        assert data["cached"] is True, f"Expected cached:true, got: {data}"
        assert isinstance(data["briefing"], str) and len(data["briefing"]) > 0, \
            f"Expected non-empty briefing, got: {data}"
        assert data["generated_at"] is not None


# ────────── DELETE cache ──────────
class TestDeleteCache:
    def test_delete_response_shape(self, session):
        """DELETE returns {success:true, data:{cleared:true}}"""
        # Ensure cache exists first
        session.get(f"{API}/ai/daily-briefing", timeout=90)
        rd = session.delete(f"{API}/ai/daily-briefing", timeout=10)
        assert rd.status_code == 200
        body = rd.json()
        assert body.get("success") is True, f"Expected success:true, got: {body}"
        assert body.get("data", {}).get("cleared") is True, \
            f"Expected data.cleared:true, got: {body}"

    def test_delete_clears_cache_and_probe_returns_false(self, session):
        # Ensure a fresh briefing exists
        session.get(f"{API}/ai/daily-briefing", timeout=90)

        # DELETE
        rd = session.delete(f"{API}/ai/daily-briefing", timeout=10)
        assert rd.status_code == 200

        # Probe after delete → no cache
        rp = session.get(f"{API}/ai/daily-briefing?probe=true", timeout=10)
        assert rp.status_code == 200
        data = rp.json()["data"]
        assert data.get("cached") is False, f"Expected cached:false after delete, got: {data}"
        assert data.get("briefing") is None

    def test_delete_then_get_regenerates(self, session):
        """After DELETE, the next GET should regenerate with cached:False."""
        # clear
        session.delete(f"{API}/ai/daily-briefing", timeout=10)
        # regenerate
        r2 = session.get(f"{API}/ai/daily-briefing", timeout=90)
        assert r2.status_code == 200
        b2 = r2.json()["data"]
        assert b2["cached"] is False, f"Expected cached:false for fresh generation, got: {b2}"
        assert isinstance(b2["briefing"], str) and len(b2["briefing"]) > 20

    def test_delete_without_existing_cache_is_idempotent(self, session):
        session.delete(f"{API}/ai/daily-briefing", timeout=10)
        r = session.delete(f"{API}/ai/daily-briefing", timeout=10)
        assert r.status_code == 200
        assert r.json().get("success") is True


# ────────── Content / persistence ──────────
class TestContentAndPersistence:
    def test_briefing_mentions_pipeline_context(self, session):
        """Verify briefing references something concrete from the broker's pipeline.
        Pull active cases & client names — at least one should appear in briefing text.
        """
        # Clear and regenerate fresh
        session.delete(f"{API}/ai/daily-briefing", timeout=10)
        # Fetch active cases for context — response is wrapped in {success, data, ...}
        rc = session.get(f"{API}/cases", timeout=10)
        assert rc.status_code == 200
        cases_body = rc.json()
        # Cases may be in data.cases or data list
        cases_data = cases_body.get("data") or cases_body
        if isinstance(cases_data, dict):
            cases = cases_data.get("cases", []) or cases_data.get("items", [])
        elif isinstance(cases_data, list):
            cases = cases_data
        else:
            cases = []

        active_stages = {"new_enquiry", "fact_find", "aip_submitted", "aip_received",
                         "full_application", "valuation", "offer", "exchange"}
        active = [c for c in cases if c.get("stage") in active_stages]

        rb = session.get(f"{API}/ai/daily-briefing", timeout=120)
        assert rb.status_code == 200
        briefing = rb.json()["data"]["briefing"].lower()

        if active:
            # Try to find at least one client first-name or last-name in briefing
            found = False
            for c in active:
                name = (c.get("client_name") or "").lower()
                if not name:
                    continue
                parts = [p for p in name.split() if len(p) > 2]
                if any(p in briefing for p in parts):
                    found = True
                    break
            # Soft assertion — Claude prompt includes names, so should appear
            assert found, f"Briefing didn't mention any active client name. Active clients: {[c.get('client_name') for c in active]}"
        else:
            # No active cases — briefing should still be non-empty
            assert len(briefing) > 20

    def test_briefing_has_four_sections(self, session):
        """Briefing text must include all 4 section labels for frontend parser."""
        r = session.get(f"{API}/ai/daily-briefing?probe=true", timeout=10)
        briefing = r.json()["data"].get("briefing", "") or ""
        if not briefing:
            # Generate one
            rg = session.get(f"{API}/ai/daily-briefing", timeout=90)
            briefing = rg.json()["data"]["briefing"]

        text_upper = briefing.upper()
        for label in ["SUMMARY:", "TODAY'S PRIORITIES:", "WATCH LIST:", "CLOSING NOTE:"]:
            assert label in text_upper, \
                f"Section label '{label}' not found in briefing text"


# ────────── Regression: AI #1 & #2 still work ──────────
class TestRegression:
    def test_borrower_score_still_works(self, session):
        rc = session.get(f"{API}/cases", timeout=10)
        cases_body = rc.json()
        cases_data = cases_body.get("data") or cases_body
        if isinstance(cases_data, dict):
            cases = cases_data.get("cases", []) or []
        elif isinstance(cases_data, list):
            cases = cases_data
        else:
            cases = []

        if not cases:
            pytest.skip("No cases available")
        case_id = cases[0]["id"]
        rcase = session.get(f"{API}/cases/{case_id}", timeout=10)
        case_data = rcase.json().get("data") or rcase.json()
        client = case_data.get("client") or {}
        client_id = client.get("id")
        if not client_id:
            pytest.skip("No client on case")
        r = session.post(f"{API}/ai/borrower-score", json={"client_id": client_id}, timeout=60)
        assert r.status_code == 200
        d = r.json()["data"]
        assert "score" in d and "classification" in d and "summary" in d

    def test_lender_match_still_works(self, session):
        rc = session.get(f"{API}/cases", timeout=10)
        cases_body = rc.json()
        cases_data = cases_body.get("data") or cases_body
        if isinstance(cases_data, dict):
            cases = cases_data.get("cases", []) or []
        elif isinstance(cases_data, list):
            cases = cases_data
        else:
            cases = []

        if not cases:
            pytest.skip("No cases available")
        case_id = cases[0]["id"]
        r = session.post(f"{API}/ai/lender-match", json={"case_id": case_id}, timeout=90)
        assert r.status_code == 200
        d = r.json()["data"]
        assert "matches" in d and "eligible_count" in d and "total_lenders" in d

    def test_dashboard_stats_still_works(self, session):
        r = session.get(f"{API}/dashboard/stats", timeout=10)
        assert r.status_code == 200
        body = r.json()
        # Stats may be at top-level or under data
        d = body.get("data") or body
        for k in ["clients_count", "cases_count", "commissions", "pipeline", "alerts"]:
            assert k in d, f"Dashboard stats missing key {k}. Got: {d.keys()}"
