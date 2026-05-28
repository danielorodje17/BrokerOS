"""
BrokerOS Phase 1 New Features Tests
Covers:
- Atomic Invoice Sequence (GET /api/commissions/{id}/invoice)
- Dashboard Enhancements: alerts + recent_cases in /api/dashboard/stats
- Clawback Risk Tab: GET /api/commissions/clawback-risk
"""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://daily-broker-brief.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@brokeros.com"
ADMIN_PASSWORD = "Admin123!"


# ---------- Fixtures ----------
@pytest.fixture(scope="module")
def auth_session():
    """Returns authenticated session for admin."""
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return s


# ========== DASHBOARD STATS - ALERTS + RECENT CASES ==========
class TestDashboardStatsEnhancements:
    """Tests for dashboard stats endpoint with alerts and recent_cases fields."""

    def test_dashboard_stats_returns_200(self, auth_session):
        """Dashboard stats endpoint returns 200."""
        r = auth_session.get(f"{API}/dashboard/stats")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"

    def test_dashboard_stats_has_alerts_field(self, auth_session):
        """Dashboard stats response contains 'alerts' object."""
        r = auth_session.get(f"{API}/dashboard/stats")
        assert r.status_code == 200
        data = r.json()
        assert "alerts" in data, f"'alerts' key missing from response: {data.keys()}"

    def test_dashboard_stats_alerts_has_required_keys(self, auth_session):
        """Alerts object has overdue_count, due_soon_count, clawback_risk_count."""
        r = auth_session.get(f"{API}/dashboard/stats")
        assert r.status_code == 200
        alerts = r.json().get("alerts", {})
        assert "overdue_count" in alerts, f"overdue_count missing from alerts: {alerts}"
        assert "due_soon_count" in alerts, f"due_soon_count missing from alerts: {alerts}"
        assert "clawback_risk_count" in alerts, f"clawback_risk_count missing from alerts: {alerts}"

    def test_dashboard_stats_alerts_counts_are_ints(self, auth_session):
        """Alert counts should be non-negative integers."""
        r = auth_session.get(f"{API}/dashboard/stats")
        assert r.status_code == 200
        alerts = r.json().get("alerts", {})
        assert isinstance(alerts.get("overdue_count"), int), "overdue_count is not an int"
        assert isinstance(alerts.get("due_soon_count"), int), "due_soon_count is not an int"
        assert isinstance(alerts.get("clawback_risk_count"), int), "clawback_risk_count is not an int"
        assert alerts.get("overdue_count") >= 0
        assert alerts.get("due_soon_count") >= 0
        assert alerts.get("clawback_risk_count") >= 0

    def test_dashboard_stats_has_recent_cases_field(self, auth_session):
        """Dashboard stats response contains 'recent_cases' list."""
        r = auth_session.get(f"{API}/dashboard/stats")
        assert r.status_code == 200
        data = r.json()
        assert "recent_cases" in data, f"'recent_cases' key missing from response: {data.keys()}"
        assert isinstance(data["recent_cases"], list), "recent_cases should be a list"

    def test_dashboard_stats_recent_cases_max_5(self, auth_session):
        """Recent cases should not exceed 5 items."""
        r = auth_session.get(f"{API}/dashboard/stats")
        assert r.status_code == 200
        recent = r.json().get("recent_cases", [])
        assert len(recent) <= 5, f"recent_cases returned {len(recent)} items (max 5 expected)"

    def test_dashboard_stats_recent_cases_fields(self, auth_session):
        """Each recent case should have required fields."""
        r = auth_session.get(f"{API}/dashboard/stats")
        assert r.status_code == 200
        recent = r.json().get("recent_cases", [])
        if len(recent) == 0:
            pytest.skip("No recent cases available to validate fields")
        for case in recent:
            assert "id" in case, f"'id' missing from recent case: {case.keys()}"
            assert "client_name" in case, f"'client_name' missing from recent case: {case.keys()}"
            assert "lender_name" in case, f"'lender_name' missing from recent case: {case.keys()}"
            assert "stage" in case, f"'stage' missing from recent case: {case.keys()}"
            assert "loan_amount" in case, f"'loan_amount' missing from recent case: {case.keys()}"

    def test_dashboard_stats_existing_fields_intact(self, auth_session):
        """Existing stats fields (clients_count, cases_count, pipeline, commissions) still present."""
        r = auth_session.get(f"{API}/dashboard/stats")
        assert r.status_code == 200
        data = r.json()
        assert "clients_count" in data
        assert "cases_count" in data
        assert "pipeline" in data
        assert "commissions" in data


