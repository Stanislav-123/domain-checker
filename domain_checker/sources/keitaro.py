"""Keitaro tracker integration."""

import httpx
from typing import List
from .base import DomainSource


class KeitaroSource(DomainSource):
    """Keitaro tracker domain source.
    
    Uses Keitaro Admin API to fetch domains.
    API documentation: https://admin-api.docs.keitaro.io/
    """
    
    def __init__(self, base_url: str, api_key: str, timeout: int = 10):
        """Initialize Keitaro source.
        
        Args:
            base_url: Keitaro tracker base URL (e.g. https://tracker.example.com)
            api_key: Keitaro API key
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
    
    async def fetch_domains(self) -> List[str]:
        """Fetch domains from Keitaro.
        
        Keitaro Admin API endpoint: GET /admin_api/v1/domains
        Returns list of domain objects with 'name' field.
        """
        url = f"{self.base_url}/admin_api/v1/domains"
        headers = {
            "Api-Key": self.api_key,
            "Accept": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            
            if isinstance(data, list):
                domains = [item.get('name') or item.get('domain', '') for item in data]
            elif isinstance(data, dict) and 'domains' in data:
                domains = [item.get('name') or item.get('domain', '') for item in data['domains']]
            else:
                domains = []
            
            return [self._clean_domain(d) for d in domains if d]
    
    def _clean_domain(self, domain: str) -> str:
        """Clean domain name (remove protocol, trailing slash)."""
        domain = domain.strip().replace('https://', '').replace('http://', '')
        domain = domain.split('/')[0].split('?')[0]
        return domain.strip().lower().rstrip('.')
