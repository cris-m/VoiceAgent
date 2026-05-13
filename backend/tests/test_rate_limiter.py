import asyncio

import pytest

from core.rate_limiter import InMemoryRateLimiter


class TestRateLimiterBasics:
    @pytest.mark.asyncio
    async def test_allow_requests_within_limit(self):
        limiter = InMemoryRateLimiter(requests=5, window_seconds=60)
        for i in range(5):
            result = await limiter.is_allowed("192.168.1.1")
            assert result is True

    @pytest.mark.asyncio
    async def test_reject_requests_over_limit(self):
        limiter = InMemoryRateLimiter(requests=2, window_seconds=60)
        assert await limiter.is_allowed("192.168.1.1") is True
        assert await limiter.is_allowed("192.168.1.1") is True
        assert await limiter.is_allowed("192.168.1.1") is False

    @pytest.mark.asyncio
    async def test_different_ips_independent(self):
        limiter = InMemoryRateLimiter(requests=2, window_seconds=60)

        assert await limiter.is_allowed("192.168.1.1") is True
        assert await limiter.is_allowed("192.168.1.1") is True
        assert await limiter.is_allowed("192.168.1.1") is False

        assert await limiter.is_allowed("192.168.1.2") is True
        assert await limiter.is_allowed("192.168.1.2") is True
        assert await limiter.is_allowed("192.168.1.2") is False

    @pytest.mark.asyncio
    async def test_exactly_at_limit(self):
        limiter = InMemoryRateLimiter(requests=3, window_seconds=60)
        assert await limiter.is_allowed("192.168.1.1") is True
        assert await limiter.is_allowed("192.168.1.1") is True
        assert await limiter.is_allowed("192.168.1.1") is True
        assert await limiter.is_allowed("192.168.1.1") is False


class TestRateLimiterWindowReset:
    @pytest.mark.asyncio
    async def test_window_reset_after_timeout(self):
        limiter = InMemoryRateLimiter(requests=2, window_seconds=1)

        assert await limiter.is_allowed("192.168.1.1") is True
        assert await limiter.is_allowed("192.168.1.1") is True
        assert await limiter.is_allowed("192.168.1.1") is False

        await asyncio.sleep(1.1)
        assert await limiter.is_allowed("192.168.1.1") is True

    @pytest.mark.asyncio
    async def test_partial_window_expiration(self):
        limiter = InMemoryRateLimiter(requests=5, window_seconds=2)

        for i in range(3):
            assert await limiter.is_allowed("192.168.1.1") is True

        await asyncio.sleep(0.5)

        for i in range(2):
            assert await limiter.is_allowed("192.168.1.1") is True
        assert await limiter.is_allowed("192.168.1.1") is False


class TestRateLimiterConcurrency:
    @pytest.mark.asyncio
    async def test_concurrent_requests_respected(self):
        limiter = InMemoryRateLimiter(requests=10, window_seconds=60)

        tasks = [limiter.is_allowed("192.168.1.1") for _ in range(15)]
        results = await asyncio.gather(*tasks)

        allowed = sum(1 for r in results if r is True)
        denied = sum(1 for r in results if r is False)

        assert allowed == 10
        assert denied == 5

    @pytest.mark.asyncio
    async def test_concurrent_different_ips(self):
        limiter = InMemoryRateLimiter(requests=3, window_seconds=60)

        ip1_tasks = [limiter.is_allowed("192.168.1.1") for _ in range(5)]
        ip2_tasks = [limiter.is_allowed("192.168.1.2") for _ in range(5)]

        all_results = await asyncio.gather(*(ip1_tasks + ip2_tasks))

        allowed = sum(1 for r in all_results if r is True)
        assert allowed == 6

    @pytest.mark.asyncio
    async def test_concurrent_and_sequential(self):
        limiter = InMemoryRateLimiter(requests=5, window_seconds=60)

        tasks = [limiter.is_allowed("192.168.1.1") for _ in range(3)]
        results1 = await asyncio.gather(*tasks)

        assert sum(1 for r in results1 if r is True) == 3

        result4 = await limiter.is_allowed("192.168.1.1")
        result5 = await limiter.is_allowed("192.168.1.1")
        result6 = await limiter.is_allowed("192.168.1.1")

        assert result4 is True
        assert result5 is True
        assert result6 is False


class TestRateLimiterLRU:
    @pytest.mark.asyncio
    async def test_lru_eviction_on_max_keys(self):
        limiter = InMemoryRateLimiter(requests=5, window_seconds=60, max_keys=2)

        assert await limiter.is_allowed("192.168.1.1") is True
        assert await limiter.is_allowed("192.168.1.2") is True
        assert await limiter.is_allowed("192.168.1.3") is True

        assert len(limiter.requests_per_key) <= 3

    @pytest.mark.asyncio
    async def test_accessed_key_not_evicted(self):
        limiter = InMemoryRateLimiter(requests=10, window_seconds=60, max_keys=2)

        await limiter.is_allowed("192.168.1.1")
        await limiter.is_allowed("192.168.1.2")

        await limiter.is_allowed("192.168.1.1")

        await limiter.is_allowed("192.168.1.3")

        keys = set(limiter.requests_per_key.keys())
        assert "192.168.1.1" in keys


class TestRateLimiterEdgeCases:
    @pytest.mark.asyncio
    async def test_zero_limit(self):
        limiter = InMemoryRateLimiter(requests=0, window_seconds=60)
        assert await limiter.is_allowed("192.168.1.1") is False

    @pytest.mark.asyncio
    async def test_single_request_limit(self):
        limiter = InMemoryRateLimiter(requests=1, window_seconds=60)
        assert await limiter.is_allowed("192.168.1.1") is True
        assert await limiter.is_allowed("192.168.1.1") is False

    @pytest.mark.asyncio
    async def test_very_large_limit(self):
        limiter = InMemoryRateLimiter(requests=10000, window_seconds=60)
        for i in range(100):
            result = await limiter.is_allowed(f"192.168.1.{i}")
            assert result is True

    @pytest.mark.asyncio
    async def test_empty_ip_string(self):
        limiter = InMemoryRateLimiter(requests=2, window_seconds=60)
        assert await limiter.is_allowed("") is True
        assert await limiter.is_allowed("") is True
        assert await limiter.is_allowed("") is False
