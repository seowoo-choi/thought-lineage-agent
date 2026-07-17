from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

# Explicit allow-list. Unknown hosts are rejected even when they are not blocked.
# The value is (publisher type, deterministic evidence grade).
ALLOWED_DOMAINS = {
    "gutenberg.org": ("primary_text_repository", "A"),
    "loc.gov": ("national_library", "A"),
    "bl.uk": ("national_library", "A"),
    "bnf.fr": ("national_library", "A"),
    "cambridge.org": ("academic_publisher", "A"),
    "oup.com": ("academic_publisher", "A"),
    "oxfordreference.com": ("academic_reference", "A"),
    "jstor.org": ("scholarly_archive", "A"),
    "doi.org": ("scholarly_identifier", "A"),
    "poetryfoundation.org": ("edited_cultural_institution", "B"),
    "britannica.com": ("edited_encyclopedia", "B"),
    "encyclopedia.com": ("edited_encyclopedia", "B"),
    "neh.gov": ("government_cultural_institution", "B"),
    "smithsonianmag.com": ("edited_cultural_institution", "B"),
    "springer.com": ("academic_publisher", "A"),
    "wiley.com": ("academic_publisher", "A"),
    "cuni.cz": ("university_journal", "A"),
    "uwm.edu.pl": ("university_journal", "A"),
    "ugr.es": ("university_journal", "A"),
    "virginia.edu": ("university_repository", "B"),
    "thelondonmagazine.org": ("edited_literary_journal", "B"),
    "byu.edu": ("university_research_publication", "B"),
    "degruyterbrill.com": ("academic_publisher", "A"),
    "ucl.ac.uk": ("university_repository", "A"),
    "dostmirkult.ru": ("peer_reviewed_journal", "A"),
    "univr.it": ("university_journal", "A"),
    "mdpi.com": ("peer_reviewed_journal", "B"),
    "montclair.edu": ("university_faculty_publication", "B"),
    "northwestern.edu": ("university_press_or_repository", "A"),
    "indiana.edu": ("university_press", "A"),
    "granta.com": ("edited_literary_journal_primary_essay", "B"),
    "uplopen.com": ("academic_book_platform", "A"),
    "nybooks.com": ("edited_literary_review", "B"),
    "theparisreview.org": ("edited_literary_journal", "B"),
    "fordhampress.com": ("university_press", "A"),
    "degruyter.com": ("academic_publisher", "A"),
}
SEARCH_HOSTS = {"google.com", "bing.com", "duckduckgo.com", "search.yahoo.com"}


def _registrable_host(host: str) -> str:
    host = host.lower().strip(".").removeprefix("www.")
    for domain in ALLOWED_DOMAINS:
        if host == domain or host.endswith("." + domain):
            return domain
    return host


def classify(url: str) -> dict:
    try:
        parsed = urlparse(url)
    except ValueError:
        return {"allowed": False, "reason": "malformed_url"}
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return {"allowed": False, "reason": "http_url_required"}
    host = parsed.hostname.lower().removeprefix("www.")
    if host in SEARCH_HOSTS or any(host.endswith("." + h) for h in SEARCH_HOSTS):
        return {"allowed": False, "reason": "search_results_page", "domain": host}
    domain = _registrable_host(host)
    policy = ALLOWED_DOMAINS.get(domain)
    if policy is None:
        return {"allowed": False, "reason": "unclassified_domain", "domain": domain}
    # Prevent allow-listed redirect wrappers from laundering arbitrary URLs.
    query = parse_qs(parsed.query)
    if any(k.lower() in {"url", "target", "redirect", "redirect_uri"} for k in query):
        return {"allowed": False, "reason": "redirect_wrapper", "domain": domain}
    return {"allowed": True, "reason": "explicit_allowlist", "domain": domain,
            "publisher_type": policy[0], "maximum_grade": policy[1]}


def publisher_key(source: dict) -> str:
    return classify(source.get("url", "")).get("domain", "")


def allowed(url: str) -> bool:
    return classify(url)["allowed"]


def check_url(url: str, timeout: int = 12) -> dict:
    checked_at = datetime.now(timezone.utc).isoformat()
    policy = classify(url)
    base = {"url": url, "checked_at": checked_at, "policy": policy,
            "method": None, "status_code": 0, "final_url": url, "ok": False}
    if not policy["allowed"]:
        return base
    headers = {"User-Agent": "Mozilla/5.0 book-atlas-audit/0.2", "Accept": "text/html,application/xhtml+xml"}
    errors = []
    for method in ("HEAD", "GET"):
        try:
            with urlopen(Request(url, headers=headers, method=method), timeout=timeout) as response:
                base.update(method=method, status_code=response.status, final_url=response.url,
                            ok=200 <= response.status < 400)
                if base["ok"]:
                    return base
        except Exception as exc:  # audit output must preserve failures, not hide them
            errors.append(f"{method}:{type(exc).__name__}:{exc}")
    base["errors"] = errors
    return base
