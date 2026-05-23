"""
BrokerOS Extension 3 (Commission Reminders) + Extension 4 (Search) backend tests
"""
import os
import uuid
import pytest
import requests
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@brokeros.com"
ADMIN_PASSWORD = "Admin123!"


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    r = sess.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"Login failed: {r.text}"
    return sess


@pytest.fixture(scope="module")
def seeded(s):
    """Create a client, lender, case + 3 commissions: due_soon, overdue, received."""
    # Client
    cli = s.post(f"{API}/clients", json={
        "first_name": "TESTExt", "last_name": f"User{uuid.uuid4().hex[:6]}",
        "email": f"TEST_ext_{uuid.uuid4().hex[:6]}@example.com"
    })
    assert cli.status_code == 200, cli.text
    client_id = cli.json()["id"]

    # Lender
    lnd = s.post(f"{API}/lenders", json={
        "name": f"TEST Lender {uuid.uuid4().hex[:6]}", "lender_type": "high_street"
    })
    assert lnd.status_code == 200, lnd.text
    lender_id = lnd.json()["id"]

    # Case
    case = s.post(f"{API}/cases", json={
        "client_id": client_id, "lender_id": lender_id,
        "loan_amount": 250000, "stage": "full_application"
    })
    assert case.status_code == 200, case.text
    case_id = case.json()["id"]

    today = datetime.now(timezone.utc).date()

    # Due soon - 7 days from now
    due_soon_date = (today + timedelta(days=7)).isoformat()
    c1 = s.post(f"{API}/commissions", json={
        "case_id": case_id, "expected_amount": 1500.0,
        "expected_payment_date": due_soon_date, "status": "pending"
    })
    assert c1.status_code == 200, c1.text
    due_soon_id = c1.json()["id"]

    # Overdue - 45 days ago
    overdue_date = (today - timedelta(days=45)).isoformat()
    c2 = s.post(f"{API}/commissions", json={
        "case_id": case_id, "expected_amount": 2000.0,
        "expected_payment_date": overdue_date, "status": "pending"
    })
    assert c2.status_code == 200, c2.text
    overdue_id = c2.json()["id"]

    # Received (should be excluded)
    c3 = s.post(f"{API}/commissions", json={
        "case_id": case_id, "expected_amount": 1000.0, "received_amount": 1000.0,
        "expected_payment_date": due_soon_date, "received_date": today.isoformat(),
        "status": "received"
    })
    assert c3.status_code == 200, c3.text
    received_id = c3.json()["id"]

    yield {
        "client_id": client_id, "lender_id": lender_id, "case_id": case_id,
        "due_soon_id": due_soon_id, "overdue_id": overdue_id, "received_id": received_id
    }

    # Cleanup
    for cid in [due_soon_id, overdue_id, received_id]:
        s.delete(f"{API}/commissions/{cid}")
    s.delete(f"{API}/cases/{case_id}")
    s.delete(f"{API}/lenders/{lender_id}")
    s.delete(f"{API}/clients/{client_id}")


