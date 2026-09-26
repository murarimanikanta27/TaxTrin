from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import SubscriptionTier, UserRole


class User(Base):
    """A login-capable account.

    Four RBAC tiers from the spec map onto `role`:
      - individual / sole_trader / corporate -> self-service taxpayers, each
        linked to exactly one Client record they own (owner_user_id on Client).
      - firm_admin / firm_staff -> belong to a Firm and manage many Clients.
      - system_admin -> manages the TaxYearConfig (statutory rate) tables.

    `subscription_tier` drives the feature-gating matrix (free vs Pro vs
    Enterprise vs Firm) enforced in app.services.entitlements.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)

    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole, native_enum=False, length=32), nullable=False)
    subscription_tier: Mapped[SubscriptionTier] = mapped_column(
        SAEnum(SubscriptionTier, native_enum=False, length=32),
        default=SubscriptionTier.FREE,
        nullable=False,
    )

    firm_id: Mapped[Optional[int]] = mapped_column(ForeignKey("firms.id"), nullable=True)
    bir_number: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    firm: Mapped[Optional["Firm"]] = relationship(back_populates="staff", foreign_keys=[firm_id])
