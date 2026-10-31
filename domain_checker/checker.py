"""Domain health checker."""

import asyncio
import socket
import ssl
import httpx
from datetime import datetime, timedelta, timezone
from typing import Dict, List
from cryptography import x509
from cryptography.hazmat.backends import default_backend


# Codes that mean "the server is alive but refuses us" (auth walls, anti-bot,
# rate limits). Treating them as DOWN produces false alarms.
REACHABLE_CODES = {401, 403, 429}


class DomainChecker:
    """Performs health checks on domains."""
    
    def __init__(
        self,
        timeout: int = 10,
        max_concurrent: int = 10
    ):
        """Initialize domain checker.
        
        Args:
            timeout: Request timeout in seconds
            max_concurrent: Maximum concurrent checks
        """
        self.timeout = timeout
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def check_domain(self, domain: str) -> Dict:
        """Perform comprehensive health check on a domain.
        
        Args:
            domain: Domain name to check
            
        Returns:
            Dictionary with check results including:
            - status: 'up' or 'down'
            - dns_resolved: bool
            - http_code: int or None
            - response_time_ms: int or None
            - ssl_valid: bool or None
            - ssl_days_remaining: int or None
            - error_message: str or None
        """
        async with self.semaphore:
            result = {
                'domain': domain,
                'status': 'unknown',
                'dns_resolved': False,
                'http_code': None,
                'response_time_ms': None,
                'ssl_valid': None,
                'ssl_days_remaining': None,
                'error_message': None,
                'checked_at': datetime.now(timezone.utc).isoformat()
            }
            
            try:
                dns_ok = await self._check_dns(domain)
                result['dns_resolved'] = dns_ok
                
                if not dns_ok:
                    result['status'] = 'down'
                    result['error_message'] = 'DNS resolution failed'
                    return result
                
                http_result = await self._check_http(domain)
                result.update(http_result)
                
                ssl_result = await self._check_ssl(domain)
                result.update(ssl_result)
                
                code = result['http_code']
                if code and (200 <= code < 400 or code in REACHABLE_CODES):
                    result['status'] = 'up'
                else:
                    result['status'] = 'down'
                    if code and not result.get('error_message'):
                        result['error_message'] = f'HTTP {code}'

                # A reachable site with a broken/expired certificate is broken for users.
                if result['status'] == 'up' and result.get('ssl_valid') is False:
                    result['status'] = 'down'
                    result['error_message'] = result.get('ssl_error') or 'SSL certificate invalid'
                
            except Exception as e:
                result['status'] = 'down'
                result['error_message'] = str(e)
            
            return result
    
    async def _check_dns(self, domain: str) -> bool:
        """Check if domain DNS resolves.
        
        Args:
            domain: Domain name
            
        Returns:
            True if DNS resolves successfully
        """
        try:
            loop = asyncio.get_running_loop()
            await loop.getaddrinfo(domain, None)
            return True
        except (socket.gaierror, OSError):
            return False
    
    async def _check_http(self, domain: str) -> Dict:
        """Check HTTP/HTTPS availability.
        
        Args:
            domain: Domain name
            
        Returns:
            Dictionary with http_code, response_time_ms, error_message
        """
        result = {
            'http_code': None,
            'response_time_ms': None,
            'error_message': None
        }
        
        for protocol in ['https', 'http']:
            try:
                url = f"{protocol}://{domain}"
                start_time = datetime.now(timezone.utc)
                
                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    follow_redirects=True,
                    verify=False
                ) as client:
                    response = await client.get(url)
                    
                    end_time = datetime.now(timezone.utc)
                    response_time = (end_time - start_time).total_seconds() * 1000
                    
                    result['http_code'] = response.status_code
                    result['response_time_ms'] = int(response_time)
                    result['error_message'] = None
                    return result
                    
            except httpx.TimeoutException:
                result['error_message'] = f'{protocol.upper()} timeout'
            except httpx.ConnectError:
                result['error_message'] = f'{protocol.upper()} connection failed'
            except Exception as e:
                result['error_message'] = f'{protocol.upper()} error: {str(e)}'
        
        return result
    
    async def _check_ssl(self, domain: str) -> Dict:
        """Check SSL certificate validity and expiration.
        
        Args:
            domain: Domain name
            
        Returns:
            Dictionary with ssl_valid and ssl_days_remaining
        """
        result = {
            'ssl_valid': None,
            'ssl_days_remaining': None,
            'ssl_error': None
        }

        # 1) Verified handshake: catches expired, self-signed, wrong-host certs.
        try:
            vctx = ssl.create_default_context()
            _, vwriter = await asyncio.wait_for(
                asyncio.open_connection(domain, 443, ssl=vctx, server_hostname=domain),
                timeout=self.timeout
            )
            vwriter.close()
            try:
                await vwriter.wait_closed()
            except Exception:
                pass
            verify_error = None
        except ssl.SSLCertVerificationError as e:
            verify_error = f'SSL: {e.verify_message or e.reason}'
        except Exception:
            verify_error = 'no-https'

        if verify_error == 'no-https':
            return result  # no HTTPS on this domain; nothing to judge

        # 2) Unverified handshake just to read the expiry date.
        try:
            
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(domain, 443, ssl=context),
                timeout=self.timeout
            )
            
            ssl_object = writer.get_extra_info('ssl_object')
            if ssl_object:
                cert_der = ssl_object.getpeercert(binary_form=True)
                cert = x509.load_der_x509_certificate(cert_der, default_backend())
                
                now = datetime.now(timezone.utc)
                not_after = cert.not_valid_after_utc if hasattr(cert, 'not_valid_after_utc') else cert.not_valid_after
                
                if now < not_after:
                    result['ssl_valid'] = True
                    days_remaining = (not_after - now).days
                    result['ssl_days_remaining'] = days_remaining
                else:
                    result['ssl_valid'] = False
                    result['ssl_days_remaining'] = 0
            
            writer.close()
            await writer.wait_closed()

        except asyncio.TimeoutError:
            pass
        except Exception:
            pass
        
        if verify_error:
            result['ssl_valid'] = False
            result['ssl_error'] = verify_error
        return result
    
    async def check_multiple_domains(self, domains: List[str]) -> List[Dict]:
        """Check multiple domains concurrently.
        
        Args:
            domains: List of domain names
            
        Returns:
            List of check result dictionaries
        """
        tasks = [self.check_domain(domain) for domain in domains]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append({
                    'domain': domains[i],
                    'status': 'down',
                    'error_message': str(result)
                })
            else:
                final_results.append(result)
        
        return final_results
