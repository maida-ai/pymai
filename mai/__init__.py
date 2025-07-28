"""pymai: A tiny-yet-powerful Python framework for composable AI agents and durable workflows.

This package provides a unified Module abstraction inspired by PyTorch's modular design,
enabling seamless composition of both synchronous and asynchronous AI components with
built-in observability and context propagation.

The framework is built around 8 core design principles:
- Single Module Abstraction: All components inherit from mai.layers.Module
- Sync/Async Auto-Detection: Runtime automatically handles execution modes
- Type-Safe I/O: Pydantic models for validation and serialization
- Invisible Context: Context propagation via contextvars
- Observability First: Rich tracing with OpenTelemetry
- Configurable Modules: Static and per-call configuration
- Micro-Kernel Core: Minimal core with pluggable backends
- Durable Workflows: Replay-able, resumable, idempotent steps

Example:
    from mai.layers import Module
    from mai.types import Context

    class MyAgent(Module):
        def forward(self, input_data: str) -> str:
            return f"Processed: {input_data}"

    agent = MyAgent().with_(timeout=30)
    result = await agent("Hello, World!")
"""
