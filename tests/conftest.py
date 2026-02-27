"""Pytest configuration and fixtures for gap-mcp tests."""

import shutil
import pytest
from gap_mcp.gap_runner import find_gap_executable


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: mark test as requiring a real GAP installation",
    )


@pytest.fixture(scope="session")
def gap_available() -> bool:
    """Return True if GAP is installed and reachable."""
    try:
        find_gap_executable()
        return True
    except FileNotFoundError:
        return False


@pytest.fixture(scope="session")
def runner(gap_available):
    """Provide a shared GAPRunner for integration tests."""
    if not gap_available:
        pytest.skip("GAP not installed — skipping integration tests")
    from gap_mcp.gap_runner import GAPRunner
    r = GAPRunner()
    yield r
    r.close()


@pytest.fixture(autouse=True)
def reset_gap_between_tests(gap_available, request):
    """Reset the shared GAP runner before each integration test.

    This prevents leaked variable state (G, H, p, …) from one test
    contaminating the next.  Only runs when GAP is available and the
    test is in a class that uses the gap_available fixture.
    """
    if not gap_available:
        return
    # Only reset for integration tests (those that receive gap_available)
    if "gap_available" not in request.fixturenames:
        return
    from gap_mcp.gap_runner import get_runner
    get_runner().reset()
