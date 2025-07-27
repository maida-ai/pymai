"""Tests for the core Module abstraction."""

import asyncio

import pytest

from mai.layers import Module


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


class ConfigurableModule(Module):
    """A module that uses configuration."""

    def __init__(self, base_value: int = 10):
        super().__init__()
        self.base_value = base_value

    def forward(self, x: int) -> int:
        """Add base_value to input."""
        return x + self.base_value


class TestModule:
    """Test suite for the Module base class."""

    def test_module_initialization(self):
        """Test that modules can be initialized properly."""
        module = SimpleModule(multiplier=3)
        assert module.multiplier == 3
        assert isinstance(module._static_cfg, dict)

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

    @pytest.mark.asyncio
    async def test_async_forward(self):
        """Test async forward pass."""
        module = AsyncModule(delay=0.001)
        result = await module(5)
        assert result == 6

    def test_with_configuration(self):
        """Test module configuration with .with_()."""
        module = ConfigurableModule(base_value=10)
        configured_module = module.with_(base_value=20)

        # Original module should be unchanged
        assert module.base_value == 10
        assert module.forward(5) == 15

        # Configured module should use new value
        assert configured_module.forward(5) == 25

    @pytest.mark.asyncio
    async def test_static_config_merging(self):
        """Test that static config merges with call-time kwargs."""
        module = ConfigurableModule(base_value=10)
        configured_module = module.with_(base_value=20)

        # Call-time kwargs should override static config
        result = await configured_module(5, base_value=30)
        assert result == 35

    def test_inheritance_required(self):
        """Test that forward() must be implemented by subclasses."""
        module = Module()
        with pytest.raises(NotImplementedError):
            module.forward(42)

    @pytest.mark.asyncio
    async def test_context_cleanup(self):
        """Test that context is properly cleaned up after execution."""
        # This test will be expanded when Context is implemented
        module = SimpleModule()
        result = await module(5)
        assert result == 10
        # TODO: Add context cleanup verification when Context is implemented


class TestModuleComposition:
    """Test module composition patterns."""

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
