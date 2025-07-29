import asyncio

import pytest

from mai.layers.module import Module
from mai.types.context import Context


class SimpleModule(Module):
    """A simple test module that doubles the input."""

    def __init__(self, multiplier: int = 2):
        super().__init__()
        self.multiplier = multiplier

    def forward(self, x: int) -> int:
        """Double the input value."""
        return x * self.multiplier


class AsyncModule(Module):
    """An async test module that adds a delay."""

    def __init__(self, delay: float = 0.01):
        super().__init__()
        self.delay = delay

    async def forward(self, x: int) -> int:
        """Add delay and return input + 1."""
        await asyncio.sleep(self.delay)
        return x + 1


class ContextAwareModule(Module):
    """A module that uses context information."""

    def forward(self, x: int) -> int:
        """Use context to modify the result."""
        ctx = Context.current()
        if ctx.metadata.get("multiplier", None) is not None:
            return x * ctx.metadata["multiplier"]
        return x


class TestModuleInitialization:
    """Test cases for Module initialization and basic setup."""

    def test_module_initialization(self):
        """Test that modules can be initialized properly."""
        module = SimpleModule(multiplier=3)
        assert module.multiplier == 3

    def test_inheritance_required(self):
        """Test that forward() must be implemented by subclasses."""
        module = Module()
        with pytest.raises(NotImplementedError):
            module.forward(42)

    def test_static_config_initialization(self):
        """Test static configuration initialization."""
        module = SimpleModule(multiplier=3)

        assert module.multiplier == 3
        assert hasattr(module, "_static_cfg")
        assert module._static_cfg == {}


class TestModuleSyncExecution:
    """Test cases for synchronous module execution."""

    def test_sync_forward(self):
        """Test synchronous forward pass."""
        module = SimpleModule(multiplier=3)
        result = module.forward(5)
        assert result == 15

    @pytest.mark.asyncio
    async def test_async_call_sync_forward(self):
        """Test calling sync forward through async __call__."""
        module = SimpleModule(multiplier=3)
        result = await module(5)
        assert result == 15

    def test_sync_forward_with_kwargs(self):
        """Test sync forward with keyword arguments."""
        module = SimpleModule(multiplier=3)
        result = module.forward(x=5)
        assert result == 15


class TestModuleAsyncExecution:
    """Test cases for asynchronous module execution."""

    @pytest.mark.asyncio
    async def test_async_forward(self):
        """Test async forward pass."""
        module = AsyncModule(delay=0.001)
        result = await module.forward(5)
        assert result == 6

    @pytest.mark.asyncio
    async def test_async_call_async_forward(self):
        """Test calling async forward through async __call__."""
        module = AsyncModule(delay=0.001)
        result = await module(5)
        assert result == 6

    @pytest.mark.asyncio
    async def test_async_forward_with_kwargs(self):
        """Test async forward with keyword arguments."""
        module = AsyncModule(delay=0.001)
        result = await module.forward(x=5)
        assert result == 6


class TestModuleConfiguration:
    """Test cases for Module configuration management."""

    def test_static_config_setting(self):
        """Test static configuration setting."""
        module = SimpleModule(multiplier=3)

        # What happens when config is empty?
        module._static_cfg = {}
        module = module.with_(timeout=42)
        assert module._static_cfg == {"timeout": 42}

        # What happens when config is not empty?
        module._static_cfg = {"timeout": 42}
        module = module.with_(timeout=24)
        assert module._static_cfg == {"timeout": 24}

    def test_with_method_returns_self(self):
        """Test that with_() method returns self for chaining."""
        module = SimpleModule(multiplier=3)
        result = module.with_(timeout=30)
        assert result is module

    def test_multiple_config_settings(self):
        """Test setting multiple configuration values."""
        module = SimpleModule(multiplier=3)
        module = module.with_(timeout=30, threshold=0.8, max_retries=3)

        assert module._static_cfg == {"timeout": 30, "threshold": 0.8, "max_retries": 3}

    def test_config_override(self):
        """Test that new config values override existing ones."""
        module = SimpleModule(multiplier=3)
        module = module.with_(timeout=30)
        module = module.with_(timeout=60, new_param="value")

        assert module._static_cfg == {"timeout": 60, "new_param": "value"}


