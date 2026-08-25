import asyncio
import ipaddress
import re
import socket
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import httpx

from app.models.business import Business
from app.models.enrichment import ExtractedContact, WebsiteInspection
from app.normalizers.contact import normalize_email, normalize_phone, normalize_website_url
from app.providers.enrichment.base import (
    RobotsDisallowedError,
    WebsiteAccessDeniedError,
    WebsiteDnsError,
    WebsiteParserError,
    WebsiteSafetyError,
    WebsiteTimeoutError,
    WebsiteUnavailableError,
)


_CONTACT_TERMS = (
    "contact",
    "contact us",
    "contact-us",
    "contactus",
    "about",
    "about us",
    "about-us",
    "reach us",
    "reach-us",
    "get in touch",
    "enquiry",
    "enquiries",
)
_CONTACT_LABEL_PATTERN = re.compile(
    r"(?:phone|mobile|call|telephone|tel|contact)\s*(?:number|no\.?|us)?\s*[:\-]?\s*"
    r"((?:\+?91[-\s.]?)?(?:0[-\s.]?)?[6-9]\d{4}[-\s.]?\d{5}|"
    r"(?:\+?91[-\s.]?)?0\d{2,4}[-\s.]\d{6,8}|"
    r"\+\d{1,3}(?:[-\s().]*\d){7,14})",
    re.IGNORECASE,
)
_PHONE_PATTERN = re.compile(
    r"(?<!\d)(?:"
    r"(?:\+?91[-\s.]?)?(?:0[-\s.]?)?[6-9]\d{4}[-\s.]?\d{5}|"
    r"(?:\+?91[-\s.]?)?0\d{2,4}[-\s.]\d{6,8}|"
    r"\+\d{1,3}(?:[-\s().]*\d){7,14}"
    r")(?!\d)",
)
_EMAIL_PATTERN = re.compile(
    r"[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Z0-9-]+(?:\.[A-Z0-9-]+)+",
    re.IGNORECASE,
)
_COMMON_SECOND_LEVEL_SUFFIXES = {
    "co.in",
    "com.au",
    "com.br",
    "com.sg",
    "co.uk",
    "org.in",
    "org.uk",
    "net.in",
    "net.au",
}
_NON_OFFICIAL_PLATFORM_DOMAINS = {
    "booking.com",
    "facebook.com",
    "g.co",
    "google.com",
    "google.co.in",
    "instagram.com",
    "justdial.com",
    "practo.com",
    "swiggy.com",
    "tripadvisor.com",
    "youtube.com",
    "youtu.be",
    "zomato.com",
}
_NAME_STOPWORDS = {
    "and",
    "clinic",
    "company",
    "dental",
    "dentist",
    "hospital",
    "hotel",
    "india",
    "limited",
    "llp",
    "pvt",
    "restaurant",
    "services",
    "the",
}


@dataclass(frozen=True, slots=True)
class ParsedHtml:
    text_chunks: tuple[str, ...]
    links: tuple[tuple[str, str], ...]

    @property
    def text(self) -> str:
        return "\n".join(self.text_chunks)


@dataclass(frozen=True, slots=True)
class FetchedDocument:
    url: str
    status_code: int
    content_type: str
    text: str


class _ContactHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text_chunks: list[str] = []
        self.links: list[tuple[str, str]] = []
        self._ignored_depth = 0
        self._active_href: str | None = None
        self._active_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.casefold()
        if lowered in {"script", "style", "noscript", "template"}:
            self._ignored_depth += 1
            return
        if lowered == "a":
            attributes = dict(attrs)
            self._active_href = attributes.get("href")
            self._active_text = []

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.casefold()
        if lowered in {"script", "style", "noscript", "template"}:
            self._ignored_depth = max(0, self._ignored_depth - 1)
            return
        if lowered == "a" and self._active_href:
            self.links.append((self._active_href, " ".join(self._active_text).strip()))
            self._active_href = None
            self._active_text = []

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        cleaned = " ".join(data.split())
        if not cleaned:
            return
        self.text_chunks.append(cleaned)
        if self._active_href is not None:
            self._active_text.append(cleaned)


def parse_html(html: str) -> ParsedHtml:
    parser = _ContactHtmlParser()
    parser.feed(html)
    return ParsedHtml(tuple(parser.text_chunks), tuple(parser.links))


def registrable_domain(host: str) -> str:
    labels = host.casefold().strip(".").split(".")
    if len(labels) <= 2:
        return ".".join(labels)
    last_two = ".".join(labels[-2:])
    if last_two in _COMMON_SECOND_LEVEL_SUFFIXES and len(labels) >= 3:
        return ".".join(labels[-3:])
    return last_two


