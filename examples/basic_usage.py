"""Basic usage example demonstrating the pymai framework."""

import asyncio
from typing import Any

from mai.layers import Module


class TextProcessor(Module):
    """A simple text processing module."""

    def __init__(self, uppercase: bool = True):
        super().__init__()
        self.uppercase = uppercase

    def forward(self, text: str) -> str:
        """Process text based on configuration."""
        if self.uppercase:
            return text.upper()
        return text.lower()


class WordCounter(Module):
    """Count words in text."""

    def forward(self, text: str) -> int:
        """Count words in the input text."""
        return len(text.split())


class AsyncTextAnalyzer(Module):
    """An async module that simulates text analysis."""

    def __init__(self, delay: float = 0.1):
        super().__init__()
        self.delay = delay

    async def forward(self, text: str) -> dict[str, Any]:
        """Analyze text asynchronously."""
        # Simulate async processing
        await asyncio.sleep(self.delay)

        return {
            "length": len(text),
            "word_count": len(text.split()),
            "char_count": len(text.replace(" ", "")),
            "processed": True,
        }


class TextPipeline(Module):
    """A pipeline that combines multiple text processing steps."""

    def __init__(self):
        super().__init__()
        self.processor = TextProcessor(uppercase=True)
        self.counter = WordCounter()
        self.analyzer = AsyncTextAnalyzer(delay=0.05)

    async def forward(self, text: str) -> dict[str, Any]:
        """Process text through the entire pipeline."""
        # Step 1: Process text (sync)
        processed_text = self.processor.forward(text)

        # Step 2: Count words (sync)
        word_count = self.counter.forward(processed_text)

        # Step 3: Analyze asynchronously
        analysis = await self.analyzer(processed_text)

        return {"original": text, "processed": processed_text, "word_count": word_count, "analysis": analysis}


async def main():
    """Demonstrate basic pymai usage."""
    print("🚀 pymai Basic Usage Example\n")

    # Create a configured pipeline
    pipeline = TextPipeline().with_(delay=0.02)

    # Test data
    test_texts = [
        "Hello world from pymai!",
        "This is a test of the framework.",
        "Async and sync modules work together seamlessly.",
    ]

    print("Processing texts through the pipeline...\n")

    for i, text in enumerate(test_texts, 1):
        print(f"Text {i}: {text}")

        # Process through pipeline
        result = await pipeline(text)

        print(f"  -> Processed: {result['processed']}")
        print(f"  -> Word count: {result['word_count']}")
        print(f"  -> Analysis: {result['analysis']}")
        print()

    print("✅ Pipeline execution completed!")

    # Demonstrate individual module usage
    print("\n--- Individual Module Usage ---")

    processor = TextProcessor(uppercase=False)
    result = await processor("Hello World")
    print(f"Lowercase processor: {result}")

    counter = WordCounter()
    count = await counter("One two three four five")
    print(f"Word counter: {count} words")


if __name__ == "__main__":
    asyncio.run(main())
