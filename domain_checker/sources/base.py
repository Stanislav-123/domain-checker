"""Base domain source interface."""

from abc import ABC, abstractmethod
from typing import List


class DomainSource(ABC):
    """Abstract base class for domain sources."""
    
    @abstractmethod
    async def fetch_domains(self) -> List[str]:
        """Fetch list of domains from the source.
        
        Returns:
            List of domain names (without protocol).
        
        Raises:
            Exception: If fetching fails.
        """
        pass
