"""system_admin-only endpoints for editing the dynamic TaxYearConfig.

This is the "Tax Configuration Service / Admin Panel Interface" from the
spec: every statutory constant is editable here without a code change.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_roles
from app.models.enums import UserRole
from app.models.tax_config import TaxYearConfig
from app.schemas import TaxYearConfigOut, TaxYearConfigUpdate

router = APIRouter(prefix="/admin/tax-config", tags=["admin"])

_admin_only = require_roles(UserRole.SYSTEM_ADMIN)


@router.get("", response_model=list[TaxYearConfigOut])
def list_tax_configs(db: Session = Depends(get_db), _admin=Depends(_admin_only)):
    return db.query(TaxYearConfig).order_by(TaxYearConfig.tax_year.desc()).all()


@router.get("/{tax_year}", response_model=TaxYearConfigOut)
def get_tax_config(tax_year: int, db: Session = Depends(get_db), _admin=Depends(_admin_only)):
    config = db.query(TaxYearConfig).filter(TaxYearConfig.tax_year == tax_year).first()
    if not config:
        raise HTTPException(status_code=404, detail=f"No TaxYearConfig for tax_year={tax_year}")
    return config


@router.patch("/{tax_year}", response_model=TaxYearConfigOut)
def update_tax_config(
    tax_year: int,
    payload: TaxYearConfigUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(_admin_only),
):
    config = db.query(TaxYearConfig).filter(TaxYearConfig.tax_year == tax_year).first()
    if not config:
        raise HTTPException(status_code=404, detail=f"No TaxYearConfig for tax_year={tax_year}")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(config, field, value)
    db.commit()
    db.refresh(config)
    return config
