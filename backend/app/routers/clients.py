from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import accessible_client_ids_for_user, get_accessible_client, get_current_user
from app.models.client import Client
from app.models.enums import UserRole
from app.models.user import User
from app.schemas import ClientCreate, ClientOut, ClientUpdate

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=list[ClientOut])
def list_clients(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ids = list(accessible_client_ids_for_user(db, current_user))
    if not ids:
        return []
    return db.query(Client).filter(Client.id.in_(ids)).all()


@router.post("", response_model=ClientOut, status_code=201)
def create_client(
    payload: ClientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Only firm staff/admins create additional Client records (the Firm
    Multi-Client Portal workflow). Self-service taxpayers get their single
    Client auto-created at registration (see routers/auth.py)."""
    if current_user.role not in (UserRole.FIRM_ADMIN, UserRole.FIRM_STAFF, UserRole.SYSTEM_ADMIN):
        raise HTTPException(status_code=403, detail="Only firm staff can add new clients")

    client = Client(
        firm_id=current_user.firm_id,
        client_type=payload.client_type,
        display_name=payload.display_name,
        bir_number=payload.bir_number,
        tin=payload.tin,
        nis_number=payload.nis_number,
        email=payload.email,
        phone=payload.phone,
        address=payload.address,
        assigned_staff_user_id=payload.assigned_staff_user_id,
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


@router.get("/{client_id}", response_model=ClientOut)
def get_client(client_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return get_accessible_client(client_id, db, current_user)


@router.patch("/{client_id}", response_model=ClientOut)
def update_client(
    client_id: int,
    payload: ClientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    client = get_accessible_client(client_id, db, current_user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(client, field, value)
    db.commit()
    db.refresh(client)
    return client
