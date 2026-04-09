from __future__ import annotations

import json
from urllib.parse import quote

from ..utils import normalize_text, unique_preserve
from .base import AdapterContext, posting


class LufthansaAdapter:
    name = "lufthansa"
    api_base = "https://api-apply.lufthansagroup.careers/search/?data="
    page_size = 100

    def _build_payload(self, first_item: int) -> dict:
        return {
            "SearchParameters": {
                "FirstItem": first_item,
                "CountItem": self.page_size,
                "Sort": [{"Criterion": "PublicationStartDate", "Direction": "DESC"}],
                "MatchedObjectDescriptor": [
                    "ID",
                    "PositionTitle",
                    "PositionURI",
                    "PositionLocation.CountryName",
                    "PositionLocation.CityName",
                    "PublicationStartDate",
                    "ParentOrganizationName",
                    "OrganizationShortName",
                    "JobCategory.Name",
                ],
            },
            "SearchCriteria": [{"CriterionName": "PublicationChannel.Code", "CriterionValue": "12"}],
            "LanguageCode": "EN",
        }

    def _matches_site_scope(self, context: AdapterContext, descriptor: dict) -> bool:
        scope_hint = normalize_text(f"{context.site.label} {context.site.source_url}")
        if "lufthansa technik" not in scope_hint and "technik" not in scope_hint:
            return True
        parent_name = normalize_text(descriptor.get("ParentOrganizationName", ""))
        org_short_name = normalize_text(descriptor.get("OrganizationShortName", ""))
        return "lufthansa technik" in parent_name or "lufthansa technik" in org_short_name

    def scrape(self, context: AdapterContext):
        jobs = []
        seen_ids: set[str] = set()
        first_item = 1
        total = None

        while total is None or first_item <= total:
            payload = self._build_payload(first_item)
            encoded_payload = quote(json.dumps(payload, separators=(",", ":")))
            response = context.session.get(f"{self.api_base}{encoded_payload}", timeout=context.timeout_seconds)
            response.raise_for_status()
            data = response.json()
            result = data.get("SearchResult", {}) or {}
            total = int(result.get("SearchResultCountAll", result.get("SearchResultCount", 0)) or 0)
            items = result.get("SearchResultItems", []) or []
            if not items:
                break

            for item in items:
                descriptor = item.get("MatchedObjectDescriptor", {}) or {}
                if not self._matches_site_scope(context, descriptor):
                    continue
                job_id = str(descriptor.get("ID") or item.get("MatchedObjectId") or "").strip()
                title = str(descriptor.get("PositionTitle") or "").strip()
                url = str(descriptor.get("PositionURI") or "").strip()
                if not job_id or not title or not url or job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                locations = descriptor.get("PositionLocation", []) or []
                location_bits = []
                for location in locations:
                    city = str(location.get("CityName") or "").strip()
                    country = str(location.get("CountryName") or "").strip()
                    location_bits.append(", ".join(bit for bit in [city, country] if bit))
                categories = descriptor.get("JobCategory", []) or []
                category_names = unique_preserve(str(item.get("Name") or "").strip() for item in categories)
                summary_bits = []
                if descriptor.get("ParentOrganizationName"):
                    summary_bits.append(str(descriptor["ParentOrganizationName"]).strip())
                if category_names:
                    summary_bits.append(f"Categories: {', '.join(category_names)}")

                jobs.append(
                    posting(
                        site_id=context.site.id,
                        adapter_name=self.name,
                        source_url=context.source_url,
                        job_id=job_id,
                        title=title,
                        url=url,
                        location="; ".join(unique_preserve(location_bits)),
                        posted_text=str(descriptor.get("PublicationStartDate") or ""),
                        summary_text=" | ".join(summary_bits),
                    )
                )

            first_item += len(items)
            if len(items) < self.page_size:
                break

        if not jobs:
            raise RuntimeError("No public Lufthansa Technik jobs were returned by the Lufthansa Group API.")
        return jobs
