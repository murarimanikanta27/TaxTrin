from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import ClientType, ReturnStatus


class Client(Base):
    """A taxpayer entity: individual, sole trader, partnership, or corporation.

    Every return, TD4, payroll run, and e-Tax export hangs off a Client.
    A Client is either:
      - self-service: `owner_user_id` points at the individual/sole_trader/
        corporate User who manages it directly, `firm_id` is NULL; or
      - firm-managed: `firm_id` points at the owning Firm, and
        `assigned_staff_user_id` optionally points at the firm_staff User
        responsible for it, enabling the firm's staff-assignment workflow.
    """

    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)

    firm_id: Mapped[Optional[int]] = mapped_column(ForeignKey("firms.id"), nullable=True)
    owner_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    assigned_staff_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)

    client_type: Mapped[ClientType] = mapped_column(SAEnum(ClientType, native_enum=False, length=32), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)

    bir_number: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    tin: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    nis_number: Mapped[Optional[str]] = mapped_column(String(9), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    filing_status: Mapped[ReturnStatus] = mapped_column(
        SAEnum(ReturnStatus, native_enum=False, length=32),
        default=ReturnStatus.DRAFT,
        nullable=False,
    )
    client_signed_off: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    firm: Mapped[Optional["Firm"]] = relationship(back_populates="clients", foreign_keys=[firm_id])
    owner_user: Mapped[Optional["User"]] = relationship(foreign_keys=[owner_user_id])
    assigned_staff: Mapped[Optional["User"]] = relationship(foreign_keys=[assigned_staff_user_id])
