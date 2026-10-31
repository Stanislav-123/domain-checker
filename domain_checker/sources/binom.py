"""Binom tracker integration."""

import httpx
from typing import List
from .base import DomainSource


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
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
    
    async def fetch_domains(self) -> List[str]:
        """Fetch domains from Binom.
        
        Binom API endpoint: GET /api.php?page=Domains&api_key=KEY
        Returns domains in various possible formats.
        """
        url = f"{self.base_url}/api.php"
        params = {
            "page": "Domains",
            "api_key": self.api_key
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            domains = []
            
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, str):
                        domains.append(item)
                    elif isinstance(item, dict):
                        domain = item.get('domain') or item.get('name') or item.get('url', '')
                        if domain:
                            domains.append(domain)
            elif isinstance(data, dict):
                if 'domains' in data:
                    domains_data = data['domains']
                    if isinstance(domains_data, list):
                        for item in domains_data:
                            if isinstance(item, str):
                                domains.append(item)
                            elif isinstance(item, dict):
                                domain = item.get('domain') or item.get('name') or item.get('url', '')
                                if domain:
                                    domains.append(domain)
                elif 'data' in data and isinstance(data['data'], list):
                    for item in data['data']:
                        if isinstance(item, str):
                            domains.append(item)
                        elif isinstance(item, dict):
                            domain = item.get('domain') or item.get('name') or item.get('url', '')
                            if domain:
                                domains.append(domain)
            
            return [self._clean_domain(d) for d in domains if d]
    
    def _clean_domain(self, domain: str) -> str:
        """Clean domain name (remove protocol, trailing slash)."""
        domain = domain.replace('https://', '').replace('http://', '')
        domain = domain.split('/')[0]
        return domain.strip()
