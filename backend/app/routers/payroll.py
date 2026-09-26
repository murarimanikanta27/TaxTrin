from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_accessible_client, get_current_user
from app.models.payroll import PayrollLine, PayrollRun
from app.models.user import User
from app.schemas import PayrollRunCreate, PayrollRunOut
from app.services.payroll_engine import compute_payroll_line
from app.services.tax_config_repo import get_tax_config_or_404

router = APIRouter(prefix="/payroll", tags=["payroll"])


@router.post("/runs", response_model=PayrollRunOut, status_code=201)
def create_payroll_run(
    payload: PayrollRunCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_accessible_client(payload.client_id, db, current_user)
    tax_year = int(payload.pay_period_start[:4])
    config = get_tax_config_or_404(db, tax_year)

    run = PayrollRun(
        client_id=payload.client_id,
        pay_period_start=payload.pay_period_start,
        pay_period_end=payload.pay_period_end,
        frequency=payload.frequency,
    )
    db.add(run)
    db.flush()

    for line_in in payload.lines:
        result = compute_payroll_line(config, line_in.gross_pay, frequency=payload.frequency.value)
        db.add(
            PayrollLine(
                run_id=run.id,
                employee_client_id=line_in.employee_client_id,
                employee_name=line_in.employee_name,
                gross_pay=result["gross_pay"],
                nis_class_name=result["nis_class_name"],
                nis_employee=result["nis_employee"],
                nis_employer=result["nis_employer"],
                health_surcharge_employee=result["health_surcharge_employee"],
                health_surcharge_employer=result["health_surcharge_employer"],
                paye_deducted=result["paye_deducted"],
                net_pay=result["net_pay"],
                computed=result,
            )
        )

    db.commit()
    db.refresh(run)
    return run


@router.get("/runs/{run_id}", response_model=PayrollRunOut)
def get_payroll_run(run_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    run = db.get(PayrollRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Payroll run not found")
    get_accessible_client(run.client_id, db, current_user)
    return run


@router.get("/clients/{client_id}/runs", response_model=list[PayrollRunOut])
def list_payroll_runs_for_client(
    client_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    get_accessible_client(client_id, db, current_user)
    return db.query(PayrollRun).filter(PayrollRun.client_id == client_id).all()
