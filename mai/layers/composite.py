"""Composite modules for invisible execution patterns.

This module provides composite modules that implement complex execution patterns
without exposing an Engine API to users. These composites work seamlessly with
the existing Module abstraction, providing PyTorch-style invisible execution.
"""

import asyncio
import inspect
from collections.abc import Callable
from typing import Any

from mai.layers.module import Module


class Sequential(Module):
    """Sequential composition of modules - invisible execution like PyTorch.

    Executes modules in sequence, automatically handling sync/async boundaries
    and context propagation. No Engine API needed - just compose and call.

    Example:
        pipeline = Sequential(
            Tokenize(tokenizer),
            Embed(model),
            Classify(classifier)
        )
        result = await pipeline(text="hello world")
    """

    def __init__(self, *modules: Module):
        """Initialize sequential composition.

        Args:
            *modules: Modules to execute in sequence
        """
        super().__init__()
        self.modules = modules

    async def forward(self, *args: Any, **kwargs: Any) -> Any:
        """Execute modules sequentially with automatic optimization.

        This method implements invisible execution - no Engine API needed.
        The runtime automatically:
        - Detects sync/async boundaries
        - Propagates context through the chain
        - Optimizes trivial operations
        - Handles error propagation

        Args:
            *args: Input arguments for the first module
            **kwargs: Keyword arguments for all modules

        Returns:
            Final result from the last module in the sequence
        """
        result = args
        for module in self.modules:
            # Handle both single values and tuples
            if isinstance(result, tuple):
                result = await module(*result, **kwargs)
            else:
                result = await module(result, **kwargs)  # type: ignore[unreachable]
        return result


class Parallel(Module):
    """Parallel execution of modules with context isolation.

    Executes multiple modules concurrently, each with its own context snapshot.
    Like PyTorch's parallel execution, this is invisible to the user.

    Example:
        parallel = Parallel(
            Agent1().with_(timeout=5.0),
            Agent2().with_(timeout=3.0)
        )
        results = await parallel(embedding)
    """

    def __init__(self, *modules: Module):
        """Initialize parallel composition.

        Args:
            *modules: Modules to execute in parallel
        """
        super().__init__()
        self.modules = modules

    async def forward(self, *args: Any, **kwargs: Any) -> tuple[Any, ...]:
        """Execute modules in parallel with context isolation.

        Each module gets its own context snapshot, ensuring isolation
        while maintaining the parent context's core settings.

        Args:
            *args: Input arguments for all modules
            **kwargs: Keyword arguments for all modules

        Returns:
            Tuple of results from all modules
        """
        # Create tasks for parallel execution
        tasks = []
        for module in self.modules:
            task = module(*args, **kwargs)
            tasks.append(task)

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions gracefully
        for result in results:
            if isinstance(result, Exception):
                raise result

        return tuple(results)


class Conditional(Module):
    """Conditional execution based on a predicate.

    Executes different modules based on a condition, with automatic
    context propagation and error handling.

    Example:
        conditional = Conditional(
            condition=lambda x: x > 0,
            true_module=PositiveProcessor(),
            false_module=NegativeProcessor()
        )
        result = await conditional(value)
    """

    def __init__(self, condition: Callable[..., bool], true_module: Module, false_module: Module):
        """Initialize conditional execution.

        Args:
            condition: Function that determines which module to execute
            true_module: Module to execute when condition is True
            false_module: Module to execute when condition is False
        """
        super().__init__()
        self.condition = condition
        self.true_module = true_module
        self.false_module = false_module

    async def forward(self, *args: Any, **kwargs: Any) -> Any:
        """Execute conditionally with automatic context handling.

        Args:
            *args: Input arguments for the selected module
            **kwargs: Keyword arguments for the selected module

        Returns:
            Result from the executed module
        """
        # Evaluate condition with proper argument handling

        cond_params = inspect.signature(self.condition).parameters
        if len(cond_params) == 1:
            # If the condition expects a single argument, pass all as a tuple
            should_execute_true = self.condition(args if len(args) > 1 else args[0])
        else:
            should_execute_true = self.condition(*args)

        # Execute appropriate module
        if should_execute_true:
            return await self.true_module(*args, **kwargs)
        else:
            return await self.false_module(*args, **kwargs)


class Delay(Module):
    """Non-blocking delay with context preservation.

    Adds a delay without blocking the event loop or affecting context.
    Useful for rate limiting and timing control.

    Example:
        delayed = Sequential(
            ProcessModule(),
            Delay(seconds=1.0),  # 1 second delay
            PostProcessModule()
        )
    """

    def __init__(self, seconds: float):
        """Initialize delay module.

        Args:
            seconds: Delay duration in seconds
        """
        super().__init__()
        self.seconds = seconds

    async def forward(self, *args: Any, **kwargs: Any) -> Any:
        """Add delay while preserving input.

        Args:
            *args: Input arguments (preserved through delay)
            **kwargs: Keyword arguments (preserved through delay)

        Returns:
            Same input arguments (delayed)
        """
        await asyncio.sleep(self.seconds)

        # Return the input unchanged
        if len(args) == 1:
            return args[0]
        return args


class Retry(Module):
    """Automatic retry with exponential backoff.

    Wraps a module with automatic retry logic, maintaining context
    and handling different types of retryable errors.

    Example:
        retry_module = Retry(
            RemoteAPIModule(),
            max_retries=3,
            retryable_exceptions=(TimeoutError, ConnectionError)
        )
    """

    def __init__(
        self, module: Module, max_retries: int = 3, retryable_exceptions: tuple[type[Exception], ...] = (TimeoutError,)
    ):
        """Initialize retry wrapper.

        Args:
            module: Module to wrap with retry logic
            max_retries: Maximum number of retry attempts
            retryable_exceptions: Exception types that should trigger retries
        """
        super().__init__()
        self.module = module
        self.max_retries = max_retries
        self.retryable_exceptions = retryable_exceptions

    async def forward(self, *args: Any, **kwargs: Any) -> Any:
        """Execute with automatic retry logic.

        Args:
            *args: Input arguments for the wrapped module
            **kwargs: Keyword arguments for the wrapped module

        Returns:
            Result from the wrapped module

        Raises:
            Exception: Last exception if all retries fail
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                return await self.module(*args, **kwargs)

            except self.retryable_exceptions as e:
                last_exception = e

                # Don't retry on the last attempt
                if attempt == self.max_retries:
                    break

                # Exponential backoff
                delay = 2**attempt
                await asyncio.sleep(delay)

        # Re-raise the last exception
        if last_exception is not None:
            raise last_exception
