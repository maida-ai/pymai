"""Tests for composite modules implementing invisible execution patterns."""

import asyncio
import time
from typing import Any

import pytest

from mai.layers import Conditional, Delay, Module, Parallel, Retry, Sequential
from mai.types.context import Context


class SimpleModule(Module):
    """Simple test module."""

    def __init__(self, multiplier: int = 1):
        super().__init__()
        self.multiplier = multiplier

    def forward(self, x: int, *args: Any, **kwargs: Any) -> int:
        return x * self.multiplier


class AsyncModule(Module):
    """Async test module."""

    def __init__(self, delay: float = 0.01):
        super().__init__()
        self.delay = delay

    async def forward(self, x: int) -> int:
        await asyncio.sleep(self.delay)
        return x * 2


class ErrorModule(Module):
    """Module that raises an exception."""

    def forward(self, x: int) -> int:
        raise ValueError("Test error")


class AggregatorModule(Module):
    """Module that aggregates multiple inputs."""

    def forward(self, *args: Any) -> int:
        """Sum all inputs."""
        return sum(args)


class IdentityModule(Module):
    """Module that returns input unchanged."""

    def forward(self, *args: Any) -> Any:
        """Return input unchanged, handling single or multiple arguments."""
        if len(args) == 1:
            return args[0]
        return args


class TestSequential:
    """Test cases for Sequential composite module."""

    @pytest.mark.asyncio
    async def test_sequential_basic(self):
        """Test basic sequential execution."""
        pipeline = Sequential(SimpleModule(2), SimpleModule(3), SimpleModule(4))

        result = await pipeline(5)
        assert result == 120  # 5 * 2 * 3 * 4

    @pytest.mark.asyncio
    async def test_sequential_mixed_sync_async(self):
        """Test sequential execution with mixed sync/async modules."""
        pipeline = Sequential(SimpleModule(2), AsyncModule(0.01), SimpleModule(3))

        result = await pipeline(5)
        assert result == 60  # 5 * 2 * 2 * 3

    @pytest.mark.asyncio
    async def test_sequential_context_propagation(self):
        """Test that context propagates through sequential modules."""
        pipeline = Sequential(SimpleModule(2), SimpleModule(3))

        with Context.with_(timeout=10.0, test_key="test_value"):
            result = await pipeline(5)
            assert result == 30
            # Context should be available throughout
            ctx = Context.current()
            assert ctx.metadata.get("test_key") == "test_value"


class TestParallel:
    """Test cases for Parallel composite module."""

    @pytest.mark.asyncio
    async def test_parallel_basic(self):
        """Test basic parallel execution."""
        pipeline = Parallel(SimpleModule(2), SimpleModule(3), SimpleModule(4))

        result = await pipeline(5)
        assert result == (10, 15, 20)  # All executed in parallel

    @pytest.mark.asyncio
    async def test_parallel_mixed_sync_async(self):
        """Test parallel execution with mixed sync/async modules."""
        start_time = time.monotonic()

        pipeline = Parallel(
            AsyncModule(0.1), SimpleModule(3), AsyncModule(0.05)  # 100ms delay  # Instant  # 50ms delay
        )

        result = await pipeline(5)
        end_time = time.monotonic()

        assert result == (10, 15, 10)  # All results correct
        # Should complete in roughly 100ms (longest delay)
        assert end_time - start_time >= 0.09  # Allow some tolerance

    @pytest.mark.asyncio
    async def test_parallel_context_isolation(self):
        """Test that parallel branches have isolated contexts."""
        pipeline = Parallel(SimpleModule(2), SimpleModule(3))

        with Context.with_(timeout=10.0, shared_key="shared"):
            result = await pipeline(5)
            assert result == (10, 15)

            # Each branch should have its own context snapshot
            # but inherit the parent context settings
            ctx = Context.current()
            assert ctx.metadata.get("shared_key") == "shared"

    @pytest.mark.asyncio
    async def test_parallel_error_handling(self):
        """Test parallel execution with error handling."""
        pipeline = Parallel(SimpleModule(2), ErrorModule(), SimpleModule(4))

        with pytest.raises(ValueError, match="Test error"):
            await pipeline(5)


class TestConditional:
    """Test cases for Conditional composite module."""

    @pytest.mark.asyncio
    async def test_conditional_true_branch(self):
        """Test conditional execution with true condition."""
        pipeline = Conditional(condition=lambda x: x > 5, true_module=SimpleModule(10), false_module=SimpleModule(1))

        result = await pipeline(10)
        assert result == 100  # Should use true_module (10 * 10)

    @pytest.mark.asyncio
    async def test_conditional_false_branch(self):
        """Test conditional execution with false condition."""
        pipeline = Conditional(condition=lambda x: x > 5, true_module=SimpleModule(10), false_module=SimpleModule(1))

        result = await pipeline(3)
        assert result == 3  # Should use false_module (3 * 1)

    @pytest.mark.asyncio
    async def test_conditional_async_modules(self):
        """Test conditional execution with async modules."""
        pipeline = Conditional(condition=lambda x: x > 5, true_module=AsyncModule(0.01), false_module=SimpleModule(1))

        result = await pipeline(10)
        assert result == 20  # Should use async true_module (10 * 2)

    @pytest.mark.asyncio
    async def test_conditional_context_propagation(self):
        """Test that context propagates to the selected branch."""
        pipeline = Conditional(condition=lambda x: x > 5, true_module=SimpleModule(10), false_module=SimpleModule(1))

        with Context.with_(timeout=10.0, test_key="conditional"):
            result = await pipeline(10)
            assert result == 100

            # Context should be available in the executed branch
            ctx = Context.current()
            assert ctx.metadata.get("test_key") == "conditional"

    @pytest.mark.asyncio
    async def test_conditional_multiple_args(self):
        """Test conditional execution with multiple arguments."""
        pipeline = Conditional(
            condition=lambda x, y: x > 5 and y > 5,
            true_module=SimpleModule(10),
            false_module=SimpleModule(1),
        )

        result = await pipeline(10, 10)
        assert result == 100  # Should use true_module (10 * 10)


