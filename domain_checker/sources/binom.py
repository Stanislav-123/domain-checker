"""Binom tracker integration."""

import httpx

from .base import DomainSource, with_retry


class BinomSource(DomainSource):
    """Binom tracker domain source.

    Uses Binom API to fetch domains.
    API documentation: https://docs.binom.org/api.php
    """

    def __init__(self, base_url: str, api_key: str, timeout: int = 10):
        """Initialize Binom source.

        Args:
            base_url: Binom tracker base URL (e.g. https://tracker.example.com)
            api_key: Binom API key
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    # Binom v2 (current) passes the key in the "api-key" header; exact paths
    # differ between builds, so we try the known ones and finally fall back to
    # the legacy v1 query-string API.
    V2_PATHS = ("/public/api/v1/domain/list/all", "/api/v2/domain")

    @with_retry(max_attempts=3)
    async def fetch_domains(self) -> list[str]:
        """Fetch domains from Binom (v2 first, then legacy v1) with automatic retry.

        Tries multiple endpoints in order:
        1. /public/api/v1/domain/list/all (v2 with api-key header)
        2. /api/v2/domain (v2 with api-key header)
        3. /api.php?page=Domains&api_key=KEY (legacy v1)

        Retries up to 3 times with exponential backoff on network errors.
        """
        errors = []
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            attempts = [
                (
                    f"{self.base_url}{path}",
                    {"api-key": self.api_key, "Accept": "application/json"},
                    None,
                )
                for path in self.V2_PATHS
            ]
            attempts.append(
                (
                    f"{self.base_url}/api.php",
                    {"Accept": "application/json"},
                    {"page": "Domains", "api_key": self.api_key},
                )
            )
            for url, headers, params in attempts:
                try:
                    response = await client.get(url, headers=headers, params=params)
                    response.raise_for_status()
                    data = response.json()
                except Exception as e:
                    errors.append(f"{url}: {e}")
                    continue
                domains = self._extract(data)
                if domains is not None:
                    return [self._clean_domain(d) for d in domains if d]
                errors.append(f"{url}: unexpected response format")
        raise RuntimeError(
            "Binom API: no endpoint returned a domain list; " + "; ".join(errors)
        )

    def _extract(self, data):
        items = None
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            for key in ("domains", "data", "items", "list"):
                if isinstance(data.get(key), list):
                    items = data[key]
                    break
        if items is None:
            return None
        out = []
        for item in items:
            if isinstance(item, str):
                out.append(item)
            elif isinstance(item, dict):
                d = item.get("domain") or item.get("name") or item.get("url") or ""
                if d:
                    out.append(d)
        return out

    def _clean_domain(self, domain: str) -> str:
        """Clean domain name (remove protocol, trailing slash)."""
        domain = domain.strip().replace("https://", "").replace("http://", "")
        domain = domain.split("/")[0].split("?")[0]
        return domain.strip().lower().rstrip(".")
