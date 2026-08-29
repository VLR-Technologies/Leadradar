from app.normalizers.contact import normalize_email, normalize_phone, normalize_website_url
from app.providers.enrichment.website import (
    extract_contacts,
    extract_whatsapp_numbers,
    find_contact_links,
    parse_html,
)


def test_normalizes_indian_mobile_phone_variants() -> None:
    assert normalize_phone("+91 9876543210") == "+919876543210"
    assert normalize_phone("09876543210") == "+919876543210"
    assert normalize_phone("98765 43210") == "+919876543210"
    assert normalize_phone("+91-98765-43210") == "+919876543210"


def test_preserves_indian_landline_with_std_code() -> None:
    assert normalize_phone("040-12345678") == "040-12345678"


def test_extracts_tel_visible_phone_and_public_emails() -> None:
    phones, emails = extract_contacts(
        """
        <html><body>
          <h1>Contact ABC Dental</h1>
          <a href="tel:+91-98765-43210">Call us</a>
          <p>Phone: 040-12345678</p>
          <a href="mailto:Info@ABCDental.in?subject=Appointment">Email</a>
          <p>Support@ABCDental.in</p>
          <p>example@example.com</p>
        </body></html>
        """,
        "https://abcdental.in/contact-us",
    )

    assert [(phone.value, phone.confidence) for phone in phones] == [
        ("+919876543210", "high"),
        ("040-12345678", "medium"),
    ]
    assert [(email.value, email.confidence) for email in emails] == [
        ("Info@abcdental.in", "high"),
        ("Support@abcdental.in", "medium"),
    ]


def test_duplicate_emails_and_placeholders_are_rejected() -> None:
    _, emails = extract_contacts(
        """
        <a href="mailto:hello@clinic.in">Mail</a>
        <p>hello@clinic.in</p>
        <p>test@example.com</p>
        """,
        "https://clinic.in/contact",
    )

    assert [email.value for email in emails] == ["hello@clinic.in"]
    assert normalize_email("mailto:test@example.com") is None


def test_contact_links_stay_on_the_same_registrable_domain() -> None:
    links = find_contact_links(
        """
        <a href="/contact-us">Contact Us</a>
        <a href="https://help.clinic.co.in/about">About</a>
        <a href="https://facebook.com/clinic">Contact on Facebook</a>
        <a href="https://evil.example/contact">Contact</a>
        """,
        "https://www.clinic.co.in/",
    )

    assert links == (
        "https://www.clinic.co.in/contact-us",
        "https://help.clinic.co.in/about",
    )


def test_normalizes_website_urls_without_forcing_existing_scheme() -> None:
    assert normalize_website_url("company.in") == "https://company.in"
    assert normalize_website_url("http://www.company.in/") == "http://www.company.in"


def test_extracts_nested_json_ld_contacts_but_ignores_regular_scripts() -> None:
    phones, emails = extract_contacts(
        """
        <script>const tracking = 'pixel@tracking.example'; const phone = '9876540000';</script>
        <script type="application/ld+json">
          {"@type":"Restaurant","contactPoint":{"telephone":"+91 98765 43210",
          "email":"bookings@restaurant.in"}}
        </script>
        """,
        "https://restaurant.in/",
    )

    assert [(value.value, value.source_type) for value in phones] == [
        ("+919876543210", "json_ld")
    ]
    assert [(value.value, value.source_type) for value in emails] == [
        ("bookings@restaurant.in", "json_ld")
    ]


def test_whatsapp_requires_an_explicit_numbered_link() -> None:
    parsed = parse_html(
        """
        <p>WhatsApp our normal phone number: 98765 40000</p>
        <a href="https://wa.me/919876543210">WhatsApp</a>
        <a href="https://api.whatsapp.com/send?phone=919123456789">Chat</a>
        <a href="https://wa.me/">Unnumbered WhatsApp</a>
        """
    )

    numbers = extract_whatsapp_numbers([("https://restaurant.in", parsed)])

    assert [(value.value, value.source_type) for value in numbers] == [
        ("+919876543210", "whatsapp_link"),
        ("+919123456789", "whatsapp_link"),
    ]


def test_non_contact_and_tracking_emails_are_rejected() -> None:
    assert normalize_email("noreply@restaurant.in") is None
    assert normalize_email("tracking@restaurant.in") is None
    assert normalize_email("hello@restaurant.in") == "hello@restaurant.in"
