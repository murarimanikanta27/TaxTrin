"""Monetization / tier feature-gating matrix.

Encodes the "5. Monetization & Tier Feature Matrix" requirement as
executable rules rather than a document, so the API can actually enforce
them (e.g. reject an e-Tax export attempt from a Free-tier individual who
has exceeded their yearly TD4 allowance).

This intentionally stays simple and in-memory for the POC: a real product
would likely track usage counters in the DB (e.g. "TD4 slips processed this
calendar year") rather than the request-time approximation here.
"""
from dataclasses import dataclass

from app.models.enums import SubscriptionTier, UserRole


@dataclass(frozen=True)
class TierLimits:
    tier: SubscriptionTier
    max_td4_per_year: int | None  # None == unlimited
    can_export_etax_files: bool
    can_generate_official_pdfs: bool
    can_file_vat200: bool
    can_file_corporate_return: bool
    max_clients_for_firm: int | None


TIER_MATRIX: dict[SubscriptionTier, TierLimits] = {
    SubscriptionTier.FREE: TierLimits(
        tier=SubscriptionTier.FREE,
        max_td4_per_year=1,
        can_export_etax_files=False,
        can_generate_official_pdfs=False,
        can_file_vat200=False,
        can_file_corporate_return=False,
        max_clients_for_firm=None,
    ),
    SubscriptionTier.PRO: TierLimits(
        tier=SubscriptionTier.PRO,
        max_td4_per_year=None,
        can_export_etax_files=True,
        can_generate_official_pdfs=True,
        can_file_vat200=True,
        can_file_corporate_return=False,
        max_clients_for_firm=None,
    ),
    SubscriptionTier.ENTERPRISE: TierLimits(
        tier=SubscriptionTier.ENTERPRISE,
        max_td4_per_year=None,
        can_export_etax_files=True,
        can_generate_official_pdfs=True,
        can_file_vat200=True,
        can_file_corporate_return=True,
        max_clients_for_firm=None,
    ),
    SubscriptionTier.FIRM: TierLimits(
        tier=SubscriptionTier.FIRM,
        max_td4_per_year=None,
        can_export_etax_files=True,
        can_generate_official_pdfs=True,
        can_file_vat200=True,
        can_file_corporate_return=True,
        max_clients_for_firm=None,  # gate on a real client count in a follow-up iteration
    ),
}


def get_tier_limits(tier: SubscriptionTier) -> TierLimits:
    return TIER_MATRIX[tier]


def default_tier_for_role(role: UserRole) -> SubscriptionTier:
    if role in (UserRole.FIRM_ADMIN, UserRole.FIRM_STAFF):
        return SubscriptionTier.FIRM
    return SubscriptionTier.FREE