# ========== Extension 3: Reminders ==========
class TestReminders:
    def test_reminders_response_shape(self, s, seeded):
        r = s.get(f"{API}/commissions/reminders")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("success") is True
        assert "data" in body
        assert "due_soon" in body["data"]
        assert "overdue" in body["data"]
        assert isinstance(body["data"]["due_soon"], list)
        assert isinstance(body["data"]["overdue"], list)

    def test_due_soon_contains_our_commission(self, s, seeded):
        r = s.get(f"{API}/commissions/reminders")
        ds = r.json()["data"]["due_soon"]
        match = [i for i in ds if i["id"] == seeded["due_soon_id"]]
        assert len(match) == 1
        item = match[0]
        # required keys
        for k in ["id", "client_name", "lender_name", "expected_amount",
                  "expected_payment_date", "days_until_due"]:
            assert k in item, f"missing {k}"
        assert 0 <= item["days_until_due"] <= 14
        assert item["expected_amount"] == 1500.0

    def test_overdue_contains_our_commission(self, s, seeded):
        r = s.get(f"{API}/commissions/reminders")
        od = r.json()["data"]["overdue"]
        match = [i for i in od if i["id"] == seeded["overdue_id"]]
        assert len(match) == 1
        item = match[0]
        for k in ["id", "client_name", "lender_name", "expected_amount",
                  "expected_payment_date", "days_overdue"]:
            assert k in item
        assert item["days_overdue"] > 30
        assert item["expected_amount"] == 2000.0

    def test_received_excluded_from_reminders(self, s, seeded):
        r = s.get(f"{API}/commissions/reminders")
        all_ids = [i["id"] for i in r.json()["data"]["due_soon"]] + \
                  [i["id"] for i in r.json()["data"]["overdue"]]
        assert seeded["received_id"] not in all_ids

    def test_due_soon_sorted_ascending(self, s, seeded):
        r = s.get(f"{API}/commissions/reminders")
        ds = r.json()["data"]["due_soon"]
        days = [i["days_until_due"] for i in ds]
        assert days == sorted(days)

    def test_overdue_sorted_ascending(self, s, seeded):
        r = s.get(f"{API}/commissions/reminders")
        od = r.json()["data"]["overdue"]
        days = [i["days_overdue"] for i in od]
        assert days == sorted(days)


# ========== Extension 4: Cases + Commissions enrichment + invoice persist ==========
class TestEnrichment:
    def test_cases_enriched_with_client_and_lender_name(self, s, seeded):
        r = s.get(f"{API}/cases?limit=100")
        assert r.status_code == 200
        cases = r.json()["cases"]
        ours = [c for c in cases if c["id"] == seeded["case_id"]]
        assert len(ours) == 1
        assert ours[0].get("client_name")
        assert ours[0].get("lender_name")
        assert "TESTExt" in ours[0]["client_name"]

    def test_commissions_enriched(self, s, seeded):
        r = s.get(f"{API}/commissions?limit=100")
        assert r.status_code == 200
        comms = r.json()["commissions"]
        ours = [c for c in comms if c["id"] == seeded["due_soon_id"]]
        assert len(ours) == 1
        c = ours[0]
        assert c.get("client_name")
        assert c.get("lender_name")
        assert c.get("loan_amount") == 250000


class TestInvoicePersistence:
    def test_invoice_persists_invoice_number_on_commission(self, s, seeded):
        # Generate invoice
        r = s.get(f"{API}/commissions/{seeded['due_soon_id']}/invoice")
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        inv_num = r.headers.get("x-invoice-number") or r.headers.get("X-Invoice-Number")
        assert inv_num, "Missing X-Invoice-Number header"
        assert inv_num.startswith("INV-")
        # Now refetch commissions and verify invoice_number persisted
        r2 = s.get(f"{API}/commissions?limit=100")
        comms = r2.json()["commissions"]
        ours = [c for c in comms if c["id"] == seeded["due_soon_id"]]
        assert len(ours) == 1
        assert ours[0].get("invoice_number") == inv_num


# ========== Regression: notes, basic CRUD ==========
class TestRegression:
    def test_notes_for_case(self, s, seeded):
        # Create note
        r = s.post(f"{API}/notes", json={"case_id": seeded["case_id"], "content": "TEST regression note"})
        assert r.status_code == 200, r.text
        # Fetch
        r2 = s.get(f"{API}/notes?case_id={seeded['case_id']}")
        assert r2.status_code == 200
        notes = r2.json().get("notes", r2.json()) if isinstance(r2.json(), dict) else r2.json()
        # accept either {notes: [...]} or [...]
        if isinstance(notes, dict):
            notes = notes.get("notes", [])
        assert any("TEST regression note" in n.get("content", "") for n in notes)

    def test_cases_list_works(self, s, seeded):
        r = s.get(f"{API}/cases?limit=100")
        assert r.status_code == 200
        assert "cases" in r.json()

    def test_dashboard_stats(self, s):
        r = s.get(f"{API}/dashboard/stats")
        assert r.status_code == 200
