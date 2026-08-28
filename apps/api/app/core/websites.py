from typing import Literal
from urllib.parse import urlsplit

WebsiteType = Literal["official", "directory", "social", "candidate", "unknown", "none"]

DIRECTORY_DOMAINS = frozenset(
    {
        "agoda.com",
        "booking.com",
        "dineout.co.in",
        "eazydiner.com",
        "foursquare.com",
        "g.co",
        "goibibo.com",
        "google.com",
        "google.co.in",
        "indiamart.com",
        "justdial.com",
        "magicpin.in",
        "makemytrip.com",
        "mouthshut.com",
        "olacabs.com",
        "oyo.com",
        "practo.com",
        "restaurant-guru.in",
        "restaurantguru.com",
        "sulekha.com",
        "swiggy.com",
        "tripadvisor.com",
        "yelp.com",
        "zomato.com",
    }
)

SOCIAL_DOMAINS = frozenset(
    {
        "api.whatsapp.com",
        "facebook.com",
        "instagram.com",
        "linkedin.com",
        "twitter.com",
        "wa.me",
        "whatsapp.com",
        "x.com",
        "youtube.com",
        "youtu.be",
    }
)


def normalized_domain(value: str) -> str | None:
    candidate = value.strip()
    if not candidate:
        return None
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    try:
        host = urlsplit(candidate).hostname
    except ValueError:
        return None
    return host.casefold().removeprefix("www.") if host else None


def _matches(host: str, domains: frozenset[str]) -> bool:
    return any(host == domain or host.endswith(f".{domain}") for domain in domains)


def classify_website_url(value: str | None) -> WebsiteType:
    if not value or not (host := normalized_domain(value)):
        return "none"
    if _matches(host, DIRECTORY_DOMAINS):
        return "directory"
    if _matches(host, SOCIAL_DOMAINS):
        return "social"
    return "official"


def is_directory_or_social(value: str | None) -> bool:
    return classify_website_url(value) in {"directory", "social"}
