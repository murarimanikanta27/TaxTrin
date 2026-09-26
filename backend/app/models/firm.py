from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Firm(Base):
    """An accounting / tax consultancy firm (the "Firm Portal" tier).

    A Firm has many staff Users (firm_admin/firm_staff) and many Clients
    (the individuals, sole traders, partnerships, and corporations it files
    on behalf of).
    """

    __tablename__ = "firms"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    bir_number: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    staff: Mapped[list["User"]] = relationship(back_populates="firm", foreign_keys="User.firm_id")
    clients: Mapped[list["Client"]] = relationship(back_populates="firm", foreign_keys="Client.firm_id")