def find_contact_links(html: str, page_url: str) -> tuple[str, ...]:
    parsed = parse_html(html)
    page_host = urlsplit(page_url).hostname
    if not page_host:
        return ()
    expected_domain = registrable_domain(page_host)
    ranked: list[tuple[int, str]] = []
    seen: set[str] = set()
    for href, anchor_text in parsed.links:
        lowered_href = href.strip().casefold()
        if not lowered_href or lowered_href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        candidate = urljoin(page_url, href)
        parsed_candidate = urlsplit(candidate)
        if parsed_candidate.scheme not in {"http", "https"} or not parsed_candidate.hostname:
            continue
        if registrable_domain(parsed_candidate.hostname) != expected_domain:
            continue
        searchable = f"{parsed_candidate.path} {anchor_text}".casefold().replace("_", " ")
        matched_terms = [term for term in _CONTACT_TERMS if term in searchable]
        if not matched_terms:
            continue
        normalized = urlunsplit(
            (
                parsed_candidate.scheme,
                parsed_candidate.netloc,
                parsed_candidate.path or "/",
                parsed_candidate.query,
                "",
            )
        )
        if normalized in seen:
            continue
        seen.add(normalized)
        rank = 0 if any("contact" in term or "reach" in term for term in matched_terms) else 1
        ranked.append((rank, normalized))
    ranked.sort(key=lambda item: item[0])
    return tuple(url for _, url in ranked)


def extract_contacts(html: str, page_url: str) -> tuple[tuple[ExtractedContact, ...], tuple[ExtractedContact, ...]]:
    parsed = parse_html(html)
    phone_candidates: list[ExtractedContact] = []
    email_candidates: list[ExtractedContact] = []

    for href, _ in parsed.links:
        if href.casefold().startswith("tel:"):
            normalized_phone = normalize_phone(href)
            if normalized_phone:
                phone_candidates.append(ExtractedContact(normalized_phone, "high", page_url))
        elif href.casefold().startswith("mailto:"):
            normalized_email = normalize_email(href)
            if normalized_email:
                email_candidates.append(ExtractedContact(normalized_email, "high", page_url))

    text = parsed.text
    contact_page = any(term.replace(" ", "-") in urlsplit(page_url).path.casefold() for term in _CONTACT_TERMS)
    visible_phones = (
        [match.group(1) for match in _CONTACT_LABEL_PATTERN.finditer(text)]
        if not contact_page
        else [match.group(0) for match in _PHONE_PATTERN.finditer(text)]
    )
    for value in visible_phones:
        normalized_phone = normalize_phone(value)
        if normalized_phone:
            phone_candidates.append(ExtractedContact(normalized_phone, "medium", page_url))
    for match in _EMAIL_PATTERN.finditer(text):
        normalized_email = normalize_email(match.group(0))
        if normalized_email:
            email_candidates.append(ExtractedContact(normalized_email, "medium", page_url))

    return _deduplicate_contacts(phone_candidates), _deduplicate_contacts(email_candidates)


def _deduplicate_contacts(values: list[ExtractedContact]) -> tuple[ExtractedContact, ...]:
    confidence_rank = {"high": 0, "medium": 1, "low": 2}
    ordered = sorted(values, key=lambda value: confidence_rank[value.confidence])
    seen: set[str] = set()
    result: list[ExtractedContact] = []
    for value in ordered:
        key = value.value.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return tuple(result)


