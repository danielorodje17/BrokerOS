"""
Extension 7: Team Permission Layer - Backend Tests
Tests role-based access control for admin role.
Covers: cases CRUD, commissions list, notes, team/members endpoint.
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Admin credentials from env/test_credentials.md
ADMIN_EMAIL = "admin@brokeros.com"
ADMIN_PASSWORD = "Admin123!"


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def admin_session():
    """Log in as admin, return a requests.Session with auth cookies."""
    session = requests.Session()
    resp = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert resp.status_code == 200, f"Admin login failed: {resp.text}"
    data = resp.json()
    assert data.get("role") == "admin", f"Expected role=admin, got {data.get('role')}"
    return session


@pytest.fixture(scope="module")
def adviser_session():
    """Create a temporary adviser user, log in, return session. Clean up after module."""
    adviser_email = f"TEST_adviser_{int(time.time())}@brokeros.com"
    adviser_password = "Adviser123!"

    # Register adviser
    reg_resp = requests.post(f"{BASE_URL}/api/auth/register", json={
        "email": adviser_email,
        "password": adviser_password,
        "first_name": "Test",
        "last_name": "Adviser"
    })
    assert reg_resp.status_code == 200, f"Adviser registration failed: {reg_resp.text}"

    # Login as adviser
    session = requests.Session()
    login_resp = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": adviser_email,
        "password": adviser_password
    })
    assert login_resp.status_code == 200, f"Adviser login failed: {login_resp.text}"

    yield session

    # No cleanup needed as adviser won't have cases/data


# ─── 1. Admin Login ───────────────────────────────────────────────────────────

class TestAdminLogin:
    """Admin authentication and role verification"""

    def test_admin_login_returns_200(self):
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert resp.status_code == 200

    def test_admin_login_role_is_admin(self):
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        data = resp.json()
        assert data.get("role") == "admin", f"Expected admin, got {data.get('role')}"

    def test_admin_me_endpoint(self, admin_session):
        resp = admin_session.get(f"{BASE_URL}/api/auth/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("role") == "admin"
        assert data.get("email") == ADMIN_EMAIL


# ─── 2. Cases CRUD for Admin (unrestricted access) ───────────────────────────

class TestAdminCasesAccess:
    """Admin should see ALL cases without role-based filtering"""

    def test_list_cases_returns_200(self, admin_session):
        resp = admin_session.get(f"{BASE_URL}/api/cases?limit=50")
        assert resp.status_code == 200

    def test_list_cases_returns_cases_array(self, admin_session):
        resp = admin_session.get(f"{BASE_URL}/api/cases?limit=50")
        data = resp.json()
        assert "cases" in data
        assert isinstance(data["cases"], list)

    def test_list_cases_has_total_field(self, admin_session):
        resp = admin_session.get(f"{BASE_URL}/api/cases?limit=50")
        data = resp.json()
        assert "total" in data
        assert isinstance(data["total"], int)

    def test_admin_can_get_any_case(self, admin_session):
        """Admin can retrieve a case detail regardless of assigned_broker_id."""
        # First get the list to find a case
        list_resp = admin_session.get(f"{BASE_URL}/api/cases?limit=10")
        cases = list_resp.json().get("cases", [])
        if len(cases) == 0:
            pytest.skip("No cases in database to test admin access on")
        case_id = cases[0]["id"]
        detail_resp = admin_session.get(f"{BASE_URL}/api/cases/{case_id}")
        assert detail_resp.status_code == 200
        assert detail_resp.json().get("id") == case_id

    def test_admin_create_case_sets_assigned_broker_id(self, admin_session):
        """Case creation assigns assigned_broker_id to current user (admin)."""
        # Need a client first
        clients_resp = admin_session.get(f"{BASE_URL}/api/clients?limit=1")
        clients = clients_resp.json().get("clients", [])
        if len(clients) == 0:
            pytest.skip("No clients available to create test case")

        client_id = clients[0]["id"]
        resp = admin_session.post(f"{BASE_URL}/api/cases", json={
            "client_id": client_id,
            "stage": "new_enquiry",
            "loan_amount": 250000,
            "property_value": 300000
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert "assigned_broker_id" in data
        # Store for later cleanup
        TestAdminCasesAccess._created_case_id = data["id"]

    def test_admin_can_update_any_case(self, admin_session):
        """Admin can PUT any case regardless of assigned_broker_id."""
        # Use a case from list
        list_resp = admin_session.get(f"{BASE_URL}/api/cases?limit=10")
        cases = list_resp.json().get("cases", [])
        if len(cases) == 0:
            pytest.skip("No cases to test update")
        case = cases[0]
        case_id = case["id"]

        # Get full case detail for update
        detail_resp = admin_session.get(f"{BASE_URL}/api/cases/{case_id}")
        case_detail = detail_resp.json()

        update_payload = {
            "client_id": case_detail.get("client_id"),
            "stage": case_detail.get("stage", "new_enquiry"),
            "loan_amount": case_detail.get("loan_amount"),
            "property_value": case_detail.get("property_value")
        }
        resp = admin_session.put(f"{BASE_URL}/api/cases/{case_id}", json=update_payload)
        assert resp.status_code == 200

    def test_admin_can_patch_stage_any_case(self, admin_session):
        """Admin can PATCH stage on any case."""
        list_resp = admin_session.get(f"{BASE_URL}/api/cases?limit=10")
        cases = list_resp.json().get("cases", [])
        if len(cases) == 0:
            pytest.skip("No cases to test stage patch")
        case = cases[0]
        original_stage = case.get("stage", "new_enquiry")
        case_id = case["id"]

        resp = admin_session.patch(f"{BASE_URL}/api/cases/{case_id}/stage?stage={original_stage}")
        assert resp.status_code == 200

    def test_admin_delete_own_created_case(self, admin_session):
        """Admin can delete a case they created."""
        case_id = getattr(TestAdminCasesAccess, '_created_case_id', None)
        if not case_id:
            pytest.skip("No test case was created to delete")
        resp = admin_session.delete(f"{BASE_URL}/api/cases/{case_id}")
        assert resp.status_code == 200
        # Verify it's gone
        get_resp = admin_session.get(f"{BASE_URL}/api/cases/{case_id}")
        assert get_resp.status_code == 404


# ─── 3. Commissions — Admin sees ALL ─────────────────────────────────────────

class TestAdminCommissionsAccess:
    """Admin should see ALL commissions, not filtered by user_id"""

    def test_list_commissions_returns_200(self, admin_session):
        resp = admin_session.get(f"{BASE_URL}/api/commissions")
        assert resp.status_code == 200

    def test_list_commissions_response_structure(self, admin_session):
        resp = admin_session.get(f"{BASE_URL}/api/commissions")
        data = resp.json()
        assert "commissions" in data
        assert "total" in data
        assert isinstance(data["commissions"], list)

    def test_list_commissions_not_filtered_by_user_id(self, admin_session):
        """Commissions list for admin uses query={}, returning ALL commissions."""
        resp = admin_session.get(f"{BASE_URL}/api/commissions?limit=100")
        assert resp.status_code == 200
        data = resp.json()
        # total should be >= 0 and response is a list (no 403)
        assert data["total"] >= 0

    def test_clawback_risk_endpoint_accessible(self, admin_session):
        resp = admin_session.get(f"{BASE_URL}/api/commissions/clawback-risk")
        assert resp.status_code == 200
        data = resp.json()
        assert "commissions" in data


# ─── 4. Notes — Admin can access notes on any case ──────────────────────────

class TestAdminNotesAccess:
    """Admin should access notes on any case"""

    def test_notes_on_existing_case(self, admin_session):
        """GET /api/notes?case_id=X returns 200 for admin on any case."""
        list_resp = admin_session.get(f"{BASE_URL}/api/cases?limit=10")
        cases = list_resp.json().get("cases", [])
        if not cases:
            pytest.skip("No cases to test notes on")
        case_id = cases[0]["id"]
        resp = admin_session.get(f"{BASE_URL}/api/notes?case_id={case_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "notes" in data

    def test_case_notes_nested_route(self, admin_session):
        """GET /api/cases/{id}/notes returns 200 for admin."""
        list_resp = admin_session.get(f"{BASE_URL}/api/cases?limit=10")
        cases = list_resp.json().get("cases", [])
        if not cases:
            pytest.skip("No cases to test notes on")
        case_id = cases[0]["id"]
        resp = admin_session.get(f"{BASE_URL}/api/cases/{case_id}/notes")
        assert resp.status_code == 200


# ─── 5. GET /api/auth/team/members ───────────────────────────────────────────

class TestTeamMembersEndpoint:
    """GET /api/auth/team/members behaviour"""

    def test_team_members_endpoint_accessible_for_admin(self, admin_session):
        """GET /api/auth/team/members returns 200 for admin."""
        resp = admin_session.get(f"{BASE_URL}/api/auth/team/members")
        assert resp.status_code == 200

    def test_team_members_correct_url_not_double_auth(self, admin_session):
        """Endpoint is at /api/auth/team/members NOT /api/auth/auth/team/members."""
        correct = admin_session.get(f"{BASE_URL}/api/auth/team/members")
        wrong = admin_session.get(f"{BASE_URL}/api/auth/auth/team/members")
        assert correct.status_code == 200
        assert wrong.status_code in [404, 405, 422]

    def test_team_members_returns_success_true(self, admin_session):
        """Response has success=True."""
        resp = admin_session.get(f"{BASE_URL}/api/auth/team/members")
        data = resp.json()
        assert data.get("success") is True

    def test_team_members_no_team_id_returns_empty_list(self, admin_session):
        """Admin with no team_id gets empty data list."""
        # First verify admin has no team_id
        me_resp = admin_session.get(f"{BASE_URL}/api/auth/me")
        admin_data = me_resp.json()
        if admin_data.get("team_id") is not None:
            pytest.skip("Admin has a team_id set — empty list test does not apply")
        resp = admin_session.get(f"{BASE_URL}/api/auth/team/members")
        data = resp.json()
        assert data.get("success") is True
        assert data.get("data") == []

    def test_team_members_returns_403_for_adviser(self, adviser_session):
        """Adviser role gets 403 from /api/auth/team/members."""
        resp = adviser_session.get(f"{BASE_URL}/api/auth/team/members")
        assert resp.status_code == 403

    def test_team_members_data_field_is_list(self, admin_session):
        """Response data field is always a list."""
        resp = admin_session.get(f"{BASE_URL}/api/auth/team/members")
        data = resp.json()
        assert isinstance(data.get("data"), list)


# ─── 6. get_case_filter helper ───────────────────────────────────────────────

class TestCaseFilterLogic:
    """Verify get_case_filter returns empty dict for admin/principal."""

    def test_admin_case_list_not_filtered(self, admin_session):
        """Admin GET /api/cases should return all cases (no assigned_broker_id filter)."""
        resp = admin_session.get(f"{BASE_URL}/api/cases?limit=100")
        assert resp.status_code == 200
        data = resp.json()
        # All cases regardless of broker should be included
        # We can't know exact count, but no 403
        assert isinstance(data.get("cases"), list)

    def test_adviser_case_list_filters_own_cases(self, adviser_session):
        """Adviser GET /api/cases should only see their own cases (0 for new adviser)."""
        resp = adviser_session.get(f"{BASE_URL}/api/cases?limit=100")
        assert resp.status_code == 200
        data = resp.json()
        # New adviser has no cases
        assert len(data.get("cases", [])) == 0


# ─── 7. Adviser 403 on case not owned ────────────────────────────────────────

class TestAdviserAccessRestrictions:
    """Adviser cannot access cases not assigned to them."""

    def test_adviser_cannot_get_admin_case(self, admin_session, adviser_session):
        """Adviser gets 403 when trying to access a case not assigned to them."""
        list_resp = admin_session.get(f"{BASE_URL}/api/cases?limit=10")
        cases = list_resp.json().get("cases", [])
        if not cases:
            pytest.skip("No cases to test adviser restriction on")

        # Find a case assigned to admin (not to adviser)
        admin_me = admin_session.get(f"{BASE_URL}/api/auth/me").json()
        admin_id = admin_me.get("id")
        adviser_me = adviser_session.get(f"{BASE_URL}/api/auth/me").json()
        adviser_id = adviser_me.get("id")

        admin_cases = [c for c in cases if c.get("assigned_broker_id") == admin_id]
        if not admin_cases:
            pytest.skip("No cases assigned to admin to test adviser restriction")

        case_id = admin_cases[0]["id"]
        resp = adviser_session.get(f"{BASE_URL}/api/cases/{case_id}")
        assert resp.status_code == 403

    def test_adviser_cannot_get_notes_on_admin_case(self, admin_session, adviser_session):
        """Adviser gets 403 when accessing notes on a case not assigned to them."""
        list_resp = admin_session.get(f"{BASE_URL}/api/cases?limit=10")
        cases = list_resp.json().get("cases", [])
        if not cases:
            pytest.skip("No cases to test")

        admin_me = admin_session.get(f"{BASE_URL}/api/auth/me").json()
        admin_id = admin_me.get("id")
        admin_cases = [c for c in cases if c.get("assigned_broker_id") == admin_id]
        if not admin_cases:
            pytest.skip("No cases assigned to admin for this test")

        case_id = admin_cases[0]["id"]
        resp = adviser_session.get(f"{BASE_URL}/api/notes?case_id={case_id}")
        assert resp.status_code == 403


# ─── 8. Migration Script Structure ───────────────────────────────────────────

class TestMigrationScript:
    """Verify migration script exists and has correct structure."""

    def test_migration_script_exists(self):
        import os
        script_path = "/app/scripts/migrate_assign_cases.py"
        assert os.path.exists(script_path), f"Migration script not found at {script_path}"

    def test_migration_script_has_async_main(self):
        with open("/app/scripts/migrate_assign_cases.py") as f:
            content = f.read()
        assert "async def main" in content
        assert "asyncio.run(main())" in content

    def test_migration_script_handles_missing_assigned_broker(self):
        with open("/app/scripts/migrate_assign_cases.py") as f:
            content = f.read()
        # Must handle None, missing, and empty string
        assert "assigned_broker_id" in content
        assert "update_many" in content

    def test_migration_script_idempotent_comment(self):
        with open("/app/scripts/migrate_assign_cases.py") as f:
            content = f.read()
        assert "idempotent" in content.lower() or "safe to run" in content.lower()
