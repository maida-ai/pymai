"""Type system and Pydantic models for type-safe I/O.

This package provides the foundational type system for the pymai framework,
including the Context class for request-scoped data and Pydantic models
for type-safe data validation and serialization.

The type system enforces the "Know your types; Fail if unsure" principle
by requiring explicit type definitions for all public APIs and providing
runtime validation through Pydantic models.

Key components:
- Context: Request-scoped carrier for deadlines, tracing, auth, etc.
- Pydantic models: Type-safe data validation and serialization
- Type adapters: Conversion utilities for external data formats

Example:
    from mai.types import Context

    # Create context with timeout
    ctx = Context(deadline=time.monotonic() + 30)

    # Access current context
    current = Context.current()
"""

from .context import Context

__all__ = ["Context"]
