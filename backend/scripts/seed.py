"""Seed the database with the 2026 TaxYearConfig and a handful of demo
accounts covering every RBAC tier, so the frontend has something to log into
immediately.

Run from backend/ inside the venv:
    .venv\\Scripts\\python.exe -m scripts.seed

Idempotent: re-running skips anything that already exists by unique key
(tax_year, email) rather than erroring or duplicating.
"""
from app.database import Base, SessionLocal, engine
from app.models.client import Client
from app.models.enums import ClientType, SubscriptionTier, UserRole
from app.models.firm import Firm
from app.models.tax_config import TaxYearConfig
from app.models.user import User
from app.seed_data import TAX_YEAR_2026
from app.services.auth import hash_password

DEMO_PASSWORD = "TaxTrin2026!"


def seed_tax_config(db) -> TaxYearConfig:
    existing = db.query(TaxYearConfig).filter(TaxYearConfig.tax_year == TAX_YEAR_2026["tax_year"]).first()
    if existing:
        print(f"TaxYearConfig {TAX_YEAR_2026['tax_year']} already exists, skipping.")
        return existing
    config = TaxYearConfig(**TAX_YEAR_2026)
    db.add(config)
    db.flush()
    print(f"Seeded TaxYearConfig for tax_year={config.tax_year}.")
    return config


def _get_or_create_user(db, *, email, full_name, role, subscription_tier, firm_id=None) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user:
        return user
    user = User(
        email=email,
        hashed_password=hash_password(DEMO_PASSWORD),
        full_name=full_name,
        role=role,
        subscription_tier=subscription_tier,
        firm_id=firm_id,
    )
    db.add(user)
    db.flush()
    return user


def _get_or_create_client(db, **kwargs) -> Client:
    query = db.query(Client).filter(Client.display_name == kwargs["display_name"])
    existing = query.first()
    if existing:
        return existing
    client = Client(**kwargs)
    db.add(client)
    db.flush()
    return client


def seed_demo_accounts(db) -> None:
    # 1. system_admin
    admin = _get_or_create_user(
        db,
        email="admin@taxtrin.tt",
        full_name="TaxTrin System Admin",
        role=UserRole.SYSTEM_ADMIN,
        subscription_tier=SubscriptionTier.ENTERPRISE,
    )

    # 2. Free-tier individual (PAYE employee)
    individual_user = _get_or_create_user(
        db,
        email="employee@example.tt",
        full_name="Alicia Ramnath",
        role=UserRole.INDIVIDUAL,
        subscription_tier=SubscriptionTier.FREE,
    )
    _get_or_create_client(
        db,
        owner_user_id=individual_user.id,
        client_type=ClientType.INDIVIDUAL,
        display_name="Alicia Ramnath",
        bir_number="1234567",
        email=individual_user.email,
    )

    # 3. Pro-tier sole trader
    sole_trader_user = _get_or_create_user(
        db,
        email="soletrader@example.tt",
        full_name="Kevin Boodram",
        role=UserRole.SOLE_TRADER,
        subscription_tier=SubscriptionTier.PRO,
    )
    _get_or_create_client(
        db,
        owner_user_id=sole_trader_user.id,
        client_type=ClientType.SOLE_TRADER,
        display_name="Kevin Boodram Hardware Supplies",
        bir_number="2345678",
        email=sole_trader_user.email,
    )

    # 4. Enterprise-tier corporate
    corporate_user = _get_or_create_user(
        db,
        email="corporate@example.tt",
        full_name="Priya Maharaj",
        role=UserRole.CORPORATE,
        subscription_tier=SubscriptionTier.ENTERPRISE,
    )
    _get_or_create_client(
        db,
        owner_user_id=corporate_user.id,
        client_type=ClientType.CORPORATE,
        display_name="Maharaj Manufacturing Ltd",
        bir_number="3456789",
        email=corporate_user.email,
    )

    # 5. Firm Portal: a firm_admin, a firm_staff, and two firm-managed clients
    firm = db.query(Firm).filter(Firm.name == "Caribbean Tax & Advisory Partners").first()
    if not firm:
        firm = Firm(name="Caribbean Tax & Advisory Partners", bir_number="4567890")
        db.add(firm)
        db.flush()

    firm_admin = _get_or_create_user(
        db,
        email="firmadmin@ctap.tt",
        full_name="Nigel Superville",
        role=UserRole.FIRM_ADMIN,
        subscription_tier=SubscriptionTier.FIRM,
        firm_id=firm.id,
    )
    firm_staff = _get_or_create_user(
        db,
        email="staff@ctap.tt",
        full_name="Renuka Persad",
        role=UserRole.FIRM_STAFF,
        subscription_tier=SubscriptionTier.FIRM,
        firm_id=firm.id,
    )
    _get_or_create_client(
        db,
        firm_id=firm.id,
        assigned_staff_user_id=firm_staff.id,
        client_type=ClientType.INDIVIDUAL,
        display_name="Marcus Cedeno",
        bir_number="5678901",
    )
    _get_or_create_client(
        db,
        firm_id=firm.id,
        assigned_staff_user_id=firm_staff.id,
        client_type=ClientType.CORPORATE,
        display_name="Cedeno Logistics Ltd",
        bir_number="6789012",
    )

    print("Seeded demo accounts (password for all: {!r}):".format(DEMO_PASSWORD))
    for u in (admin, individual_user, sole_trader_user, corporate_user, firm_admin, firm_staff):
        print(f"  - {u.email:28s} role={u.role.value:14s} tier={u.subscription_tier.value}")


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_tax_config(db)
        seed_demo_accounts(db)
        db.commit()
    finally:
        db.close()
    print("Seed complete.")


if __name__ == "__main__":
    main()
