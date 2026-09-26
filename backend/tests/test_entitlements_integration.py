"""Integration tests for the monetization tier-gating enforced in the API
routers (app/services/entitlements.py wired into app/routers/{td4,returns,
etax_export}.py). Uses a fully isolated in-memory SQLite DB per test run via
FastAPI's dependency override, so this suite doesn't touch the real
backend/taxtrin.db file.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.client import Client
from app.models.enums import ClientType, SubscriptionTier, UserRole
from app.models.tax_config import TaxYearConfig
from app.models.user import User
from app.seed_data import TAX_YEAR_2026
from app.services.auth import hash_password


@pytest.fixture()
def client():
    # StaticPool keeps a single shared connection alive for the whole test,
    # which is required for an in-memory SQLite DB to be visible across the
    # fixture's setup session and every request TestClient makes afterward
    # (each of which would otherwise open its own :memory: connection).
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    db = TestingSessionLocal()
    db.add(TaxYearConfig(**TAX_YEAR_2026))

    free_user = User(
        email="free@example.tt",
        hashed_password=hash_password("password123"),
        full_name="Free User",
        role=UserRole.INDIVIDUAL,
        subscription_tier=SubscriptionTier.FREE,
    )
    db.add(free_user)
    db.flush()
    free_client = Client(owner_user_id=free_user.id, client_type=ClientType.INDIVIDUAL, display_name="Free User")
    db.add(free_client)

    pro_user = User(
        email="pro@example.tt",
        hashed_password=hash_password("password123"),
        full_name="Pro User",
        role=UserRole.SOLE_TRADER,
        subscription_tier=SubscriptionTier.PRO,
    )
    db.add(pro_user)
    db.flush()
    pro_client = Client(owner_user_id=pro_user.id, client_type=ClientType.SOLE_TRADER, display_name="Pro User")
    db.add(pro_client)

    db.commit()

    test_client = TestClient(app)
    yield test_client, free_client.id, pro_client.id

    app.dependency_overrides.clear()


def _login(test_client: TestClient, email: str) -> dict:
    resp = test_client.post("/auth/login", json={"email": email, "password": "password123"})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestFreeTierTD4Limit:
    def test_free_tier_can_create_one_td4(self, client):
        test_client, free_client_id, _ = client
        headers = _login(test_client, "free@example.tt")
        resp = test_client.post(
            "/td4",
            json={"client_id": free_client_id, "income_year": 2026, "employee_name": "A", "gross_earnings": 1000},
            headers=headers,
        )
        assert resp.status_code == 201

    def test_free_tier_blocked_on_second_td4_same_year(self, client):
        test_client, free_client_id, _ = client
        headers = _login(test_client, "free@example.tt")
        test_client.post(
            "/td4",
            json={"client_id": free_client_id, "income_year": 2026, "employee_name": "A", "gross_earnings": 1000},
            headers=headers,
        )
        resp = test_client.post(
            "/td4",
            json={"client_id": free_client_id, "income_year": 2026, "employee_name": "B", "gross_earnings": 2000},
            headers=headers,
        )
        assert resp.status_code == 402
        assert "TD4" in resp.json()["detail"]

    def test_free_tier_can_create_td4_for_a_different_year(self, client):
        test_client, free_client_id, _ = client
        headers = _login(test_client, "free@example.tt")
        test_client.post(
            "/td4",
            json={"client_id": free_client_id, "income_year": 2025, "employee_name": "A", "gross_earnings": 1000},
            headers=headers,
        )
        resp = test_client.post(
            "/td4",
            json={"client_id": free_client_id, "income_year": 2026, "employee_name": "B", "gross_earnings": 2000},
            headers=headers,
        )
        assert resp.status_code == 201

    def test_pro_tier_has_no_td4_limit(self, client):
        test_client, _, pro_client_id = client
        headers = _login(test_client, "pro@example.tt")
        for i in range(3):
            resp = test_client.post(
                "/td4",
                json={"client_id": pro_client_id, "income_year": 2026, "employee_name": f"E{i}", "gross_earnings": 1000},
                headers=headers,
            )
            assert resp.status_code == 201


class TestFreeTierExportGating:
    def test_free_tier_blocked_from_td4_csv_export(self, client):
        test_client, free_client_id, _ = client
        headers = _login(test_client, "free@example.tt")
        resp = test_client.post(
            "/etax-export/td4-supplementary-csv",
            json={"client_id": free_client_id, "income_year": 2026},
            headers=headers,
        )
        assert resp.status_code == 402
        assert "Pro plan" in resp.json()["detail"]

    def test_pro_tier_can_export_td4_csv(self, client):
        test_client, _, pro_client_id = client
        headers = _login(test_client, "pro@example.tt")
        resp = test_client.post(
            "/etax-export/td4-supplementary-csv",
            json={"client_id": pro_client_id, "income_year": 2026},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.headers["x-validation-status"] == "failed"  # no TD4 records -> validate_td4_rows fails


class TestVAT200Gating:
    def test_free_tier_blocked_from_filing_vat200(self, client):
        test_client, free_client_id, _ = client
        headers = _login(test_client, "free@example.tt")
        resp = test_client.post(
            "/returns/vat200",
            json={"client_id": free_client_id, "period_start": "2026-01-01", "period_end": "2026-02-28"},
            headers=headers,
        )
        assert resp.status_code == 402

    def test_pro_tier_can_file_vat200(self, client):
        test_client, _, pro_client_id = client
        headers = _login(test_client, "pro@example.tt")
        resp = test_client.post(
            "/returns/vat200",
            json={"client_id": pro_client_id, "period_start": "2026-01-01", "period_end": "2026-02-28"},
            headers=headers,
        )
        assert resp.status_code == 201


class TestCorporateReturnGating:
    def test_pro_tier_blocked_from_filing_corporate_return(self, client):
        test_client, _, pro_client_id = client
        headers = _login(test_client, "pro@example.tt")
        resp = test_client.post(
            "/returns/corporate",
            json={"client_id": pro_client_id, "tax_year": 2026, "inputs": {"chargeable_profits": 100000, "gross_receipts": 500000}},
            headers=headers,
        )
        assert resp.status_code == 402
        assert "Form 500" in resp.json()["detail"]
