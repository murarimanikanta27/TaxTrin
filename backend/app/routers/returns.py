"""Individual (Form 440), Corporate (Form 500), and VAT 200 return endpoints.

Each POST both persists the return AND runs the tax engine immediately,
storing the result in `.computed` -- this is what powers the wizard's
"real-time refund/tax balance indicator".
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_accessible_client, get_current_user
from app.models.returns import CorporateReturn, IndividualReturn, VAT200Return
from app.models.user import User
from app.schemas import (
    CorporateReturnCreate,
    CorporateReturnOut,
    CorporateReturnPreviewRequest,
    IndividualReturnCreate,
    IndividualReturnOut,
    IndividualReturnPreviewRequest,
    VAT200ReturnCreate,
    VAT200ReturnOut,
)
from app.services.entitlements import get_tier_limits
from app.services.return_engine import compute_corporate_return, compute_individual_return, compute_vat200_return
from app.services.tax_config_repo import get_tax_config_or_404

router = APIRouter(tags=["returns"])


# --- Individual (Form 440) ---


@router.post("/returns/individual/preview")
def preview_individual_return(
    payload: IndividualReturnPreviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Stateless computation for the wizard's live refund/balance indicator.
    Does not touch the database beyond reading the active TaxYearConfig."""
    config = get_tax_config_or_404(db, payload.tax_year)
    return compute_individual_return(config, payload.inputs)


@router.post("/returns/individual", response_model=IndividualReturnOut, status_code=201)
def create_individual_return(
    payload: IndividualReturnCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_accessible_client(payload.client_id, db, current_user)
    config = get_tax_config_or_404(db, payload.tax_year)

    computed = compute_individual_return(config, payload.inputs)

    tax_return = IndividualReturn(
        client_id=payload.client_id,
        tax_year=payload.tax_year,
        inputs=payload.inputs,
        computed=computed,
        td4_input_ids=payload.td4_input_ids,
        refund_or_balance_due=computed["refund_or_balance_due"],
    )
    db.add(tax_return)
    db.commit()
    db.refresh(tax_return)
    return tax_return


@router.get("/returns/individual/{return_id}", response_model=IndividualReturnOut)
def get_individual_return(return_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    tax_return = db.get(IndividualReturn, return_id)
    if not tax_return:
        raise HTTPException(status_code=404, detail="Return not found")
    get_accessible_client(tax_return.client_id, db, current_user)
    return tax_return


@router.get("/clients/{client_id}/returns/individual", response_model=list[IndividualReturnOut])
def list_individual_returns_for_client(
    client_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    get_accessible_client(client_id, db, current_user)
    return db.query(IndividualReturn).filter(IndividualReturn.client_id == client_id).all()


# --- Corporate (Form 500) ---


@router.post("/returns/corporate/preview")
def preview_corporate_return(
    payload: CorporateReturnPreviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    config = get_tax_config_or_404(db, payload.tax_year)
    return compute_corporate_return(config, payload.inputs)


@router.post("/returns/corporate", response_model=CorporateReturnOut, status_code=201)
def create_corporate_return(
    payload: CorporateReturnCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_accessible_client(payload.client_id, db, current_user)
    if not get_tier_limits(current_user.subscription_tier).can_file_corporate_return:
        raise HTTPException(
            status_code=402,
            detail="Filing a Form 500 corporation tax return requires an Enterprise or Firm plan.",
        )
    config = get_tax_config_or_404(db, payload.tax_year)

    computed = compute_corporate_return(config, payload.inputs)

    tax_return = CorporateReturn(
        client_id=payload.client_id,
        tax_year=payload.tax_year,
        accounting_period_start=payload.accounting_period_start,
        accounting_period_end=payload.accounting_period_end,
        inputs=payload.inputs,
        computed=computed,
        refund_or_balance_due=computed["refund_or_balance_due"],
    )
    db.add(tax_return)
    db.commit()
    db.refresh(tax_return)
    return tax_return


@router.get("/returns/corporate/{return_id}", response_model=CorporateReturnOut)
def get_corporate_return(return_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    tax_return = db.get(CorporateReturn, return_id)
    if not tax_return:
        raise HTTPException(status_code=404, detail="Return not found")
    get_accessible_client(tax_return.client_id, db, current_user)
    return tax_return


@router.get("/clients/{client_id}/returns/corporate", response_model=list[CorporateReturnOut])
def list_corporate_returns_for_client(
    client_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    get_accessible_client(client_id, db, current_user)
    return db.query(CorporateReturn).filter(CorporateReturn.client_id == client_id).all()


# --- VAT 200 ---


@router.post("/returns/vat200", response_model=VAT200ReturnOut, status_code=201)
def create_vat200_return(
    payload: VAT200ReturnCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_accessible_client(payload.client_id, db, current_user)
    if not get_tier_limits(current_user.subscription_tier).can_file_vat200:
        raise HTTPException(
            status_code=402,
            detail="Filing a VAT 200 return requires a Pro plan or higher. Upgrade your subscription to unlock this feature.",
        )
    # VAT200 returns are bimonthly and not tied to a single "tax_year" in the
    # same sense as income tax; use the period's start-year for rate lookup.
    tax_year = int(payload.period_start[:4])
    config = get_tax_config_or_404(db, tax_year)

    computed = compute_vat200_return(config, payload.model_dump())

    vat_return = VAT200Return(
        client_id=payload.client_id,
        period_start=payload.period_start,
        period_end=payload.period_end,
        standard_rated_sales=computed["standard_rated_sales"],
        zero_rated_sales=computed["zero_rated_sales"],
        exempt_sales=computed["exempt_sales"],
        output_vat=computed["output_vat"],
        input_vat=computed["input_vat"],
        net_vat_payable=computed["net_vat_payable"],
        computed=computed,
    )
    db.add(vat_return)
    db.commit()
    db.refresh(vat_return)
    return vat_return


@router.get("/returns/vat200/{return_id}", response_model=VAT200ReturnOut)
def get_vat200_return(return_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    vat_return = db.get(VAT200Return, return_id)
    if not vat_return:
        raise HTTPException(status_code=404, detail="Return not found")
    get_accessible_client(vat_return.client_id, db, current_user)
    return vat_return


@router.get("/clients/{client_id}/returns/vat200", response_model=list[VAT200ReturnOut])
def list_vat200_returns_for_client(
    client_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    get_accessible_client(client_id, db, current_user)
    return db.query(VAT200Return).filter(VAT200Return.client_id == client_id).all()
