"""Custom API integration."""

import httpx

from .base import DomainSource, with_retry


class CustomSource(DomainSource):
    """Custom API domain source.

    Supports flexible custom API endpoints with configurable:
    - Header name and authentication
    - Response format (JSON list, nested JSON, or plain text)
    """

    def __init__(
        self,
        url: str,
        api_key: str,
        header_name: str = "Authorization",
        domains_path: str = "domains",
        timeout: int = 10,
    ):
        """Initialize custom source.

        Args:
            url: Custom API endpoint URL
            api_key: API key value
            header_name: Header name for API key (default: Authorization)
            domains_path: JSON path to domains (e.g. 'domains' or 'data.domains')
            timeout: Request timeout in seconds
        """
        self.url = url
        self.api_key = api_key
        self.header_name = header_name
        self.domains_path = domains_path
        self.timeout = timeout

    @with_retry(max_attempts=3)
    async def fetch_domains(self) -> list[str]:
        """Fetch domains from custom API with automatic retry.

        Supports:
        1. JSON list: ["domain1.com", "domain2.com"]
        2. JSON object with domains field: {"domains": [...]}
        3. Nested JSON path: {"data": {"domains": [...]}}
        4. Plain text: one domain per line

        Retries up to 3 times with exponential backoff on network errors.
        """
        headers = {
            self.header_name: (
                f"Bearer {self.api_key}"
                if self.header_name.lower() == "authorization"
                and not self.api_key.lower().startswith(("bearer ", "basic ", "token "))
                else self.api_key
            ),
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(self.url, headers=headers)
            response.raise_for_status()

            response.headers.get("content-type", "")

            try:
                data = response.json()
                is_json = isinstance(data, (list, dict))
            except ValueError:
                is_json = False
            if is_json:
                domains = self._parse_json(data)
            else:
                domains = self._parse_text(response.text)

            return [self._clean_domain(d) for d in domains if d]

    def _parse_json(self, data) -> list[str]:
        """Parse JSON response based on configured domains path."""
        if isinstance(data, list):
            return self._extract_domains_from_list(data)

        if isinstance(data, dict):
            path_parts = self.domains_path.split(".")
            current = data

            for part in path_parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    break

            if isinstance(current, list):
                return self._extract_domains_from_list(current)
            elif isinstance(current, str):
                return [current]

        return []

    def _extract_domains_from_list(self, items: list) -> list[str]:
        """Extract domain strings from a list of items."""
        domains = []
        for item in items:
            if isinstance(item, str):
                domains.append(item)
            elif isinstance(item, dict):
                domain = item.get("domain") or item.get("name") or item.get("url", "")
                if domain:
                    domains.append(domain)
        return domains

    def _parse_text(self, text: str) -> list[str]:
        """Parse plain text response (one domain per line)."""
        lines = text.replace(",", "\n").split("\n")
        return [
            line.strip()
            for line in lines
            if line.strip() and not line.strip().startswith("#")
        ]

    def _clean_domain(self, domain: str) -> str:
        """Clean domain name (remove protocol, trailing slash)."""
        domain = domain.strip().replace("https://", "").replace("http://", "")
        domain = domain.split("/")[0].split("?")[0]
        return domain.strip().lower().rstrip(".")
