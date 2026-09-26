"""FastAPI dependencies: DB session (re-exported), current user, RBAC guards,
and client-scoping (a user may only touch Clients they own or their Firm
manages).
"""
from typing import Iterable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.client import Client
from app.models.enums import UserRole
from app.models.user import User
from app.services.auth import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_error
    try:
        payload = decode_access_token(token)
        user_id = int(payload.get("sub"))
    except (jwt.PyJWTError, TypeError, ValueError):
        raise credentials_error

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise credentials_error
    return user


def require_roles(*allowed_roles: UserRole):
    """Dependency factory: 403s unless the current user's role is in
    `allowed_roles`. Used to gate admin-only or firm-only endpoints."""

    def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires one of the following roles: {', '.join(r.value for r in allowed_roles)}",
            )
        return current_user

    return _check


def get_accessible_client(client_id: int, db: Session, current_user: User) -> Client:
    """Fetch a Client the current user is allowed to see/edit:
      - system_admin: any client
      - firm_admin / firm_staff: any client belonging to their firm
      - individual / sole_trader / corporate: only the client they own
    404s (not 403) on an inaccessible client to avoid leaking existence.
    """
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")

    if current_user.role == UserRole.SYSTEM_ADMIN:
        return client
    if current_user.role in (UserRole.FIRM_ADMIN, UserRole.FIRM_STAFF):
        if client.firm_id == current_user.firm_id:
            return client
    else:
        if client.owner_user_id == current_user.id:
            return client

    raise HTTPException(status_code=404, detail="Client not found")


def accessible_client_ids_for_user(db: Session, current_user: User) -> Iterable[int]:
    """All client IDs the current user may list/browse."""
    if current_user.role == UserRole.SYSTEM_ADMIN:
        return [c.id for c in db.query(Client.id).all()]
    if current_user.role in (UserRole.FIRM_ADMIN, UserRole.FIRM_STAFF):
        return [c.id for c in db.query(Client.id).filter(Client.firm_id == current_user.firm_id).all()]
    return [c.id for c in db.query(Client.id).filter(Client.owner_user_id == current_user.id).all()]
