"""Core Module abstraction for composable AI components.

This module provides the foundational Module class that serves as the base
for all composable AI components in the pymai framework. The Module abstraction
enables seamless composition of both synchronous and asynchronous components
with automatic execution mode detection and context propagation.
"""

import inspect
from typing import Any, Self

import anyio

from mai.types.context import Context


class Module:
    """Base class for all composable AI components in the pymai framework.

    The Module class provides a unified abstraction for AI components, automatically
    handling both synchronous and asynchronous execution modes. It implements
    context propagation, configuration management, and type-safe I/O patterns.

    Key features:
    - Automatic sync/async detection and execution
    - Context propagation for deadlines, tracing, auth, etc.
    - Configuration management via .with_() method
    - Thread pool execution for sync functions to keep event loop responsive
    - Type-safe I/O with runtime validation

    Subclasses must implement the forward() method, which can be either
    synchronous or asynchronous. The runtime automatically detects the execution
    mode and handles it appropriately.

    Example:
        class TextProcessor(Module):
            def forward(self, text: str) -> str:
                return text.upper()

        processor = TextProcessor().with_(timeout=10)
        result = await processor("hello world")
    """

    def __new__(cls, *args: Any, **kwargs: Any) -> Self:
        """Creates a new Module instance with static configuration.

        Args:
            *args: Positional arguments passed to the constructor
            **kwargs: Keyword arguments passed to the constructor

        Returns:
            A new Module instance with initialized static configuration
        """
        instance = super().__new__(cls)
        instance._static_cfg = {}
        return instance

    def __init__(self, *args: Any, **kwargs: Any):
        """Initializes the Module with optional configuration.

        This method is called after __new__ to complete the initialization.
        The _static_cfg attribute is initialized in __new__ to ensure
        it's available for the .with_() method.

        Args:
            *args: Positional arguments (typically unused in base class)
            **kwargs: Keyword arguments (typically unused in base class)
        """
        # We need init to avoid mypy complaining about _static_cfg being undefined
        # Practically, it is defined in __new__
        self._static_cfg: dict[str, Any] = {}

    def with_(self, **cfg: Any) -> Self:
        """Attaches static configuration overrides for this module.

        This method allows setting configuration values that will be applied
        to all future calls to this module. Common configuration options
        include timeout, threshold, model parameters, etc.

        Args:
            **cfg: Configuration key-value pairs to attach to this module

        Returns:
            Self for method chaining

        Example:
            module = MyModule().with_(timeout=30, threshold=0.8)
            result = await module(input_data)
        """
        self._static_cfg |= cfg
        return self

    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Executes the module with automatic sync/async detection.

        This method is the main entry point for module execution. It:
        1. Merges static configuration with call-time settings
        2. Sets up context propagation
        3. Detects if forward() is sync or async
        4. Executes in appropriate execution mode
        5. Cleans up context on completion

        Args:
            *args: Positional arguments to pass to forward()
            **kwargs: Keyword arguments to pass to forward()

        Returns:
            The result from the forward() method

        Raises:
            NotImplementedError: If forward() method is not implemented
            Exception: Any exception raised by the forward() method
        """
        # merge static + call-time settings
        kwargs = {**self._static_cfg, **kwargs}
        ctx_token = Context.set(**kwargs)
        try:
            fn = inspect.unwrap(self.forward)
            if inspect.iscoroutinefunction(fn):
                return await fn(*args, **kwargs)
            # run sync forward in a worker thread so event loop stays responsive
            return await anyio.to_thread.run_sync(fn, *args, **kwargs)
        finally:
            Context.reset(ctx_token)

    def forward(self, *args: Any, **kwargs: Any) -> Any:
        """Core processing logic to be implemented by subclasses.

        This method contains the main processing logic for the module.
        It can be implemented as either a synchronous or asynchronous
        method - the runtime will automatically detect and handle the
        execution mode appropriately.

        Args:
            *args: Input arguments for processing
            **kwargs: Keyword arguments for processing

        Returns:
            The processed result

        Raises:
            NotImplementedError: This method must be implemented by subclasses

        Example:
            def forward(self, text: str) -> str:
                return text.upper()
        """
        raise NotImplementedError
