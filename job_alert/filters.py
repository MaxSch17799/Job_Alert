from __future__ import annotations

from .models import JobPosting, KeywordProfile, SiteConfig
from .utils import normalize_text, unique_preserve

GENERIC_ENGINEERING_HINTS = (
    "engineer",
    "engineering",
    "systems",
    "electrical",
    "electronics",
    "avionics",
    "mission",
    "operations",
    "integration",
    "test",
    "verification",
    "validation",
    "propulsion",
    "power",
    "satellite",
    "spacecraft",
    "space ",
    "radar",
    "ground segment",
    "flight",
    "payload",
    "copernicus",
    "telemetry",
    "tt&c",
)


def effective_profile(site: SiteConfig, profile: KeywordProfile) -> KeywordProfile:
    include_any = list(profile.include_any) if site.use_profile_defaults else []
    exclude_any = list(profile.exclude_any) if site.use_profile_defaults else []
    location_any = list(profile.location_any) if site.use_profile_defaults else []
    contract_type_any = list(profile.contract_type_any) if site.use_profile_defaults else []
    language_any = list(profile.language_any) if site.use_profile_defaults else []
    include_any.extend(site.include_any)
    exclude_any.extend(site.exclude_any)
    location_any.extend(site.filters.location_any)
    contract_type_any.extend(site.filters.contract_type_any)
    language_any.extend(site.filters.language_any)
    return KeywordProfile(
        include_any=unique_preserve(include_any),
        exclude_any=unique_preserve(exclude_any),
        location_any=unique_preserve(location_any),
        contract_type_any=unique_preserve(contract_type_any),
        language_any=unique_preserve(language_any),
    )


def match_job(job: JobPosting, profile: KeywordProfile, broad_match: bool) -> tuple[bool, list[str]]:
    haystack = normalize_text(job.combined_text)
    exclude_hits = [term for term in profile.exclude_any if normalize_text(term) in haystack]
    if exclude_hits:
        return False, exclude_hits

    include_hits = [term for term in profile.include_any if normalize_text(term) in haystack]
    broad_hits = [hint for hint in GENERIC_ENGINEERING_HINTS if hint in haystack]
    if profile.include_any and not include_hits and not broad_match:
        return False, []
    if profile.include_any and not include_hits and broad_match and not broad_hits:
        return False, []

    matched_terms: list[str] = []
    if profile.location_any:
        matched_terms.extend(term for term in profile.location_any if normalize_text(term) in haystack)
    if profile.contract_type_any:
        matched_terms.extend(term for term in profile.contract_type_any if normalize_text(term) in haystack)
    if profile.language_any:
        matched_terms.extend(term for term in profile.language_any if normalize_text(term) in haystack)

    if profile.include_any:
        matched_terms.extend(include_hits or (["broad-match"] + broad_hits[:3] if broad_match else []))
    else:
        matched_terms.append("no-include-filter")
    return True, unique_preserve(matched_terms)
