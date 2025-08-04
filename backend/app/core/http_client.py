"""
Centralized HTTP client with comprehensive timeout and retry configurations.
Provides a consistent interface for all external API calls with proper error handling.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, Union
from enum import Enum
import httpx
import aiohttp
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_log,
    after_log
)

logger = logging.getLogger(__name__)


class TimeoutProfile(Enum):
    """Predefined timeout profiles for different types of API calls."""
    
    # Quick lookups (e.g., simple REST calls)
    QUICK = (5.0, 10.0)  # (connect_timeout, read_timeout)
    
    # Standard API calls (most common)
    STANDARD = (10.0, 30.0)
    
    # Extended for complex operations (e.g., AI/ML services)
    EXTENDED = (20.0, 60.0)
    
    # Long-running operations (e.g., file uploads, batch processing)
    LONG = (30.0, 120.0)


class HTTPClientError(Exception):
    """Base exception for HTTP client errors."""
    pass


class TimeoutError(HTTPClientError):
    """Raised when a request times out."""
    pass


class RetryExhaustedError(HTTPClientError):
    """Raised when all retry attempts are exhausted."""
    pass


class BaseHTTPClient:
    """Base HTTP client with timeout and retry configuration."""
    
    def __init__(
        self,
        timeout_profile: TimeoutProfile = TimeoutProfile.STANDARD,
        max_retries: int = 3,
        backoff_factor: float = 0.3,
        status_forcelist: Optional[list] = None
    ):
        self.timeout_profile = timeout_profile
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.status_forcelist = status_forcelist or [500, 502, 503, 504]
        
    def get_timeout(self) -> Union[float, tuple]:
        """Get timeout configuration based on profile."""
        return self.timeout_profile.value


class AsyncHTTPClient(BaseHTTPClient):
    """Async HTTP client using httpx with comprehensive error handling."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._client: Optional[httpx.AsyncClient] = None
        
    async def __aenter__(self):
        """Context manager entry."""
        await self.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()
        
    async def start(self):
        """Initialize the HTTP client."""
        if not self._client:
            connect_timeout, read_timeout = self.get_timeout()
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(
                    connect=connect_timeout,
                    read=read_timeout,
                    write=None,
                    pool=None
                ),
                limits=httpx.Limits(
                    max_keepalive_connections=5,
                    max_connections=10,
                    keepalive_expiry=5.0
                ),
                follow_redirects=True
            )
            
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
            
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        before=before_log(logger, logging.WARNING),
        after=after_log(logger, logging.WARNING)
    )
    async def request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> httpx.Response:
        """
        Make an HTTP request with automatic retries and timeout handling.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            **kwargs: Additional arguments passed to httpx
            
        Returns:
            httpx.Response object
            
        Raises:
            TimeoutError: If request times out after retries
            HTTPClientError: For other HTTP errors
        """
        if not self._client:
            await self.start()
            
        try:
            response = await self._client.request(method, url, **kwargs)
            response.raise_for_status()
            return response
            
        except httpx.TimeoutException as e:
            logger.error(f"Request timeout for {method} {url}: {str(e)}")
            raise TimeoutError(f"Request timed out: {str(e)}") from e
            
        except httpx.HTTPStatusError as e:
            # Don't retry on 4xx errors
            if 400 <= e.response.status_code < 500:
                logger.warning(f"Client error for {method} {url}: {e.response.status_code}")
                raise
            logger.error(f"Server error for {method} {url}: {e.response.status_code}")
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error for {method} {url}: {str(e)}")
            raise HTTPClientError(f"HTTP request failed: {str(e)}") from e
            
    async def get(self, url: str, **kwargs) -> httpx.Response:
        """Make a GET request."""
        return await self.request("GET", url, **kwargs)
        
    async def post(self, url: str, **kwargs) -> httpx.Response:
        """Make a POST request."""
        return await self.request("POST", url, **kwargs)
        
    async def put(self, url: str, **kwargs) -> httpx.Response:
        """Make a PUT request."""
        return await self.request("PUT", url, **kwargs)
        
    async def delete(self, url: str, **kwargs) -> httpx.Response:
        """Make a DELETE request."""
        return await self.request("DELETE", url, **kwargs)
        
    async def patch(self, url: str, **kwargs) -> httpx.Response:
        """Make a PATCH request."""
        return await self.request("PATCH", url, **kwargs)


