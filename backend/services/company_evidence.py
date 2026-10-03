"""Company-identity checks that do not depend on a company being famous."""

from typing import Optional
from urllib.parse import urlparse


PERSONAL_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "yahoo.in", "outlook.com", "hotmail.com",
    "rediffmail.com", "protonmail.com", "aol.com", "ymail.com", "mail.com",
    "inbox.com", "zoho.com", "icloud.com", "live.com", "yandex.com",
}
SUSPICIOUS_TLDS = (".xyz", ".tk", ".ml", ".ga", ".cf", ".gq", ".buzz", ".top")


def _domain(value: str) -> str:
    value = value.strip().lower()
    if not value:
        return ""
    if "@" in value and "://" not in value:
        return value.rsplit("@", 1)[-1]
    parsed = urlparse(value if "://" in value else f"https://{value}")
    return (parsed.hostname or "").removeprefix("www.")


def _domains_match(left: str, right: str) -> bool:
    return bool(left and right and (left == right or left.endswith(f".{right}") or right.endswith(f".{left}")))


def evaluate_company_evidence(
    company_name: Optional[str],
    company_website: Optional[str],
    contact_email: Optional[str],
) -> list[dict]:
    """Return concrete identity inconsistencies, never a fame-based score."""
    flags: list[dict] = []
    website_domain = _domain(company_website or "")
    email_domain = _domain(contact_email or "")

    if company_website and not website_domain:
        flags.append({"rule": "provided_website_check", "severity": "medium", "message": "The company website address could not be read. Check that it is a complete domain, such as company.in.", "score": 0.45})
    elif website_domain and website_domain.endswith(SUSPICIOUS_TLDS):
        flags.append({"rule": "provided_website_check", "severity": "high", "message": f"The supplied company website uses {website_domain}. Verify the domain through an independent source before responding.", "score": 0.7})

    if email_domain in PERSONAL_EMAIL_DOMAINS:
        flags.append({"rule": "provided_email_check", "severity": "high", "message": f"The supplied contact email uses {email_domain}, a personal email service. Verify the recruiter through the company's published contact channel.", "score": 0.8})
    elif website_domain and email_domain and not _domains_match(website_domain, email_domain):
        flags.append({"rule": "company_identity_mismatch", "severity": "medium", "message": f"The contact email domain ({email_domain}) does not match the supplied website ({website_domain}). This can be legitimate for a recruiter, but verify it independently.", "score": 0.5})

    return flags
