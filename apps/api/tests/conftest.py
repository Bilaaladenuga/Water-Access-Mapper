"""Test configuration — tests hit the live API server."""
import pytest
import httpx

BASE_URL = "http://localhost:8000"

@pytest.fixture
def client():
    """Create an httpx client pointing at the live server."""
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as c:
        yield c
