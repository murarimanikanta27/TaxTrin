from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import LinkedReturnType, ScheduleType


class TaxSchedule(Base):
    """A supporting schedule for a return: Schedule A/B, wear-and-tear, etc.

    Kept generic (one table, a `schedule_type` discriminator, and a JSON
    `data` blob of line items) rather than one table per schedule type, since
    every schedule here is fundamentally "a list of rows with a subtotal" and
    the exact columns vary by schedule. `linked_return_type`/`linked_return_id`
    point at either an IndividualReturn or a CorporateReturn.
    """

    __tablename__ = "tax_schedules"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    tax_year: Mapped[int] = mapped_column(Integer, nullable=False)

    schedule_type: Mapped[ScheduleType] = mapped_column(
        SAEnum(ScheduleType, native_enum=False, length=64), nullable=False
    )
    linked_return_type: Mapped[Optional[LinkedReturnType]] = mapped_column(
        SAEnum(LinkedReturnType, native_enum=False, length=32), nullable=True
    )
    linked_return_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # e.g. for wear_and_tear: {"items": [{"description": "Delivery van", "asset_class": "B",
    #   "cost": 120000, "rate": 0.30, "opening_wdv": 84000, "allowance": 25200, "closing_wdv": 58800}]}
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    client: Mapped["Client"] = relationship()
