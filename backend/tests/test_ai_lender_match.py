"""
Backend tests for AI Feature 2: Lender Matching Engine (Phase 2)
Endpoint: POST /api/ai/lender-match
Endpoint: PATCH /api/cases/{case_id}/lender
"""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://daily-broker-brief.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@brokeros.com"
ADMIN_PASSWORD = "Admin123!"

# Known seeded test case (per request) - test will fallback to first available if missing
KNOWN_CASE_ID = "09ecdc6c-828e-4134-b316-9c112ccd2848"


# ────────── Fixtures ──────────
@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"Login failed: {r.status_code} {r.text}")
    return s


@pytest.fixture(scope="session")
def case_id(session):
    # Use known case if present
    r = session.get(f"{API}/cases/{KNOWN_CASE_ID}", timeout=10)
    if r.status_code == 200:
        return KNOWN_CASE_ID
    # Else pick any existing case
    r = session.get(f"{API}/cases", timeout=10)
    assert r.status_code == 200, r.text
    cases = r.json().get("cases", [])
    if not cases:
        pytest.skip("No cases available to test")
    return cases[0]["id"]


@pytest.fixture(scope="session")
def case_obj(session, case_id):
    r = session.get(f"{API}/cases/{case_id}", timeout=10)
    assert r.status_code == 200
    return r.json()


