import asyncio

import pytest

from mai.layers.module import Module


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


class TestModule:
    """Test suite for the Module base class."""

    def test_module_initialization(self):
        """Test that modules can be initialized properly."""
        module = SimpleModule(multiplier=3)
        assert module.multiplier == 3

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
        result = await module.forward(5)
        assert result == 6

    def test_inheritance_required(self):
        """Test that forward() must be implemented by subclasses."""
        module = Module()
        with pytest.raises(NotImplementedError):
            module.forward(42)


class TestModuleStaticConfig:
    """Test module static configuration."""

    def test_static_config_initialization(self):
        """Test static configuration."""
        module = SimpleModule(multiplier=3)

        assert module.multiplier == 3
        assert hasattr(module, "_static_cfg")
        assert module._static_cfg == {}

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