class AioHTTPClient(BaseHTTPClient):
    """Async HTTP client using aiohttp with comprehensive error handling."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """Context manager entry."""
        await self.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()
        
    async def start(self):
        """Initialize the HTTP session."""
        if not self._session:
            connect_timeout, read_timeout = self.get_timeout()
            timeout = aiohttp.ClientTimeout(
                total=connect_timeout + read_timeout,
                connect=connect_timeout,
                sock_connect=connect_timeout,
                sock_read=read_timeout
            )
            
            connector = aiohttp.TCPConnector(
                limit=10,
                limit_per_host=5,
                ttl_dns_cache=300
            )
            
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector
            )
            
    async def close(self):
        """Close the HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
            
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((asyncio.TimeoutError, aiohttp.ClientError)),
        before=before_log(logger, logging.WARNING),
        after=after_log(logger, logging.WARNING)
    )
    async def request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> aiohttp.ClientResponse:
        """
        Make an HTTP request with automatic retries and timeout handling.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            **kwargs: Additional arguments passed to aiohttp
            
        Returns:
            aiohttp.ClientResponse object
            
        Raises:
            TimeoutError: If request times out after retries
            HTTPClientError: For other HTTP errors
        """
        if not self._session:
            await self.start()
            
        try:
            async with self._session.request(method, url, **kwargs) as response:
                # Read the response body to avoid connection issues
                await response.read()
                
                if response.status >= 400:
                    # Don't retry on 4xx errors
                    if 400 <= response.status < 500:
                        logger.warning(f"Client error for {method} {url}: {response.status}")
                        response.raise_for_status()
                    else:
                        logger.error(f"Server error for {method} {url}: {response.status}")
                        response.raise_for_status()
                        
                return response
                
        except asyncio.TimeoutError as e:
            logger.error(f"Request timeout for {method} {url}: {str(e)}")
            raise TimeoutError(f"Request timed out: {str(e)}") from e
            
        except aiohttp.ClientError as e:
            logger.error(f"Client error for {method} {url}: {str(e)}")
            raise HTTPClientError(f"HTTP request failed: {str(e)}") from e
            
        except Exception as e:
            logger.error(f"Unexpected error for {method} {url}: {str(e)}")
            raise HTTPClientError(f"HTTP request failed: {str(e)}") from e
            
    async def get(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make a GET request."""
        return await self.request("GET", url, **kwargs)
        
    async def post(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make a POST request."""
        return await self.request("POST", url, **kwargs)
        
    async def put(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make a PUT request."""
        return await self.request("PUT", url, **kwargs)
        
    async def delete(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make a DELETE request."""
        return await self.request("DELETE", url, **kwargs)
        
    async def patch(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make a PATCH request."""
        return await self.request("PATCH", url, **kwargs)


class SyncHTTPClient(BaseHTTPClient):
    """Synchronous HTTP client using requests with retry adapter."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._session: Optional[requests.Session] = None
        
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        
    def start(self):
        """Initialize the HTTP session with retry configuration."""
        if not self._session:
            self._session = requests.Session()
            
            # Configure retry adapter
            retry_strategy = Retry(
                total=self.max_retries,
                backoff_factor=self.backoff_factor,
                status_forcelist=self.status_forcelist,
                allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST", "PATCH"]
            )
            
            adapter = HTTPAdapter(max_retries=retry_strategy)
            self._session.mount("http://", adapter)
            self._session.mount("https://", adapter)
            
    def close(self):
        """Close the HTTP session."""
        if self._session:
            self._session.close()
            self._session = None
            
    def request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> requests.Response:
        """
        Make an HTTP request with automatic retries and timeout handling.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            **kwargs: Additional arguments passed to requests
            
        Returns:
            requests.Response object
            
        Raises:
            TimeoutError: If request times out
            HTTPClientError: For other HTTP errors
        """
        if not self._session:
            self.start()
            
        # Set timeout if not provided
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.get_timeout()
            
        try:
            response = self._session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
            
        except requests.Timeout as e:
            logger.error(f"Request timeout for {method} {url}: {str(e)}")
            raise TimeoutError(f"Request timed out: {str(e)}") from e
            
        except requests.HTTPError as e:
            # Don't retry on 4xx errors
            if e.response and 400 <= e.response.status_code < 500:
                logger.warning(f"Client error for {method} {url}: {e.response.status_code}")
                raise
            logger.error(f"Server error for {method} {url}: {e.response.status_code if e.response else 'Unknown'}")
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error for {method} {url}: {str(e)}")
            raise HTTPClientError(f"HTTP request failed: {str(e)}") from e
            
    def get(self, url: str, **kwargs) -> requests.Response:
        """Make a GET request."""
        return self.request("GET", url, **kwargs)
        
    def post(self, url: str, **kwargs) -> requests.Response:
        """Make a POST request."""
        return self.request("POST", url, **kwargs)
        
    def put(self, url: str, **kwargs) -> requests.Response:
        """Make a PUT request."""
        return self.request("PUT", url, **kwargs)
        
    def delete(self, url: str, **kwargs) -> requests.Response:
        """Make a DELETE request."""
        return self.request("DELETE", url, **kwargs)
        
    def patch(self, url: str, **kwargs) -> requests.Response:
        """Make a PATCH request."""
        return self.request("PATCH", url, **kwargs)


# Factory functions for easy client creation
def create_async_client(
    timeout_profile: TimeoutProfile = TimeoutProfile.STANDARD,
    **kwargs
) -> AsyncHTTPClient:
    """Create an async HTTP client with the specified timeout profile."""
    return AsyncHTTPClient(timeout_profile=timeout_profile, **kwargs)


def create_aiohttp_client(
    timeout_profile: TimeoutProfile = TimeoutProfile.STANDARD,
    **kwargs
) -> AioHTTPClient:
    """Create an aiohttp client with the specified timeout profile."""
    return AioHTTPClient(timeout_profile=timeout_profile, **kwargs)


def create_sync_client(
    timeout_profile: TimeoutProfile = TimeoutProfile.STANDARD,
    **kwargs
) -> SyncHTTPClient:
    """Create a synchronous HTTP client with the specified timeout profile."""
    return SyncHTTPClient(timeout_profile=timeout_profile, **kwargs)