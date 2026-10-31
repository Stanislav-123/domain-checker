"""Base domain source interface."""

from abc import ABC, abstractmethod

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


class DomainSource(ABC):
    """Abstract base class for domain sources."""

    @abstractmethod
    async def fetch_domains(self) -> list[str]:
        """Fetch list of domains from the source.

        Returns:
            List of domain names (without protocol).

        Raises:
            Exception: If fetching fails.
        """
        pass


def with_retry(max_attempts: int = 3):
    """Decorator to add retry logic to fetch operations.

    Args:
        max_attempts: Maximum number of retry attempts

    Returns:
        Retry decorator configured for network operations
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(
            (
                httpx.TimeoutException,
                httpx.ConnectError,
                httpx.NetworkError,
            )
        ),
        reraise=True,
    )
