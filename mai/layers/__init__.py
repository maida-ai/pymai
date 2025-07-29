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

Composite modules provide invisible execution patterns:
- Sequential: Chain modules in sequence
- Parallel: Execute modules concurrently
- Conditional: Execute based on conditions
- Delay: Add non-blocking delays
- Retry: Automatic retry with backoff

Example:
    from mai.layers import Module, Sequential, Parallel

    class TextProcessor(Module):
        def forward(self, text: str) -> str:
            return text.upper()

    # Invisible execution - no Engine API needed
    pipeline = Sequential(
        TextProcessor(),
        Parallel(
            Module1(),
            Module2()
        )
    )
    result = await pipeline("hello world")
"""

from .composite import Conditional, Delay, Parallel, Retry, Sequential
from .module import Module

__all__ = ["Module", "Sequential", "Parallel", "Conditional", "Delay", "Retry"]