class TestDelay:
    """Test cases for Delay composite module."""

    @pytest.mark.asyncio
    async def test_delay_basic(self):
        """Test basic delay functionality."""
        delay_module = Delay(seconds=0.1)

        start_time = time.monotonic()
        result = await delay_module(42)
        end_time = time.monotonic()

        assert result == 42  # Input should be preserved
        assert end_time - start_time >= 0.09  # Should delay for ~100ms

    @pytest.mark.asyncio
    async def test_delay_multiple_args(self):
        """Test delay with multiple arguments."""
        delay_module = Delay(seconds=0.01)

        result = await delay_module(1, 2, 3)
        assert result == (1, 2, 3)  # Should preserve tuple

    @pytest.mark.asyncio
    async def test_delay_context_preservation(self):
        """Test that delay preserves context."""
        delay_module = Delay(seconds=0.01)

        with Context.with_(timeout=10.0, delay_test="preserved"):
            result = await delay_module(42)
            assert result == 42

            # Context should still be available after delay
            ctx = Context.current()
            assert ctx.metadata.get("delay_test") == "preserved"


class TestRetry:
    """Test cases for Retry composite module."""

    @pytest.mark.asyncio
    async def test_retry_success_first_try(self):
        """Test retry with immediate success."""
        retry_module = Retry(SimpleModule(2), max_retries=3, retryable_exceptions=(ValueError,))

        result = await retry_module(5)
        assert result == 10  # Should succeed immediately

    @pytest.mark.asyncio
    async def test_retry_success_after_retries(self):
        """Test retry that succeeds after some failures."""
        call_count = 0

        class FailingModule(Module):
            def forward(self, x: int) -> int:
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise ValueError("Temporary failure")
                return x * 2

        retry_module = Retry(FailingModule(), max_retries=3, retryable_exceptions=(ValueError,))

        result = await retry_module(5)
        assert result == 10  # Should succeed after 2 retries
        assert call_count == 3  # Should have been called 3 times

    @pytest.mark.asyncio
    async def test_retry_max_retries_exceeded(self):
        """Test retry that fails after max retries."""
        retry_module = Retry(ErrorModule(), max_retries=2, retryable_exceptions=(ValueError,))

        with pytest.raises(ValueError, match="Test error"):
            await retry_module(5)

    @pytest.mark.asyncio
    async def test_retry_non_retryable_exception(self):
        """Test retry with non-retryable exception."""
        retry_module = Retry(
            ErrorModule(), max_retries=3, retryable_exceptions=(TypeError,)  # ValueError not in retryable
        )

        with pytest.raises(ValueError, match="Test error"):
            await retry_module(5)

    @pytest.mark.asyncio
    async def test_retry_context_preservation(self):
        """Test that retry preserves context across attempts."""
        call_count = 0

        class ContextAwareModule(Module):
            def forward(self, x: int) -> int:
                nonlocal call_count
                call_count += 1
                ctx = Context.current()
                assert ctx.metadata.get("retry_test") == "preserved"

                if call_count < 2:
                    raise ValueError("Temporary failure")
                return x * 2

        retry_module = Retry(ContextAwareModule(), max_retries=3, retryable_exceptions=(ValueError,))

        with Context.with_(timeout=10.0, retry_test="preserved"):
            result = await retry_module(5)
            assert result == 10
            assert call_count == 2


class TestComplexComposition:
    """Test cases for complex module compositions."""

    @pytest.mark.asyncio
    async def test_nested_composition(self):
        """Test nested composition of different composite types."""
        pipeline = Sequential(
            SimpleModule(2),
            Parallel(SimpleModule(3), SimpleModule(4)),
            Conditional(
                condition=lambda x: isinstance(x, tuple) and len(x) == 2,
                true_module=AggregatorModule(),
                false_module=IdentityModule(),
            ),
        )

        result = await pipeline(5)
        # 5 * 2 = 10
        # Parallel: (10 * 3, 10 * 4) = (30, 40)
        # Conditional: (30, 40) is tuple with len 2, so aggregate: 30 + 40 = 70
        assert result == 70

    @pytest.mark.asyncio
    async def test_complex_workflow(self):
        """Test a complex workflow with multiple composite types."""
        workflow = Sequential(
            SimpleModule(2),
            Parallel(Sequential(SimpleModule(3), Delay(0.01)), Sequential(SimpleModule(4), Delay(0.01))),
            AggregatorModule(),
            Conditional(condition=lambda x: x > 100, true_module=SimpleModule(10), false_module=SimpleModule(1)),
        )

        result = await workflow(5)
        # 5 * 2 = 10
        # Parallel: (10 * 3, 10 * 4) = (30, 40)
        # Aggregator: 30 + 40 = 70
        # Conditional: 70 > 100? No, so 70 * 1 = 70
        assert result == 70