class TestModuleContextIntegration:
    """Test cases for Module context integration."""

    @pytest.mark.asyncio
    async def test_context_propagation(self):
        """Test that context is properly propagated to modules."""
        module = ContextAwareModule()

        with Context.with_(multiplier=3):
            result = await module(5)
            assert result == 15

    @pytest.mark.asyncio
    async def test_context_without_metadata(self):
        """Test module behavior when context has no relevant metadata."""
        module = ContextAwareModule()

        with Context.with_(timeout=30):
            result = await module(5)
            assert result == 5

    @pytest.mark.asyncio
    async def test_context_cleanup(self):
        """Test that context is properly cleaned up after module execution."""
        module = SimpleModule(multiplier=3)

        # Set up initial context
        initial_ctx = Context(metadata={"initial": "value"})
        token = Context.set(metadata=initial_ctx.metadata)

        try:
            # Execute module with different context
            with Context.with_(timeout=30, user_id="12345"):
                result = await module(5)
                assert result == 15

                # Verify current context has the expected values
                current_ctx = Context.current()
                assert current_ctx.metadata["user_id"] == "12345"
                assert current_ctx.metadata["initial"] == "value"
        finally:
            Context.reset(token)

    @pytest.mark.asyncio
    async def test_context_with_deadline(self):
        """Test module execution with deadline in context."""
        module = SimpleModule(multiplier=3)

        with Context.with_(timeout=1):  # 1 second timeout
            result = await module(5)
            assert result == 15


class TestModuleComposition:
    """Test cases for Module composition patterns."""

    def test_sequential_composition(self):
        """Test chaining modules together."""
        # This test will be expanded when Sequential is implemented
        module1 = SimpleModule(multiplier=2)
        module2 = SimpleModule(multiplier=3)

        # Manual composition
        result1 = module1.forward(5)
        result2 = module2.forward(result1)
        assert result2 == 30

    @pytest.mark.asyncio
    async def test_async_composition(self):
        """Test composing async and sync modules."""
        sync_module = SimpleModule(multiplier=2)
        async_module = AsyncModule(delay=0.001)

        # Manual composition
        result1 = await sync_module(5)
        result2 = await async_module(result1)
        assert result2 == 11

    @pytest.mark.asyncio
    async def test_mixed_composition_with_context(self):
        """Test composing modules with context propagation."""
        sync_module = SimpleModule(multiplier=2)
        context_module = ContextAwareModule()

        with Context.with_(multiplier=3):
            result1 = await sync_module(5)
            result2 = await context_module(result1)
            assert result2 == 30  # 5 * 2 * 3


class TestModuleErrorHandling:
    """Test cases for Module error handling."""

    def test_not_implemented_error(self):
        """Test that base Module raises NotImplementedError."""
        module = Module()
        with pytest.raises(NotImplementedError):
            module.forward(42)

    @pytest.mark.asyncio
    async def test_async_not_implemented_error(self):
        """Test that base Module raises NotImplementedError in async context."""
        module = Module()
        with pytest.raises(NotImplementedError):
            await module(42)

    def test_forward_with_invalid_args(self):
        """Test module behavior with invalid arguments."""
        module = SimpleModule(multiplier=3)

        # This should work fine with any numeric input
        result = module.forward(5.5)  # type: ignore[arg-type]  # TODO: Make this strict
        assert result == 16.5

    @pytest.mark.asyncio
    async def test_async_forward_with_invalid_args(self):
        """Test async module behavior with invalid arguments."""
        module = AsyncModule(delay=0.001)

        # This should work fine with any numeric input
        result = await module.forward(5.5)  # type: ignore[arg-type]  # TODO: Make this strict
        assert result == 6.5
