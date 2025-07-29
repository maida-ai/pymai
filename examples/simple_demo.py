"""Simple demo to test basic functionality."""

import asyncio

from mai.layers import Module, Parallel, Sequential


class SimpleTokenizer(Module):
    """Simple tokenizer that handles both strings and lists."""

    def forward(self, text: str) -> list[str]:
        """Tokenize text into words."""
        if isinstance(text, list):
            # If already a list, return as is
            return text
        return text.lower().split()


class SimpleEmbedder(Module):
    """Simple embedding module."""

    def forward(self, tokens: list[str]) -> list[float]:
        """Create simple embeddings."""
        return [len(token) * 0.1 for token in tokens]


class SimpleAnalyzer(Module):
    """Simple analyzer module."""

    def forward(self, embeddings: list[float]) -> dict:
        """Analyze embeddings."""
        avg = sum(embeddings) / len(embeddings) if embeddings else 0
        return {"score": avg, "confidence": min(abs(avg), 1.0)}


async def test_simple_pipeline():
    """Test a simple pipeline."""
    print("=== Simple Pipeline Test ===")

    pipeline = Sequential(SimpleTokenizer(), SimpleEmbedder(), SimpleAnalyzer())

    result = await pipeline("Hello world test")
    print(f"Result: {result}")


async def test_parallel_pipeline():
    """Test a parallel pipeline."""
    print("\n=== Parallel Pipeline Test ===")

    pipeline = Parallel(SimpleAnalyzer(), SimpleAnalyzer())

    # Test with embeddings
    embeddings = [0.1, 0.2, 0.3, 0.4, 0.5]
    result = await pipeline(embeddings)
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(test_simple_pipeline())
    asyncio.run(test_parallel_pipeline())
