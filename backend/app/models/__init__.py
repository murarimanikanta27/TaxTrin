"""SQLAlchemy models package.

Importing every model module here means a single `from app.models import Base`
(or importing this package at all) registers every table on `Base.metadata`,
which is what `Base.metadata.create_all()` in app.database / scripts.seed
relies on.
"""
from app.database import Base
from app.models.client import Client
from app.models.enums import (
    ClientType,
    ETaxExportType,
    PayFrequency,
    ReturnStatus,
    TD4Type,
    UserRole,
    ValidationStatus,
)
from app.models.etax_export import ETaxExportLog
from app.models.firm import Firm
from app.models.payroll import PayrollLine, PayrollRun
from app.models.returns import CorporateReturn, IndividualReturn, VAT200Return
from app.models.schedule import TaxSchedule
from app.models.td4 import TD4Input
from app.models.tax_config import TaxYearConfig
from app.models.user import User

__all__ = [
    "Base",
    "User",
    "Firm",
    "Client",
    "TaxYearConfig",
    "TD4Input",
    "IndividualReturn",
    "CorporateReturn",
    "VAT200Return",
    "TaxSchedule",
    "PayrollRun",
    "PayrollLine",
    "ETaxExportLog",
    "UserRole",
    "ClientType",
    "ReturnStatus",
    "TD4Type",
    "PayFrequency",
    "ETaxExportType",
    "ValidationStatus",
]