# ========== CLAWBACK RISK ENDPOINT ==========
class TestClawbackRiskEndpoint:
    """Tests for GET /api/commissions/clawback-risk."""

    def test_clawback_risk_returns_200(self, auth_session):
        """Clawback risk endpoint returns 200."""
        r = auth_session.get(f"{API}/commissions/clawback-risk")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"

    def test_clawback_risk_response_structure(self, auth_session):
        """Response has commissions (list) and total (int)."""
        r = auth_session.get(f"{API}/commissions/clawback-risk")
        assert r.status_code == 200
        data = r.json()
        assert "commissions" in data, f"'commissions' key missing: {data.keys()}"
        assert "total" in data, f"'total' key missing: {data.keys()}"
        assert isinstance(data["commissions"], list)
        assert isinstance(data["total"], int)

    def test_clawback_risk_total_matches_list(self, auth_session):
        """total field matches len(commissions)."""
        r = auth_session.get(f"{API}/commissions/clawback-risk")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == len(data["commissions"]), \
            f"total={data['total']} but commissions list has {len(data['commissions'])} items"

    def test_clawback_risk_items_have_required_fields(self, auth_session):
        """Each clawback item should have enriched fields."""
        r = auth_session.get(f"{API}/commissions/clawback-risk")
        assert r.status_code == 200
        items = r.json().get("commissions", [])
        if not items:
            pytest.skip("No clawback risk items available to validate fields")
        for item in items:
            assert "client_name" in item, f"client_name missing: {item.keys()}"
            assert "lender_name" in item, f"lender_name missing: {item.keys()}"
            assert "days_remaining" in item, f"days_remaining missing: {item.keys()}"
            assert "clawback_risk_until_formatted" in item, f"clawback_risk_until_formatted missing: {item.keys()}"
            assert "status" in item, f"status missing: {item.keys()}"

    def test_clawback_risk_days_remaining_positive(self, auth_session):
        """All returned items should have days_remaining > 0 (future date)."""
        r = auth_session.get(f"{API}/commissions/clawback-risk")
        assert r.status_code == 200
        items = r.json().get("commissions", [])
        for item in items:
            days = item.get("days_remaining")
            if days is not None:
                assert days > 0, f"Clawback item has days_remaining={days} (should be future, >0)"

    def test_clawback_risk_unauthorized_returns_401(self):
        """Unauthenticated request returns 401."""
        s = requests.Session()
        r = s.get(f"{API}/commissions/clawback-risk")
        assert r.status_code == 401, f"Expected 401, got {r.status_code}"


