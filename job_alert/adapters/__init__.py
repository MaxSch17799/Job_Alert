from __future__ import annotations

from urllib.parse import urlparse

from bs4 import BeautifulSoup

from ..models import ResolvedSite, SiteConfig
from ..utils import absolute_url
from .base import create_session
from .browser_links import BrowserLinksAdapter
from .html_links import HtmlLinksAdapter
from .lufthansa import LufthansaAdapter
from .onlyfy import OnlyfyAdapter
from .successfactors import SuccessFactorsAdapter
from .workday import WorkdayAdapter


ADAPTERS = {
    "workday": WorkdayAdapter(),
    "onlyfy": OnlyfyAdapter(),
    "html_links": HtmlLinksAdapter(),
    "browser_links": BrowserLinksAdapter(),
    "lufthansa": LufthansaAdapter(),
    "successfactors": SuccessFactorsAdapter(),
}


def get_adapter(name: str):
    if name not in ADAPTERS:
        raise KeyError(f"Unsupported adapter: {name}")
    return ADAPTERS[name]


def _esa_search_url(parsed) -> str:
    origin = f"{parsed.scheme}://{parsed.netloc}"
    return f"{origin}/search/?createNewAlert=false&q=&locationsearch="


def resolve_site(site: SiteConfig, timeout_seconds: int, logger) -> ResolvedSite:
    if site.type and site.type != "auto":
        return ResolvedSite(adapter_name=site.type, resolved_url=site.source_url, notes=["manual adapter override"])

    source_url = site.source_url
    lowered = source_url.casefold()
    parsed = urlparse(source_url)
    if parsed.netloc == "jobs.esa.int" and "/search/" not in parsed.path:
        return ResolvedSite("html_links", _esa_search_url(parsed), ["resolved ESA landing page to search results"])
    if "careers.smartrecruiters.com/cern" in lowered or parsed.netloc == "careers.cern":
        return ResolvedSite("html_links", "https://careers.cern/jobs/", ["resolved CERN landing page to jobs board"])
    if "myworkdayjobs.com" in lowered:
        return ResolvedSite("workday", source_url, ["detected Workday from URL"])
    if "onlyfy.jobs" in lowered:
        return ResolvedSite("onlyfy", source_url, ["detected onlyfy from URL"])
    if "lufthansa-technik.com" in lowered or "lufthansagroup.careers" in lowered or "api-apply.lufthansagroup.careers" in lowered:
        return ResolvedSite("lufthansa", source_url, ["detected Lufthansa Group career board"])
    if "successfactors" in lowered:
        return ResolvedSite("successfactors", source_url, ["detected SuccessFactors board"])
    if "smartrecruiters.com" in lowered:
        return ResolvedSite("html_links", source_url, ["treated as static jobs page"])
    if "career-ohb.csod.com" in lowered or "jobs.esa.int" in lowered:
        return ResolvedSite("browser_links", source_url, ["detected dynamic portal"])

    session = create_session()
    response = session.get(source_url, timeout=timeout_seconds)
    response.raise_for_status()
    final_url = response.url or source_url
    final_lowered = final_url.casefold()
    final_parsed = urlparse(final_url)

    if final_parsed.netloc == "jobs.esa.int" and "/search/" not in final_parsed.path:
        return ResolvedSite("html_links", _esa_search_url(final_parsed), ["resolved ESA redirect to search results"])
    if final_parsed.netloc == "careers.cern":
        return ResolvedSite("html_links", "https://careers.cern/jobs/", ["resolved redirect to CERN jobs board"])
    if "lufthansagroup.careers" in final_lowered:
        return ResolvedSite("lufthansa", final_url, ["resolved landing page to Lufthansa Group board"])
    if "successfactors" in final_lowered:
        return ResolvedSite("successfactors", final_url, ["resolved landing page to SuccessFactors board"])

    soup = BeautifulSoup(response.text, "html.parser")
    anchors = [absolute_url(final_url, anchor.get("href", "")) for anchor in soup.select("a[href]")]
    anchors = [anchor for anchor in anchors if anchor]
    forms = soup.find_all("form")

    for form in forms:
        action = form.get("action", "").strip()
        if not action:
            continue
        absolute_action = absolute_url(final_url, action)
        lowered_action = absolute_action.casefold()
        if "/search/" in lowered_action:
            if "createNewAlert=false" not in absolute_action:
                separator = "&" if "?" in absolute_action else "?"
                absolute_action = f"{absolute_action}{separator}createNewAlert=false&q=&locationsearch="
            return ResolvedSite("html_links", absolute_action, ["resolved landing page via public search form"])

    for anchor in anchors:
        lowered_anchor = anchor.casefold()
        if "onlyfy.jobs" in lowered_anchor:
            return ResolvedSite("onlyfy", anchor, ["resolved landing page to onlyfy board"])
        if "myworkdayjobs.com" in lowered_anchor:
            return ResolvedSite("workday", anchor, ["resolved landing page to Workday board"])
        if "career-ohb.csod.com" in lowered_anchor:
            return ResolvedSite("browser_links", anchor, ["resolved landing page to CSOD board"])
        if "lufthansagroup.careers" in lowered_anchor:
            return ResolvedSite("lufthansa", anchor, ["resolved landing page to Lufthansa Group board"])
        if "apply.lufthansagroup.careers" in lowered_anchor:
            return ResolvedSite("lufthansa", anchor, ["resolved landing page to Lufthansa application board"])
        if "successfactors" in lowered_anchor:
            return ResolvedSite("successfactors", anchor, ["resolved landing page to SuccessFactors board"])
        if "jobs.esa.int" in lowered_anchor or "careers.beyondgravity.com" in lowered_anchor:
            return ResolvedSite("browser_links", anchor, ["resolved landing page to dynamic board"])
        if "/career/job-opportunities" in lowered_anchor:
            return ResolvedSite("html_links", anchor, ["resolved landing page to static jobs page"])
        if lowered_anchor.rstrip("/") == "https://careers.cern":
            return ResolvedSite("html_links", "https://careers.cern/jobs/", ["resolved landing page to CERN jobs board"])
        if "careers.cern/jobs" in lowered_anchor:
            return ResolvedSite("html_links", anchor, ["resolved landing page to jobs page"])

    body = response.text.casefold()
    parsed_host = final_parsed.netloc
    if "api.csod.com" in body or "csod.context" in body:
        return ResolvedSite("browser_links", final_url, ["found CSOD markers in page source"])
    if "career opportunities: sign in" in body or "loginflowrequired" in body or "successfactors" in body:
        return ResolvedSite("successfactors", final_url, ["found SuccessFactors markers in page source"])
    if "jobs.esa.int" in parsed_host:
        return ResolvedSite("browser_links", final_url, ["found ESA dynamic board markers"])
    if parsed_host == "careers.cern" or "careers.cern/jobs/" in final_url:
        return ResolvedSite("html_links", "https://careers.cern/jobs/", ["using HTML links for CERN jobs page"])
    if "saab.com" in parsed_host or "beyondgravity.com" in parsed_host or "pilatus-aircraft.com" in parsed_host:
        return ResolvedSite("html_links", final_url, ["using HTML links as generic fallback"])
    return ResolvedSite("html_links", final_url, ["generic HTML fallback"])
