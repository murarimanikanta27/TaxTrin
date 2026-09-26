import pytest

from app.models.tax_config import TaxYearConfig
from app.seed_data import TAX_YEAR_2026


@pytest.fixture()
def config_2026() -> TaxYearConfig:
    """An in-memory (never committed to a DB) TaxYearConfig(2026) row, built
    straight from the same seed_data dict the real seed script inserts.
    Using the ORM class directly (not a DB session) keeps engine unit tests
    fast and DB-independent.
    """
    return TaxYearConfig(**TAX_YEAR_2026)