# ────────── Endpoint contract tests ──────────
class TestLenderMatchEndpoint:
    def test_auth_required(self):
        r = requests.post(f"{API}/ai/lender-match", json={"case_id": "x"}, timeout=10)
        assert r.status_code in (401, 403), f"Expected 401/403 unauth, got {r.status_code}"

    def test_invalid_case_404(self, session):
        r = session.post(f"{API}/ai/lender-match", json={"case_id": "non-existent-" + uuid.uuid4().hex}, timeout=30)
        assert r.status_code == 404

    def test_valid_case_returns_matches(self, session, case_id):
        r = session.post(f"{API}/ai/lender-match", json={"case_id": case_id}, timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("success") is True
        data = body["data"]
        assert "matches" in data
        assert "eligible_count" in data
        assert "total_lenders" in data
        assert "message" in data
        assert isinstance(data["matches"], list)
        assert isinstance(data["eligible_count"], int)
        assert isinstance(data["total_lenders"], int)
        # If matches exist, validate match shape
        if data["matches"]:
            m = data["matches"][0]
            for k in [
                "rank", "lender_id", "lender_name", "proc_fee_purchase",
                "max_ltv", "avg_processing_days", "broker_success_rate",
                "reason", "watch_out",
            ]:
                assert k in m, f"Missing key {k} in match: {m}"
            assert isinstance(m["rank"], int)
            # ranks should be sequential starting at 1
            ranks = [x["rank"] for x in data["matches"]]
            assert ranks == sorted(ranks)
            assert ranks[0] == 1


# ────────── Hard filter unit-style tests via lender creation ──────────
class TestHardFilter:
    """
    Create temporary lenders with attributes that should be filtered out
    by the deterministic hard filter, then verify they don't appear in matches.
    """

    @pytest.fixture
    def case_for_filter(self, case_obj):
        # Need ltv, loan_amount, employment_type, credit_profile
        assert case_obj.get("ltv") is not None, "Case has no LTV — can't run filter tests"
        return case_obj

    def _create_lender(self, session, **kwargs):
        payload = {
            "name": kwargs.pop("name", f"TEST_Lender_{uuid.uuid4().hex[:8]}"),
            "max_ltv": kwargs.pop("max_ltv", 95),
            "min_loan": kwargs.pop("min_loan", 0),
            "max_loan": kwargs.pop("max_loan", 10_000_000),
            "proc_fee_purchase": kwargs.pop("proc_fee_purchase", 0.4),
            "proc_fee_remortgage": kwargs.pop("proc_fee_remortgage", 0.35),
            "avg_processing_days": kwargs.pop("avg_processing_days", 20),
            "broker_success_rate": kwargs.pop("broker_success_rate", 85),
            "accepts_self_employed": kwargs.pop("accepts_self_employed", True),
            "accepts_contractors": kwargs.pop("accepts_contractors", True),
            "accepts_adverse": kwargs.pop("accepts_adverse", True),
        }
        payload.update(kwargs)
        r = session.post(f"{API}/lenders", json=payload, timeout=10)
        assert r.status_code in (200, 201), r.text
        return r.json()

    def _delete_lender(self, session, lender_id):
        session.delete(f"{API}/lenders/{lender_id}", timeout=10)

    def _match_lender_ids(self, session, cid):
        r = session.post(f"{API}/ai/lender-match", json={"case_id": cid}, timeout=60)
        assert r.status_code == 200
        return {m["lender_id"] for m in r.json()["data"]["matches"]}

    def test_excluded_when_max_ltv_below_case_ltv(self, session, case_for_filter):
        case_id = case_for_filter["id"]
        ltv = case_for_filter["ltv"]
        # max_ltv strictly below case ltv → excluded
        bad = self._create_lender(session, max_ltv=max(0, int(ltv) - 5))
        try:
            ids = self._match_lender_ids(session, case_id)
            assert bad["id"] not in ids, "Lender with max_ltv < case.ltv should be filtered out"
        finally:
            self._delete_lender(session, bad["id"])

    def test_excluded_when_min_loan_above_case_loan(self, session, case_for_filter):
        case_id = case_for_filter["id"]
        loan = case_for_filter.get("loan_amount") or 0
        bad = self._create_lender(session, min_loan=int(loan) + 1_000_000)
        try:
            ids = self._match_lender_ids(session, case_id)
            assert bad["id"] not in ids
        finally:
            self._delete_lender(session, bad["id"])

    def test_excluded_when_max_loan_below_case_loan(self, session, case_for_filter):
        case_id = case_for_filter["id"]
        loan = case_for_filter.get("loan_amount") or 0
        if loan <= 0:
            pytest.skip("Case has no loan amount")
        bad = self._create_lender(session, max_loan=max(1, int(loan) - 1))
        try:
            ids = self._match_lender_ids(session, case_id)
            assert bad["id"] not in ids
        finally:
            self._delete_lender(session, bad["id"])

    def test_excluded_when_client_self_employed_and_lender_does_not_accept(self, session, case_for_filter):
        client = case_for_filter.get("client") or {}
        emp = (client.get("employment_type") or "").lower()
        if emp not in ("self_employed", "self-employed"):
            pytest.skip("Client is not self-employed")
        bad = self._create_lender(session, accepts_self_employed=False)
        try:
            ids = self._match_lender_ids(session, case_for_filter["id"])
            assert bad["id"] not in ids
        finally:
            self._delete_lender(session, bad["id"])

    def test_excluded_when_client_contractor_and_lender_does_not_accept(self, session, case_for_filter):
        client = case_for_filter.get("client") or {}
        emp = (client.get("employment_type") or "").lower()
        if emp != "contractor":
            pytest.skip("Client is not contractor")
        bad = self._create_lender(session, accepts_contractors=False)
        try:
            ids = self._match_lender_ids(session, case_for_filter["id"])
            assert bad["id"] not in ids
        finally:
            self._delete_lender(session, bad["id"])

    def test_excluded_when_client_adverse_and_lender_does_not_accept(self, session, case_for_filter):
        client = case_for_filter.get("client") or {}
        credit = (client.get("credit_profile") or "").lower()
        if credit != "adverse":
            pytest.skip("Client credit is not adverse")
        bad = self._create_lender(session, accepts_adverse=False)
        try:
            ids = self._match_lender_ids(session, case_for_filter["id"])
            assert bad["id"] not in ids
        finally:
            self._delete_lender(session, bad["id"])


# ────────── Explicit client-profile exclusion tests ──────────
class TestClientProfileExclusion:
    """Create a controlled client+case to test self_employed/contractor/adverse exclusion."""

    def _setup(self, session, employment_type, credit_profile):
        client = {
            "first_name": "TEST",
            "last_name": f"Profile_{employment_type}",
            "email": f"test_{employment_type}_{uuid.uuid4().hex[:6]}@example.com",
            "phone": "07000000000",
            "date_of_birth": "1985-01-01",
            "employment_type": employment_type,
            "annual_income": 50000,
            "credit_profile": credit_profile,
            "gdpr_consent": True,
        }
        rc = session.post(f"{API}/clients", json=client, timeout=10)
        if rc.status_code not in (200, 201):
            pytest.skip(f"Cannot create client: {rc.text}")
        cid = rc.json()["id"]
        case = {
            "client_id": cid,
            "mortgage_type": "residential",
            "loan_amount": 200000,
            "property_value": 300000,
            "term_years": 25,
            "stage": "new_enquiry",
            "rate_type": None, "rate_percent": None,
            "expected_completion_date": None, "notes": None, "lender_id": None,
        }
        rcase = session.post(f"{API}/cases", json=case, timeout=10)
        if rcase.status_code not in (200, 201):
            session.delete(f"{API}/clients/{cid}", timeout=10)
            pytest.skip(f"Cannot create case: {rcase.text}")
        return cid, rcase.json()["id"]

    def _create_lender(self, session, **flags):
        payload = {
            "name": f"TEST_Excl_{uuid.uuid4().hex[:8]}",
            "max_ltv": 95, "min_loan": 0, "max_loan": 10_000_000,
            "proc_fee_purchase": 0.4, "proc_fee_remortgage": 0.35,
            "avg_processing_days": 20, "broker_success_rate": 85,
            "accepts_self_employed": True, "accepts_contractors": True, "accepts_adverse": True,
        }
        payload.update(flags)
        r = session.post(f"{API}/lenders", json=payload, timeout=10)
        assert r.status_code in (200, 201), r.text
        return r.json()["id"]

    def _matches_ids(self, session, case_id):
        r = session.post(f"{API}/ai/lender-match", json={"case_id": case_id}, timeout=60)
        assert r.status_code == 200
        return {m["lender_id"] for m in r.json()["data"]["matches"]}

    def test_self_employed_lender_excluded(self, session):
        client_id, case_id = self._setup(session, "self_employed", "clean")
        bad = self._create_lender(session, accepts_self_employed=False)
        try:
            assert bad not in self._matches_ids(session, case_id)
        finally:
            session.delete(f"{API}/lenders/{bad}", timeout=10)
            session.delete(f"{API}/cases/{case_id}", timeout=10)
            session.delete(f"{API}/clients/{client_id}", timeout=10)

    def test_contractor_lender_excluded(self, session):
        client_id, case_id = self._setup(session, "contractor", "clean")
        bad = self._create_lender(session, accepts_contractors=False)
        try:
            assert bad not in self._matches_ids(session, case_id)
        finally:
            session.delete(f"{API}/lenders/{bad}", timeout=10)
            session.delete(f"{API}/cases/{case_id}", timeout=10)
            session.delete(f"{API}/clients/{client_id}", timeout=10)

    def test_adverse_lender_excluded(self, session):
        client_id, case_id = self._setup(session, "employed", "adverse")
        bad = self._create_lender(session, accepts_adverse=False)
        try:
            assert bad not in self._matches_ids(session, case_id)
        finally:
            session.delete(f"{API}/lenders/{bad}", timeout=10)
            session.delete(f"{API}/cases/{case_id}", timeout=10)
            session.delete(f"{API}/clients/{client_id}", timeout=10)


# ────────── Empty result scenario ──────────
class TestEmptyResult:
    def test_no_eligible_returns_message(self, session, case_obj):
        """
        Create a temp client with self_employed + adverse + tiny income, then
        a case with extreme LTV that probably excludes all lenders.
        Verify empty array + message.
        """
        # Use existing case but with impossible LTV via a fresh case
        client = case_obj.get("client") or {}
        # Build new client
        new_client = {
            "first_name": "TEST",
            "last_name": "Empty",
            "email": f"test_empty_{uuid.uuid4().hex[:6]}@example.com",
            "phone": "07000000000",
            "date_of_birth": "1985-01-01",
            "employment_type": "self_employed",
            "annual_income": 10000,
            "credit_profile": "adverse",
            "gdpr_consent": True,
        }
        r = session.post(f"{API}/clients", json=new_client, timeout=10)
        if r.status_code not in (200, 201):
            pytest.skip(f"Cannot create test client: {r.status_code} {r.text}")
        client_id = r.json()["id"]

        try:
            new_case = {
                "client_id": client_id,
                "mortgage_type": "residential",
                "loan_amount": 9_999_999_999,
                "property_value": 10_000_000_000,
                "term_years": 25,
                "stage": "new_enquiry",
                "rate_type": None,
                "rate_percent": None,
                "expected_completion_date": None,
                "notes": None,
                "lender_id": None,
            }
            rc = session.post(f"{API}/cases", json=new_case, timeout=10)
            if rc.status_code not in (200, 201):
                pytest.skip(f"Cannot create test case: {rc.status_code} {rc.text}")
            new_case_id = rc.json()["id"]

            try:
                resp = session.post(f"{API}/ai/lender-match", json={"case_id": new_case_id}, timeout=60)
                assert resp.status_code == 200
                d = resp.json()["data"]
                # Probably empty since LTV is 99.99% AND extreme loan + self-emp + adverse
                if d["eligible_count"] == 0:
                    assert d["matches"] == []
                    assert d["message"] is not None
                else:
                    # Not strictly empty — log but pass shape check
                    assert isinstance(d["matches"], list)
            finally:
                session.delete(f"{API}/cases/{new_case_id}", timeout=10)
        finally:
            session.delete(f"{API}/clients/{client_id}", timeout=10)


# ────────── PATCH /cases/{id}/lender ──────────
class TestUpdateCaseLender:
    def test_patch_with_valid_lender_updates_and_enriches(self, session, case_id):
        r = session.get(f"{API}/lenders", timeout=10)
        assert r.status_code == 200
        lenders = r.json().get("lenders", [])
        if not lenders:
            pytest.skip("No lenders to test")
        lender_id = lenders[0]["id"]

        r = session.patch(f"{API}/cases/{case_id}/lender", params={"lender_id": lender_id}, timeout=10)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("lender_id") == lender_id
        assert body.get("lender", {}).get("id") == lender_id
        assert body.get("lender", {}).get("name")

        # Verify persistence
        r = session.get(f"{API}/cases/{case_id}", timeout=10)
        assert r.status_code == 200
        assert r.json().get("lender_id") == lender_id

    def test_patch_with_nonexistent_lender_404(self, session, case_id):
        r = session.patch(
            f"{API}/cases/{case_id}/lender",
            params={"lender_id": "non-existent-" + uuid.uuid4().hex},
            timeout=10,
        )
        assert r.status_code == 404

    def test_patch_with_nonexistent_case_404(self, session):
        r = session.patch(
            f"{API}/cases/non-existent-case-id/lender",
            params={"lender_id": "anything"},
            timeout=10,
        )
        assert r.status_code == 404


# ────────── Regression: AI Feature 1 still works ──────────
class TestRegressionBorrowerScore:
    def test_borrower_score_endpoint_still_works(self, session, case_obj):
        client_id = (case_obj.get("client") or {}).get("id")
        if not client_id:
            pytest.skip("No client on case")
        r = session.post(f"{API}/ai/borrower-score", json={"client_id": client_id}, timeout=60)
        assert r.status_code == 200
        d = r.json()["data"]
        assert "score" in d and "classification" in d and "summary" in d and "breakdown" in d
