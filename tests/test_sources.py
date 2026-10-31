"""Tests for domain sources."""

import pytest
import respx
import httpx
from domain_checker.sources import KeitaroSource, BinomSource, CustomSource


@pytest.mark.asyncio
@respx.mock
async def test_keitaro_source_list_format():
    """Test Keitaro source with list format response."""
    url = "https://tracker.example.com"
    api_key = "test-key"
    
    respx.get(f"{url}/admin_api/v1/domains").mock(return_value=httpx.Response(
        200,
        json=[
            {"name": "domain1.com", "id": 1},
            {"name": "domain2.com", "id": 2}
        ]
    ))
    
    source = KeitaroSource(url, api_key)
    domains = await source.fetch_domains()
    
    assert domains == ["domain1.com", "domain2.com"]


@pytest.mark.asyncio
@respx.mock
async def test_keitaro_source_with_protocol():
    """Test Keitaro source cleans protocols."""
    url = "https://tracker.example.com"
    api_key = "test-key"
    
    respx.get(f"{url}/admin_api/v1/domains").mock(return_value=httpx.Response(
        200,
        json=[
            {"name": "https://domain1.com"},
            {"name": "http://domain2.com/path"}
        ]
    ))
    
    source = KeitaroSource(url, api_key)
    domains = await source.fetch_domains()
    
    assert domains == ["domain1.com", "domain2.com"]


@pytest.mark.asyncio
@respx.mock
async def test_binom_source_list_format():
    """Test Binom source with list format."""
    url = "https://tracker.example.com"
    api_key = "test-key"
    
    respx.get(f"{url}/api.php").mock(return_value=httpx.Response(
        200,
        json=[
            {"domain": "domain1.com"},
            {"domain": "domain2.com"}
        ]
    ))
    
    source = BinomSource(url, api_key)
    domains = await source.fetch_domains()
    
    assert domains == ["domain1.com", "domain2.com"]


@pytest.mark.asyncio
@respx.mock
async def test_binom_source_nested_format():
    """Test Binom source with nested domains format."""
    url = "https://tracker.example.com"
    api_key = "test-key"
    
    respx.get(f"{url}/api.php").mock(return_value=httpx.Response(
        200,
        json={
            "domains": [
                {"name": "domain1.com"},
                {"name": "domain2.com"}
            ]
        }
    ))
    
    source = BinomSource(url, api_key)
    domains = await source.fetch_domains()
    
    assert domains == ["domain1.com", "domain2.com"]


@pytest.mark.asyncio
@respx.mock
async def test_custom_source_json_list():
    """Test custom source with JSON list."""
    url = "https://api.example.com/domains"
    api_key = "test-key"
    
    respx.get(url).mock(return_value=httpx.Response(
        200,
        json=["domain1.com", "domain2.com"],
        headers={"content-type": "application/json"}
    ))
    
    source = CustomSource(url, api_key)
    domains = await source.fetch_domains()
    
    assert domains == ["domain1.com", "domain2.com"]


@pytest.mark.asyncio
@respx.mock
async def test_custom_source_json_object():
    """Test custom source with JSON object."""
    url = "https://api.example.com/domains"
    api_key = "test-key"
    
    respx.get(url).mock(return_value=httpx.Response(
        200,
        json={
            "domains": ["domain1.com", "domain2.com"]
        },
        headers={"content-type": "application/json"}
    ))
    
    source = CustomSource(url, api_key, domains_path="domains")
    domains = await source.fetch_domains()
    
    assert domains == ["domain1.com", "domain2.com"]


@pytest.mark.asyncio
@respx.mock
async def test_custom_source_nested_path():
    """Test custom source with nested JSON path."""
    url = "https://api.example.com/domains"
    api_key = "test-key"
    
    respx.get(url).mock(return_value=httpx.Response(
        200,
        json={
            "data": {
                "domains": ["domain1.com", "domain2.com"]
            }
        },
        headers={"content-type": "application/json"}
    ))
    
    source = CustomSource(url, api_key, domains_path="data.domains")
    domains = await source.fetch_domains()
    
    assert domains == ["domain1.com", "domain2.com"]


@pytest.mark.asyncio
@respx.mock
async def test_custom_source_plain_text():
    """Test custom source with plain text format."""
    url = "https://api.example.com/domains"
    api_key = "test-key"
    
    respx.get(url).mock(return_value=httpx.Response(
        200,
        text="domain1.com\ndomain2.com\ndomain3.com",
        headers={"content-type": "text/plain"}
    ))
    
    source = CustomSource(url, api_key)
    domains = await source.fetch_domains()
    
    assert domains == ["domain1.com", "domain2.com", "domain3.com"]


@pytest.mark.asyncio
@respx.mock
async def test_custom_source_custom_header():
    """Test custom source with custom header name."""
    url = "https://api.example.com/domains"
    api_key = "test-key"
    header_name = "X-API-Key"
    
    route = respx.get(url).mock(return_value=httpx.Response(
        200,
        json=["domain1.com"],
        headers={"content-type": "application/json"}
    ))
    
    source = CustomSource(url, api_key, header_name=header_name)
    domains = await source.fetch_domains()
    
    assert domains == ["domain1.com"]
    assert route.calls.last.request.headers[header_name] == api_key
