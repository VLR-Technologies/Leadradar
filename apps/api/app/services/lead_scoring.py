from dataclasses import dataclass, replace

from app.core.websites import classify_website_url
from app.models.business import Business, OpportunityLevel, WebsiteAudit, WebsiteStatus


@dataclass(frozen=True, slots=True)
class LeadOpportunity:
    score: int
    level: OpportunityLevel
    reasons: tuple[str, ...]


def score_lead(
    business: Business,
    *,
    website_status: WebsiteStatus | None = None,
    audit: WebsiteAudit | None = None,
) -> LeadOpportunity:
    """Score internal sales opportunity, never business quality or legitimacy."""
    status = website_status or business.website_status
    audit = audit or business.website_audit
    has_phone = bool(business.phone or business.phones)
    has_email = bool(business.email or business.emails)
    has_social = bool(business.social_links or business.whatsapp_numbers)
    has_official_website = bool(
        business.website and classify_website_url(business.website) == "official"
    )
    score = 0
    reasons: list[str] = []

    if has_phone:
        score += 30
        reasons.append("Public phone available")
    if has_email:
        score += 8
        reasons.append("Public email available")

    if status == "not_found" or not has_official_website:
        score += 45 if has_phone else 22
        reasons.append("No verified website found in current sources")
    elif status == "unreachable" or (audit and audit.reachable is False):
        score += 45
        reasons.append("Listed website was unreachable during the audit")
    elif audit:
        weaknesses = (
            (audit.uses_https is False, 10, "Website does not use HTTPS"),
            (audit.mobile_viewport is False, 12, "Mobile viewport metadata was not found"),
            (audit.contact_page_present is False, 10, "Contact page was not found"),
            (audit.meta_description_present is False, 7, "Meta description was not found"),
            (audit.title_present is False, 5, "Page title was not found"),
        )
        for applies, points, reason in weaknesses:
            if applies:
                score += points
                reasons.append(reason)
        if not any(applies for applies, _, _ in weaknesses):
            score = max(0, score - 22)
            reasons.append("Website has strong basic digital-presence signals")
    else:
        score += 12
        reasons.append("Website is listed but has not yet been verified")

    if not has_email:
        score += 5
        reasons.append("No public email found")
    if business.operating_status == "open":
        score += 5
        reasons.append("Open operating status reported by a discovery source")

    if not (has_phone or has_email or has_social):
        score = min(score, 35)
        reasons.append("No public calling or messaging contact found")

    score = max(0, min(100, score))
    level: OpportunityLevel = "High" if score >= 70 else "Medium" if score >= 40 else "Low"
    return LeadOpportunity(score=score, level=level, reasons=tuple(dict.fromkeys(reasons)))


def apply_lead_score(business: Business) -> Business:
    opportunity = score_lead(business)
    return replace(
        business,
        lead_score=opportunity.score,
        opportunity_level=opportunity.level,
        opportunity_reasons=opportunity.reasons,
    )
