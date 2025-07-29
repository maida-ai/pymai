"""Demonstration of Context context manager functionality.

This example shows how to use the new context manager support in the Context class
for automatic cleanup and proper context propagation.
"""

import asyncio
import time

from mai.layers import Module
from mai.types.context import Context


class SimpleProcessor(Module):
    """A simple module that demonstrates context usage."""

    def forward(self, text: str, **kwargs) -> str:
        """Process text and demonstrate context access."""
        # Access current context
        ctx = Context.current()
        print(f"Processing with context: {ctx.metadata}")
        print(f"Additional kwargs: {kwargs}")

        # Check deadline if set
        if ctx.deadline and time.monotonic() > ctx.deadline:
            raise TimeoutError("Processing deadline exceeded")

        # Add processing metadata
        ctx.metadata["processed_at"] = time.monotonic()
        ctx.metadata["input_length"] = len(text)

        return f"Processed: {text.upper()}"


async def demonstrate_context_manager():
    """Demonstrate various context manager usage patterns."""

    processor = SimpleProcessor()

    print("=== Basic Context Manager Usage ===")
    with Context.with_(timeout=30, user_id="12345", operation="demo"):
        result = await processor("hello world")
        print(f"Result: {result}")
        print(f"Context after processing: {Context.current().metadata}")

    print("\n=== Nested Context Managers ===")
    with Context.with_(timeout=60, outer_key="outer_value"):
        print(f"Outer context: {Context.current().metadata}")

        with Context.with_(timeout=30, inner_key="inner_value"):
            print(f"Inner context: {Context.current().metadata}")
            result = await processor("nested example")
            print(f"Result: {result}")

        print(f"Back to outer context: {Context.current().metadata}")

    print("\n=== Direct Context Instance Usage ===")
    ctx = Context(timeout=15, metadata={"direct": "usage"})
    with ctx:
        result = await processor("direct context")
        print(f"Result: {result}")
        print(f"Context: {Context.current().metadata}")

    print("\n=== Exception Handling ===")
    try:
        with Context.with_(timeout=0.001):  # Very short timeout
            await asyncio.sleep(0.1)  # This will exceed the timeout
            result = await processor("should timeout")
    except TimeoutError as e:
        print(f"Caught timeout: {e}")

    print("\n=== Module with Context Manager ===")
    # The Module.__call__ method now uses Context.with_ internally
    result = await processor.with_(timeout=30, module_config="test")("module call")
    print(f"Module result: {result}")


if __name__ == "__main__":
    asyncio.run(demonstrate_context_manager())
