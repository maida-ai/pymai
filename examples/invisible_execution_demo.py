"""Demonstration of PyTorch-style invisible execution in pymai.

This example shows how complex AI workflows can be composed and executed
without exposing any Engine API to users. The execution engine is completely
invisible, just like PyTorch's autograd and JIT compilation.
"""

import asyncio
import time
from typing import Any

from mai.layers import Conditional, Delay, Module, Parallel, Retry, Sequential
from mai.types.context import Context

# ============================================================================
# Atomic Modules (like PyTorch layers)
# ============================================================================


class Tokenizer(Module):
    """Simple tokenizer module."""

    def forward(self, text: str) -> list[str]:
        """Tokenize text into words."""
        return text.lower().split()


class Embedder(Module):
    """Simple embedding module."""

    def forward(self, tokens: list[str]) -> list[float]:
        """Create simple embeddings."""
        return [len(token) * 0.1 for token in tokens]


class SentimentAnalyzer(Module):
    """Sentiment analysis module."""

    def forward(self, embeddings: list[float]) -> dict[str, Any]:
        """Analyze sentiment from embeddings."""
        avg_embedding = sum(embeddings) / len(embeddings) if embeddings else 0
        return {
            "sentiment": "positive" if avg_embedding > 0.5 else "negative",
            "confidence": min(abs(avg_embedding), 1.0),
            "score": avg_embedding,
        }


class KeywordExtractor(Module):
    """Keyword extraction module."""

    def forward(self, tokens: list[str]) -> list[str]:
        """Extract keywords (words longer than 3 characters)."""
        return [token for token in tokens if len(token) > 3]


class Summarizer(Module):
    """Text summarization module."""

    def forward(self, tokens: list[str]) -> str:
        """Create a simple summary."""
        if not tokens:
            return "Empty text"
        return f"Summary: {len(tokens)} words, key: {tokens[0]}"


class RemoteAPI(Module):
    """Simulates a remote API call."""

    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    async def forward(self, data: Any) -> dict[str, Any]:
        """Simulate remote API call with delay."""
        await asyncio.sleep(0.1)  # Simulate network delay
        return {"service": self.service_name, "result": f"Processed by {self.service_name}", "timestamp": time.time()}


class Aggregator(Module):
    """Aggregates results from parallel modules."""

    def forward(self, *results: Any) -> dict[str, Any]:
        """Combine results from parallel execution."""
        combined = {}
        for i, result in enumerate(results):
            if isinstance(result, dict):
                combined[f"branch_{i}"] = result
            else:
                combined[f"branch_{i}"] = {"value": result}
        return combined


class ThresholdFilter(Module):
    """Filters results based on threshold."""

    def __init__(self, threshold: float = 0.5):
        super().__init__()
        self.threshold = threshold

    def forward(self, data: dict[str, Any]) -> dict[str, Any]:
        """Filter data based on confidence threshold."""
        if "confidence" in data and data["confidence"] < self.threshold:
            return {"status": "rejected", "reason": "low_confidence"}
        return data


# ============================================================================
# Complex Workflow Composition (Invisible Execution)
# ============================================================================


def create_complex_workflow() -> Module:
    """Create a complex workflow without any Engine API.

    This demonstrates PyTorch-style composition where the execution
    engine is completely invisible to the user.
    """

    # Branch 1: Sentiment Analysis Pipeline
    sentiment_pipeline = Sequential(Embedder(), SentimentAnalyzer())

    # Branch 2: Content Analysis Pipeline
    content_pipeline = Sequential(Parallel(KeywordExtractor(), Summarizer()), Aggregator())

    # Branch 3: Remote API Calls (with retry)
    remote_pipeline = Sequential(
        Parallel(Retry(RemoteAPI("service_a"), max_retries=2), Retry(RemoteAPI("service_b"), max_retries=2)),
        Aggregator(),
    )

    # Main workflow with conditional execution
    main_workflow = Sequential(
        # Initial processing - tokenize once
        Tokenizer(),
        # Parallel analysis branches
        Parallel(
            sentiment_pipeline.with_(timeout=5.0),
            content_pipeline.with_(timeout=3.0),
            remote_pipeline.with_(timeout=10.0),
        ),
        # Aggregation
        Aggregator(),
        # Conditional filtering
        Conditional(
            condition=lambda data: "confidence" in data.get("branch_0", {}),
            true_module=ThresholdFilter(threshold=0.7),
            false_module=IdentityModule(),
        ),
        # Final delay for rate limiting
        Delay(seconds=0.1),
    )

    return main_workflow


class IdentityModule(Module):
    """Module that returns input unchanged."""

    def forward(self, data: Any) -> Any:
        """Return input unchanged."""
        return data


class StatusModule(Module):
    """Module that returns a status message."""

    def forward(self, text: str) -> dict[str, Any]:
        """Return status message."""
        return {"status": "too_short", "text": text}


# ============================================================================
# Usage Examples
# ============================================================================


async def demonstrate_invisible_execution():
    """Demonstrate PyTorch-style invisible execution."""

    print("=== PyTorch-Style Invisible Execution Demo ===\n")

    # Create complex workflow (no Engine API needed)
    workflow = create_complex_workflow()

    # Execute with context (invisible execution)
    print("1. Executing complex workflow...")
    with Context.with_(timeout=30.0, user_id="demo_user"):
        result = await workflow("Hello world, this is a test message for sentiment analysis!")

    print(f"Result: {result}")
    print(f"Context: {Context.current().metadata}")

    print("\n2. Executing with different context...")
    with Context.with_(timeout=15.0, operation="batch_processing"):
        result2 = await workflow("Another test message with different context")

    print(f"Result: {result2}")

    print("\n3. Demonstrating error handling...")
    try:
        with Context.with_(timeout=0.001):  # Very short timeout
            await workflow("This should timeout")
    except Exception as e:
        print(f"Expected error: {type(e).__name__}: {e}")


async def demonstrate_simple_composition():
    """Demonstrate simple module composition."""

    print("\n=== Simple Composition Demo ===\n")

    # Simple sequential pipeline
    simple_pipeline = Sequential(Tokenizer(), Embedder(), SentimentAnalyzer())

    print("Simple pipeline result:")
    result = await simple_pipeline("I love this framework!")
    print(f"Result: {result}")

    # Parallel execution with proper data types
    parallel_pipeline = Parallel(
        Sequential(Embedder(), SentimentAnalyzer()).with_(timeout=2.0), KeywordExtractor().with_(timeout=1.0)
    )

    print("\nParallel execution result:")
    tokens = ["hello", "world", "test", "message"]
    result = await parallel_pipeline(tokens)
    print(f"Result: {result}")


async def demonstrate_conditional_execution():
    """Demonstrate conditional execution."""

    print("\n=== Conditional Execution Demo ===\n")

    # Conditional based on input length
    conditional_pipeline = Conditional(
        condition=lambda text: len(text) > 10,
        true_module=Sequential(Tokenizer(), Summarizer()),
        false_module=StatusModule(),
    )

    # Test with short text
    result1 = await conditional_pipeline("Hi")
    print(f"Short text result: {result1}")

    # Test with long text
    result2 = await conditional_pipeline("This is a much longer text that should trigger the summarizer")
    print(f"Long text result: {result2}")


if __name__ == "__main__":
    asyncio.run(demonstrate_invisible_execution())
    asyncio.run(demonstrate_simple_composition())
    asyncio.run(demonstrate_conditional_execution())
