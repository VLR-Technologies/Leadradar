import re
from urllib.parse import urlsplit, urlunsplit

_EMAIL_PATTERN = re.compile(
    r"^[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?"
    r"(?:\.[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?)+$",
    re.IGNORECASE,
)
_PLACEHOLDER_EMAILS = {
    "example@example.com",
    "test@example.com",
    "email@example.com",
    "name@example.com",
}
_PLACEHOLDER_DOMAINS = {"example.com", "example.org", "example.net", "example.test"}
_ASSET_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".css", ".js")
_NON_CONTACT_LOCAL_PARTS = {
    "donotreply",
    "do-not-reply",
    "no-reply",
    "noreply",
    "null",
    "pixel",
    "test",
    "tracking",
}


def split_public_values(value: str | None) -> tuple[str, ...]:
    """Split provider list fields without inventing or reformatting their public values."""
    if not value:
        return ()
    values = [item.strip() for item in re.split(r"\s*[;,]\s*", value) if item.strip()]
    return tuple(dict.fromkeys(values))


def normalize_phone(value: str) -> str | None:
    cleaned = value.strip()
    if cleaned.lower().startswith("tel:"):
        cleaned = cleaned[4:]
    cleaned = cleaned.split("?", 1)[0]
    cleaned = re.sub(r"(?:ext\.?|extension|x)\s*\d+$", "", cleaned, flags=re.IGNORECASE).strip()
    digits = re.sub(r"\D", "", cleaned)
    if not 8 <= len(digits) <= 15 or len(set(digits)) == 1:
        return None

    if len(digits) == 12 and digits.startswith("91") and digits[2] in "6789":
        return f"+91{digits[2:]}"
    if len(digits) == 11 and digits.startswith("0") and digits[1] in "6789":
        return f"+91{digits[1:]}"
    if len(digits) == 10 and digits[0] in "6789":
        return f"+91{digits}"

    landline_match = re.fullmatch(
        r"(?:\+91[-\s]?)?(0\d{2,4})[-\s](\d{6,8})",
        cleaned,
    )
    if landline_match:
        return f"{landline_match.group(1)}-{landline_match.group(2)}"

    if cleaned.startswith("+"):
        return f"+{digits}"
    return digits if not cleaned.startswith("0") else f"0{digits.lstrip('0')}"


def normalize_email(value: str) -> str | None:
    cleaned = value.strip().strip("<>.,;:()[]{}\"'")
    if cleaned.lower().startswith("mailto:"):
        cleaned = cleaned[7:].split("?", 1)[0]
    if "@" not in cleaned:
        return None
    local_part, domain = cleaned.rsplit("@", 1)
    normalized = f"{local_part}@{domain.lower()}"
    if not _EMAIL_PATTERN.fullmatch(normalized):
        return None
    if normalized.lower() in _PLACEHOLDER_EMAILS or domain.lower() in _PLACEHOLDER_DOMAINS:
        return None
    if local_part.casefold() in _NON_CONTACT_LOCAL_PARTS:
        return None
    if local_part.lower().endswith(_ASSET_SUFFIXES):
        return None
    return normalized


def normalize_website_url(value: str) -> str | None:
    cleaned = value.strip()
    if not cleaned:
        return None
    if "://" not in cleaned:
        cleaned = f"https://{cleaned}"
    try:
        parsed = urlsplit(cleaned)
        host = parsed.hostname
        port = parsed.port
    except ValueError:
        return None
    if parsed.scheme.lower() not in {"http", "https"} or not host:
        return None
    netloc = host.lower()
    if port:
        netloc = f"{netloc}:{port}"
    path = parsed.path or ""
    if path == "/":
        path = ""
    return urlunsplit((parsed.scheme.lower(), netloc, path, parsed.query, ""))
