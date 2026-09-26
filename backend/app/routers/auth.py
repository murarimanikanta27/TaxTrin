from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.client import Client
from app.models.enums import ClientType, UserRole
from app.models.firm import Firm
from app.models.user import User
from app.schemas import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.services.auth import create_access_token, hash_password, verify_password
from app.services.entitlements import default_tier_for_role

router = APIRouter(prefix="/auth", tags=["auth"])

_ROLE_TO_CLIENT_TYPE = {
    UserRole.INDIVIDUAL: ClientType.INDIVIDUAL,
    UserRole.SOLE_TRADER: ClientType.SOLE_TRADER,
    UserRole.CORPORATE: ClientType.CORPORATE,
}


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists")

    if payload.role == UserRole.SYSTEM_ADMIN:
        raise HTTPException(status_code=400, detail="system_admin accounts cannot self-register")

    firm_id = None
    if payload.role == UserRole.FIRM_ADMIN:
        if not payload.firm_name:
            raise HTTPException(status_code=400, detail="firm_name is required when registering as firm_admin")
        firm = Firm(name=payload.firm_name)
        db.add(firm)
        db.flush()
        firm_id = firm.id
    elif payload.role == UserRole.FIRM_STAFF:
        raise HTTPException(
            status_code=400,
            detail="firm_staff accounts must be invited by a firm_admin, not self-registered",
        )

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        subscription_tier=default_tier_for_role(payload.role),
        firm_id=firm_id,
    )
    db.add(user)
    db.flush()

    # Self-service taxpayer roles get exactly one Client record they own,
    # created automatically so they land straight in their own tax wizard.
    if payload.role in _ROLE_TO_CLIENT_TYPE:
        client = Client(
            owner_user_id=user.id,
            client_type=_ROLE_TO_CLIENT_TYPE[payload.role],
            display_name=payload.full_name,
            email=payload.email,
        )
        db.add(client)

    db.commit()
    db.refresh(user)

    token = create_access_token(subject=str(user.id), extra_claims={"role": user.role.value})
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account has been deactivated")

    token = create_access_token(subject=str(user.id), extra_claims={"role": user.role.value})
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
