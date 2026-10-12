import pytest

from core import ratelimit


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    ratelimit.reset()
    yield
    ratelimit.reset()