# ========== CLAWBACK WITH SEED DATA ==========
class TestClawbackWithData:
    """Create a commission with future clawback_risk_until and verify it appears in clawback endpoint."""

    @pytest.fixture(scope="class")
    def commission_with_clawback(self, auth_session):
        """Creates a test commission with a future clawback date, yields it, then cleans up."""
        # Get existing case
        cases_r = auth_session.get(f"{API}/cases?limit=10")
        assert cases_r.status_code == 200, "Could not fetch cases"
        cases = cases_r.json().get("cases", [])
        if not cases:
            pytest.skip("No cases available to create test commission")
        case_id = cases[0]["id"]

        # Create commission with future clawback date
        payload = {
            "case_id": case_id,
            "expected_amount": 2500.0,
            "expected_payment_date": "2027-06-01",
            "received_amount": 2500.0,
            "received_date": "2025-06-01",
            "status": "received",
            "clawback_risk_until": "2027-06-01"
        }
        create_r = auth_session.post(f"{API}/commissions", json=payload)
        assert create_r.status_code == 200, f"Failed to create commission: {create_r.text}"
        commission = create_r.json()
        commission_id = commission.get("id")

        yield commission

        # Cleanup
        if commission_id:
            auth_session.delete(f"{API}/commissions/{commission_id}")

    def test_clawback_commission_appears_in_endpoint(self, auth_session, commission_with_clawback):
        """Commission with future clawback_risk_until appears in /clawback-risk."""
        commission_id = commission_with_clawback.get("id")
        r = auth_session.get(f"{API}/commissions/clawback-risk")
        assert r.status_code == 200
        ids = [c.get("id") for c in r.json().get("commissions", [])]
        assert commission_id in ids, f"Created commission {commission_id} not found in clawback-risk list"

    def test_clawback_commission_days_remaining_correct(self, auth_session, commission_with_clawback):
        """Days remaining is calculated correctly (positive future days)."""
        commission_id = commission_with_clawback.get("id")
        r = auth_session.get(f"{API}/commissions/clawback-risk")
        assert r.status_code == 200
        items = {c.get("id"): c for c in r.json().get("commissions", [])}
        assert commission_id in items, "Commission not in clawback-risk list"
        item = items[commission_id]
        assert item.get("days_remaining") is not None
        assert item.get("days_remaining") > 0, f"Expected positive days_remaining, got {item.get('days_remaining')}"
        # 2027-06-01 is well into the future, should be > 365 days
        assert item.get("days_remaining") > 365, f"Expected >365 days for 2027 date, got {item.get('days_remaining')}"

    def test_clawback_commission_formatted_date(self, auth_session, commission_with_clawback):
        """clawback_risk_until_formatted is in DD/MM/YYYY format."""
        commission_id = commission_with_clawback.get("id")
        r = auth_session.get(f"{API}/commissions/clawback-risk")
        assert r.status_code == 200
        items = {c.get("id"): c for c in r.json().get("commissions", [])}
        assert commission_id in items
        formatted = items[commission_id].get("clawback_risk_until_formatted")
        assert formatted == "01/06/2027", f"Expected '01/06/2027', got '{formatted}'"


# ========== INVOICE SEQUENCE ==========
class TestAtomicInvoiceSequence:
    """Tests for atomic invoice sequence generation."""

    def test_invoice_generates_correct_format(self, auth_session):
        """Invoice number follows INV-YYYY-NNNN format."""
        # Get a commission to invoice
        comms_r = auth_session.get(f"{API}/commissions?limit=20")
        assert comms_r.status_code == 200
        comms = comms_r.json().get("commissions", [])
        if not comms:
            pytest.skip("No commissions available to test invoice generation")

        commission_id = comms[0]["id"]
        r = auth_session.get(f"{API}/commissions/{commission_id}/invoice")
        assert r.status_code == 200, f"Invoice generation failed: {r.status_code} {r.text[:300]}"

        # Check content type is PDF
        assert "application/pdf" in r.headers.get("content-type", ""), \
            f"Expected PDF content type, got {r.headers.get('content-type')}"

        # Check invoice number header
        invoice_number = r.headers.get("x-invoice-number") or r.headers.get("X-Invoice-Number")
        assert invoice_number is not None, "X-Invoice-Number header missing from response"

        import re
        assert re.match(r"INV-\d{4}-\d{4}", invoice_number), \
            f"Invoice number '{invoice_number}' doesn't match INV-YYYY-NNNN format"

    def test_invoice_number_increments(self, auth_session):
        """Two consecutive invoice generations produce different numbers."""
        comms_r = auth_session.get(f"{API}/commissions?limit=20")
        assert comms_r.status_code == 200
        comms = comms_r.json().get("commissions", [])
        if len(comms) < 2:
            pytest.skip("Need at least 2 commissions to test invoice increment")

        # Generate two invoices
        r1 = auth_session.get(f"{API}/commissions/{comms[0]['id']}/invoice")
        r2 = auth_session.get(f"{API}/commissions/{comms[1]['id']}/invoice")
        assert r1.status_code == 200
        assert r2.status_code == 200

        inv1 = r1.headers.get("x-invoice-number") or r1.headers.get("X-Invoice-Number")
        inv2 = r2.headers.get("x-invoice-number") or r2.headers.get("X-Invoice-Number")
        assert inv1 != inv2, f"Expected different invoice numbers, both got '{inv1}'"
