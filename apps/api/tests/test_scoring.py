from dataclasses import replace

from app.models.business import Business, BusinessAddress, WebsiteAudit
from app.services.lead_scoring import score_lead


def business(
    *,
    phone: str | None = None,
    email: str | None = None,
    website: str | None = None,
    website_status: str = "not_found",
    website_audit: WebsiteAudit | None = None,
) -> Business:
    return Business(
        source_id="overture:1",
        source="overture",
        name="ABC Dental Clinic",
        category="Dentist",
        address=BusinessAddress(city="Hyderabad", country="India"),
        latitude=17.4,
        longitude=78.4,
        phone=phone,
        email=email,
        website=website,
        opening_hours=None,
        phones=(phone,) if phone else (),
        emails=(email,) if email else (),
        websites=(website,) if website else (),
        website_status=website_status,
        website_audit=website_audit,
        operating_status="open",
    )


def test_phone_without_website_is_high_opportunity() -> None:
    result = score_lead(business(phone="+91 98765 43210"))

    assert result.level == "High"
    assert result.score == 85
    assert "Public phone available" in result.reasons
    assert "No verified website found in current sources" in result.reasons


def test_no_contact_details_caps_calling_readiness() -> None:
    result = score_lead(business())

    assert result.level == "Low"
    assert result.score <= 35
    assert "No public calling or messaging contact found" in result.reasons


def test_strong_verified_website_reduces_website_opportunity() -> None:
    audit = WebsiteAudit(
        reachable=True,
        uses_https=True,
        mobile_viewport=True,
        contact_page_present=True,
        title_present=True,
        meta_description_present=True,
        label="Basic digital presence",
    )
    result = score_lead(
        business(
            phone="+91 98765 43210",
            email="hello@abcdental.in",
            website="https://abcdental.in",
            website_status="verified",
            website_audit=audit,
        )
    )

    assert result.level == "Low"
    assert result.score == 21
    assert "Website has strong basic digital-presence signals" in result.reasons


def test_unreachable_website_with_phone_is_high_opportunity() -> None:
    lead = business(
        phone="+91 98765 43210",
        website="https://abcdental.in",
        website_status="listed",
    )
    result = score_lead(
        replace(
            lead,
            website_audit=WebsiteAudit(reachable=False, label="Website unreachable"),
        )
    )

    assert result.level == "High"
    assert "Listed website was unreachable during the audit" in result.reasons
