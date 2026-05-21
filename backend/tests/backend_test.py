"""
BrokerOS Backend API Tests
Covers: auth, clients, cases, lenders, commissions, dashboard, notes, settings
"""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://commission-track-28.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@brokeros.com"
ADMIN_PASSWORD = "Admin123!"


# ---------- Fixtures ----------
@pytest.fixture(scope="session")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    assert "access_token" in s.cookies, "access_token cookie not set"
    return s


@pytest.fixture(scope="session")
def created_resources():
    return {"client_ids": [], "case_ids": [], "lender_ids": [], "commission_ids": []}


# ---------- Health ----------
def test_health():
    r = requests.get(f"{API}/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


# ---------- Auth ----------
class TestAuth:
    def test_login_success_sets_httponly_cookies(self):
        s = requests.Session()
        r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == ADMIN_EMAIL
        assert data["role"] == "admin"
        # Check Set-Cookie for HttpOnly
        cookies_headers = r.headers.get("set-cookie", "")
        assert "HttpOnly" in cookies_headers or "httponly" in cookies_headers.lower()
        assert "access_token" in s.cookies

    def test_login_invalid_password(self):
        s = requests.Session()
        r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": "wrongpass"})
        assert r.status_code == 401

    def test_auth_me(self, admin_session):
        r = admin_session.get(f"{API}/auth/me")
        assert r.status_code == 200
        assert r.json()["email"] == ADMIN_EMAIL

    def test_unauthenticated_access(self):
        r = requests.get(f"{API}/auth/me")
        assert r.status_code == 401

    def test_register_new_user_and_onboarding(self):
        s = requests.Session()
        email = f"TEST_user_{uuid.uuid4().hex[:8]}@example.com"
        r = s.post(f"{API}/auth/register", json={
            "email": email, "password": "TestPass123!", "first_name": "Test", "last_name": "User"
        })
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["email"] == email.lower()
        assert data["onboarding_completed"] is False
        # complete onboarding
        r2 = s.put(f"{API}/users/me/onboarding")
        assert r2.status_code == 200
        # verify
        me = s.get(f"{API}/auth/me").json()
        assert me["onboarding_completed"] is True

    def test_register_duplicate_email(self):
        s = requests.Session()
        r = s.post(f"{API}/auth/register", json={
            "email": ADMIN_EMAIL, "password": "Whatever1!", "first_name": "X", "last_name": "Y"
        })
        assert r.status_code == 400

    def test_logout(self):
        s = requests.Session()
        s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        r = s.post(f"{API}/auth/logout")
        assert r.status_code == 200


# ---------- Clients ----------
class TestClients:
    def test_create_client(self, admin_session, created_resources):
        payload = {
            "first_name": "TEST_John", "last_name": "Doe",
            "email": f"TEST_john_{uuid.uuid4().hex[:6]}@test.com",
            "phone": "07700900123", "employment_type": "employed",
            "annual_income": 50000, "credit_profile": "clean"
        }
        r = admin_session.post(f"{API}/clients", json=payload)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "id" in data and data["first_name"] == "TEST_John"
        created_resources["client_ids"].append(data["id"])

    def test_list_clients(self, admin_session):
        r = admin_session.get(f"{API}/clients")
        assert r.status_code == 200
        assert "clients" in r.json()

    def test_get_client(self, admin_session, created_resources):
        cid = created_resources["client_ids"][0]
        r = admin_session.get(f"{API}/clients/{cid}")
        assert r.status_code == 200
        assert r.json()["id"] == cid

    def test_update_client(self, admin_session, created_resources):
        cid = created_resources["client_ids"][0]
        r = admin_session.put(f"{API}/clients/{cid}", json={
            "first_name": "TEST_Updated", "last_name": "Doe", "employment_type": "employed"
        })
        assert r.status_code == 200
        # Verify persistence
        r2 = admin_session.get(f"{API}/clients/{cid}")
        assert r2.json()["first_name"] == "TEST_Updated"


# ---------- Lenders ----------
class TestLenders:
    def test_create_lender(self, admin_session, created_resources):
        r = admin_session.post(f"{API}/lenders", json={
            "name": "TEST_Lender_X", "bdm_name": "Jane BDM",
            "bdm_email": "bdm@lender.com", "proc_fee_purchase": 0.4,
            "proc_fee_remortgage": 0.35, "max_ltv": 95, "min_loan": 25000, "max_loan": 1000000
        })
        assert r.status_code == 200
        data = r.json()
        created_resources["lender_ids"].append(data["id"])
        assert data["bdm_name"] == "Jane BDM"

    def test_list_lenders(self, admin_session):
        r = admin_session.get(f"{API}/lenders")
        assert r.status_code == 200
        assert "lenders" in r.json()

    def test_update_lender(self, admin_session, created_resources):
        lid = created_resources["lender_ids"][0]
        r = admin_session.put(f"{API}/lenders/{lid}", json={
            "name": "TEST_Lender_X_Updated", "proc_fee_purchase": 0.5
        })
        assert r.status_code == 200
        assert r.json()["name"] == "TEST_Lender_X_Updated"


# ---------- Cases ----------
class TestCases:
    def test_create_case_with_ltv(self, admin_session, created_resources):
        client_id = created_resources["client_ids"][0]
        lender_id = created_resources["lender_ids"][0]
        r = admin_session.post(f"{API}/cases", json={
            "client_id": client_id, "mortgage_type": "residential",
            "stage": "new_enquiry", "loan_amount": 200000, "property_value": 250000,
            "term_years": 25, "lender_id": lender_id, "rate_type": "fixed", "rate_percent": 4.5
        })
        assert r.status_code == 200, r.text
        data = r.json()
        # LTV = 200000/250000 * 100 = 80.0
        assert data["ltv"] == 80.0, f"LTV mismatch: {data.get('ltv')}"
        created_resources["case_ids"].append(data["id"])

    def test_create_case_invalid_client(self, admin_session):
        r = admin_session.post(f"{API}/cases", json={
            "client_id": "non-existent-id", "stage": "new_enquiry"
        })
        assert r.status_code == 404

    def test_list_cases_with_enrichment(self, admin_session):
        r = admin_session.get(f"{API}/cases")
        assert r.status_code == 200
        cases = r.json()["cases"]
        assert len(cases) >= 1
        # check enrichment
        assert "client_name" in cases[0]

    def test_update_case_stage(self, admin_session, created_resources):
        case_id = created_resources["case_ids"][0]
        r = admin_session.patch(f"{API}/cases/{case_id}/stage", params={"stage": "fact_find"})
        assert r.status_code == 200
        assert r.json()["stage"] == "fact_find"

    def test_get_case_detail(self, admin_session, created_resources):
        case_id = created_resources["case_ids"][0]
        r = admin_session.get(f"{API}/cases/{case_id}")
        assert r.status_code == 200
        data = r.json()
        assert "client" in data

    def test_case_note_create_and_list(self, admin_session, created_resources):
        case_id = created_resources["case_ids"][0]
        r = admin_session.post(f"{API}/notes", json={"case_id": case_id, "content": "TEST note"})
        assert r.status_code == 200
        r2 = admin_session.get(f"{API}/cases/{case_id}/notes")
        assert r2.status_code == 200
        assert len(r2.json()["notes"]) >= 1


# ---------- Commissions ----------
class TestCommissions:
    def test_create_commission(self, admin_session, created_resources):
        case_id = created_resources["case_ids"][0]
        r = admin_session.post(f"{API}/commissions", json={
            "case_id": case_id, "expected_amount": 1200, "status": "pending"
        })
        assert r.status_code == 200
        data = r.json()
        created_resources["commission_ids"].append(data["id"])

    def test_list_commissions_enriched(self, admin_session):
        r = admin_session.get(f"{API}/commissions")
        assert r.status_code == 200
        comms = r.json()["commissions"]
        assert len(comms) >= 1
        assert "client_name" in comms[0]
        assert "lender_name" in comms[0]


# ---------- Dashboard ----------
class TestDashboard:
    def test_dashboard_stats(self, admin_session):
        r = admin_session.get(f"{API}/dashboard/stats")
        assert r.status_code == 200
        data = r.json()
        for key in ("clients_count", "cases_count", "pipeline", "commissions"):
            assert key in data
        assert "pending" in data["commissions"]


# ---------- Settings ----------
class TestSettings:
    def test_update_profile_fca(self, admin_session):
        r = admin_session.put(f"{API}/users/me", json={"fca_number": "FCA-TEST-001"})
        assert r.status_code == 200
        assert r.json().get("fca_number") == "FCA-TEST-001"

    def test_change_password_wrong_current(self, admin_session):
        r = admin_session.put(f"{API}/users/me", json={
            "current_password": "WRONG_PWD",
            "new_password": "NewPass123!"
        })
        assert r.status_code == 400


# ---------- Cleanup ----------
def test_zzz_cleanup(admin_session, created_resources):
    for cid in created_resources["commission_ids"]:
        admin_session.delete(f"{API}/commissions/{cid}")
    for cid in created_resources["case_ids"]:
        admin_session.delete(f"{API}/cases/{cid}")
    for cid in created_resources["lender_ids"]:
        admin_session.delete(f"{API}/lenders/{cid}")
    for cid in created_resources["client_ids"]:
        admin_session.delete(f"{API}/clients/{cid}")
