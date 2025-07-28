"""Core Module abstraction for composable AI components.

This package provides the foundational Module class that serves as the base
for all composable AI components in the pymai framework. The Module abstraction
enables seamless composition of both synchronous and asynchronous components
with automatic execution mode detection and context propagation.

The Module class implements the core design principles:
- Single abstraction for all components
- Automatic sync/async detection and execution
- Context propagation for cross-cutting concerns
- Configuration management via .with_() method
- Type-safe I/O with runtime validation

Example:
    from mai.layers import Module

    class TextProcessor(Module):
        def forward(self, text: str) -> str:
            return text.upper()

    processor = TextProcessor().with_(timeout=10)
    result = await processor("hello world")
"""

from .module import Module

__all__ = ["Module"]
