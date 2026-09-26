"""Lookup helper for the active TaxYearConfig, shared by every router that
needs to run a calculation.
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.tax_config import TaxYearConfig


def get_tax_config_or_404(db: Session, tax_year: int) -> TaxYearConfig:
    config = (
        db.query(TaxYearConfig)
        .filter(TaxYearConfig.tax_year == tax_year, TaxYearConfig.is_active.is_(True))
        .first()
    )
    if not config:
        raise HTTPException(
            status_code=404,
            detail=f"No active tax configuration found for tax_year={tax_year}. "
            "An admin must create one via /admin/tax-config.",
        )
    return config