def _normalize_words(value: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[a-z0-9]+", value.casefold()))


def website_matches_business(business: Business, page_text: str) -> bool:
    page_words = set(_normalize_words(page_text))
    raw_name_words = _normalize_words(business.name)
    meaningful_name_words = tuple(
        word for word in raw_name_words if len(word) >= 3 and word not in _NAME_STOPWORDS
    ) or raw_name_words
    if not meaningful_name_words or not page_words:
        return False

    normalized_name = " ".join(raw_name_words)
    normalized_page = " ".join(_normalize_words(page_text))
    if normalized_name and normalized_name in normalized_page:
        return True

    overlap = sum(word in page_words for word in meaningful_name_words) / len(meaningful_name_words)
    city_words = _normalize_words(business.address.city or "")
    city_matches = bool(city_words) and all(word in page_words for word in city_words)
    if overlap >= 0.67 or (overlap >= 0.5 and city_matches):
        return True

    known_email = normalize_email(business.email or "")
    if known_email and known_email.casefold() in page_text.casefold() and overlap >= 0.34:
        return True
    known_phone = normalize_phone(business.phone or "")
    page_digits = re.sub(r"\D", "", page_text)
    if known_phone and re.sub(r"\D", "", known_phone) in page_digits and overlap >= 0.34:
        return True
    return False


async def _assert_public_host(host: str) -> None:
    if host.casefold() == "localhost" or host.casefold().endswith(".local"):
        raise WebsiteSafetyError("Local website addresses are not permitted.")
    try:
        addresses = {ipaddress.ip_address(host)}
    except ValueError:
        try:
            records = await asyncio.to_thread(
                socket.getaddrinfo,
                host,
                None,
                socket.AF_UNSPEC,
                socket.SOCK_STREAM,
            )
        except OSError as exc:
            raise WebsiteDnsError("The website hostname could not be resolved.") from exc
        addresses = {ipaddress.ip_address(record[4][0]) for record in records}
    if not addresses or any(not address.is_global for address in addresses):
        raise WebsiteSafetyError("Private or non-public website addresses are not permitted.")


class WebsiteEnrichmentProvider:
    def __init__(
        self,
        *,
        timeout_seconds: float = 10.0,
        max_pages: int = 4,
        max_response_bytes: int = 1_000_000,
        max_contacts_per_kind: int = 5,
        max_redirects: int = 4,
        user_agent: str = "LeadRadar/0.1",
        transport: httpx.AsyncBaseTransport | None = None,
        host_validator: Callable[[str], Awaitable[None]] = _assert_public_host,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_pages = max_pages
        self.max_response_bytes = max_response_bytes
        self.max_contacts_per_kind = max_contacts_per_kind
        self.max_redirects = max_redirects
        self.user_agent = user_agent
        self.transport = transport
        self.host_validator = host_validator

    async def inspect(self, *, business: Business, website_url: str) -> WebsiteInspection:
        normalized_url = normalize_website_url(website_url)
        if not normalized_url:
            raise WebsiteSafetyError("The listed website URL is invalid.")
        parsed_start = urlsplit(normalized_url)
        if parsed_start.username or parsed_start.password:
            raise WebsiteSafetyError("Website URLs with embedded credentials are not permitted.")
        start_host = parsed_start.hostname
        if not start_host:
            raise WebsiteSafetyError("The listed website URL has no hostname.")
        expected_domain = registrable_domain(start_host)

        queue: deque[str] = deque([normalized_url])
        queued = {normalized_url}
        visited: list[str] = []
        parsed_pages: list[tuple[str, ParsedHtml]] = []
        robots_cache: dict[str, RobotFileParser | bool] = {}

        timeout = httpx.Timeout(self.timeout_seconds)
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=False,
            headers={"User-Agent": self.user_agent, "Accept": "text/html,application/xhtml+xml"},
            transport=self.transport,
        ) as client:
            while queue and len(visited) < self.max_pages:
                current_url = queue.popleft()
                if not await self._robots_allowed(
                    client=client,
                    url=current_url,
                    expected_domain=expected_domain,
                    cache=robots_cache,
                ):
                    if not visited:
                        raise RobotsDisallowedError("The website does not permit automated inspection.")
                    continue
                document = await self._fetch_document(
                    client=client,
                    url=current_url,
                    expected_domain=expected_domain,
                )
                if document.status_code in {401, 403}:
                    raise WebsiteAccessDeniedError("The website refused automated access.")
                if not 200 <= document.status_code < 300:
                    if not visited:
                        raise WebsiteUnavailableError("The website returned an unsuccessful response.")
                    continue
                if "html" not in document.content_type.casefold() and "<html" not in document.text[:500].casefold():
                    if not visited:
                        raise WebsiteUnavailableError("The website did not return an HTML page.")
                    continue
                if document.url in visited:
                    continue
                visited.append(document.url)
                try:
                    parsed_document = parse_html(document.text)
                    contact_links = find_contact_links(document.text, document.url)
                except Exception as exc:
                    raise WebsiteParserError("The website HTML could not be processed.") from exc
                parsed_pages.append((document.url, parsed_document))
                for contact_url in contact_links:
                    if contact_url not in queued and len(queued) < self.max_pages * 4:
                        queue.append(contact_url)
                        queued.add(contact_url)

        combined_text = "\n".join(page.text for _, page in parsed_pages)
        final_url = visited[0] if visited else normalized_url
        if not parsed_pages or not website_matches_business(business, combined_text):
            return WebsiteInspection(
                verification_status="mismatch",
                final_url=final_url,
                visited_pages=tuple(visited),
                message="The listed website could not be confidently matched to this business.",
            )

        phones: list[ExtractedContact] = []
        emails: list[ExtractedContact] = []
        try:
            for page_url, parsed_page in parsed_pages:
                page_phones, page_emails = extract_contacts(
                    parsed_page.text + _links_as_html(parsed_page),
                    page_url,
                )
                phones.extend(page_phones)
                emails.extend(page_emails)
        except Exception as exc:
            raise WebsiteParserError("Public contact details could not be processed.") from exc
        return WebsiteInspection(
            verification_status="verified",
            final_url=final_url,
            phones=_deduplicate_contacts(phones)[: self.max_contacts_per_kind],
            emails=_deduplicate_contacts(emails)[: self.max_contacts_per_kind],
            visited_pages=tuple(visited),
            message="Official website verified and public contact pages inspected.",
        )

    async def _robots_allowed(
        self,
        *,
        client: httpx.AsyncClient,
        url: str,
        expected_domain: str,
        cache: dict[str, RobotFileParser | bool],
    ) -> bool:
        parsed = urlsplit(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        cached = cache.get(origin)
        if cached is False:
            return False
        if isinstance(cached, RobotFileParser):
            return cached.can_fetch(self.user_agent, url)

        robots_url = f"{origin}/robots.txt"
        try:
            document = await self._fetch_document(
                client=client,
                url=robots_url,
                expected_domain=expected_domain,
                response_limit=min(self.max_response_bytes, 128_000),
            )
        except (WebsiteTimeoutError, WebsiteUnavailableError):
            cache[origin] = RobotFileParser()
            return True
        if document.status_code in {401, 403}:
            cache[origin] = False
            return False
        parser = RobotFileParser()
        if 200 <= document.status_code < 300:
            parser.set_url(robots_url)
            parser.parse(document.text.splitlines())
        else:
            parser.parse([])
        cache[origin] = parser
        return parser.can_fetch(self.user_agent, url)

    async def _fetch_document(
        self,
        *,
        client: httpx.AsyncClient,
        url: str,
        expected_domain: str,
        response_limit: int | None = None,
    ) -> FetchedDocument:
        current_url = url
        limit = response_limit or self.max_response_bytes
        for _ in range(self.max_redirects + 1):
            await self._validate_url(current_url, expected_domain)
            try:
                request = client.build_request("GET", current_url)
                response = await client.send(request, stream=True)
            except httpx.TimeoutException as exc:
                raise WebsiteTimeoutError("The website took too long to respond.") from exc
            except httpx.HTTPError as exc:
                raise WebsiteUnavailableError("The website could not be reached.") from exc

            try:
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        raise WebsiteUnavailableError("The website returned an invalid redirect.")
                    current_url = urljoin(str(response.url), location)
                    continue
                content_length = response.headers.get("content-length")
                declared_length = (
                    int(content_length)
                    if content_length and content_length.isdigit()
                    else None
                )
                if declared_length and declared_length > limit:
                    raise WebsiteUnavailableError("The website response was too large to inspect safely.")
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > limit:
                        raise WebsiteUnavailableError("The website response was too large to inspect safely.")
                encoding = response.encoding or "utf-8"
                return FetchedDocument(
                    url=str(response.url),
                    status_code=response.status_code,
                    content_type=response.headers.get("content-type", ""),
                    text=bytes(body).decode(encoding, errors="replace"),
                )
            finally:
                await response.aclose()
        raise WebsiteUnavailableError("The website redirected too many times.")

    async def _validate_url(self, url: str, expected_domain: str) -> None:
        try:
            parsed = urlsplit(url)
            port = parsed.port
        except ValueError as exc:
            raise WebsiteSafetyError("The website URL is invalid.") from exc
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise WebsiteSafetyError("Only public HTTP and HTTPS websites are permitted.")
        if parsed.username or parsed.password or port not in {None, 80, 443}:
            raise WebsiteSafetyError("The website URL contains unsupported connection details.")
        if registrable_domain(parsed.hostname) != expected_domain:
            raise WebsiteSafetyError("The website redirected outside its original domain.")
        if registrable_domain(parsed.hostname) in _NON_OFFICIAL_PLATFORM_DOMAINS:
            raise WebsiteSafetyError("Third-party directory and social platform pages are not crawled.")
        await self.host_validator(parsed.hostname)


def _links_as_html(parsed: ParsedHtml) -> str:
    return "".join(
        f'<a href="{href}">{text}</a>'
        for href, text in parsed.links
    )
