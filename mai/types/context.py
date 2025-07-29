"""Request-scoped context management for pymai framework.

This module provides the Context class for managing request-scoped data
such as deadlines, tracing information, authentication, retries, and
other cross-cutting concerns. The Context uses contextvars for thread-safe
propagation through the call stack.
"""

import time
import uuid
from contextvars import ContextVar, Token
from typing import Any, ClassVar

import pydantic


def _is_wall_clock_time(t: float) -> bool:
    """Checks if time.time() was used instead of time.monotonic().

    This function detects whether a timestamp was created using wall clock
    time (time.time()) instead of monotonic time (time.monotonic()). It
    uses a 10-year threshold to distinguish between the two time sources.

    Args:
        t: Timestamp to check

    Returns:
        True if the timestamp appears to be wall clock time, False otherwise

    Note:
        This is used to enforce the use of monotonic time for deadlines
        to ensure consistent behavior across system clock changes.
    """
    ONE_YEAR_IN_SECONDS = 365 * 24 * 60 * 60
    threshold = 10 * ONE_YEAR_IN_SECONDS
    return abs(t - time.monotonic()) > threshold


class Context(pydantic.BaseModel):
    """Request-scoped carrier for deadlines, tracing, auth, retries, etc.

    The Context class provides a unified way to carry request-scoped data
    through the call stack. It uses contextvars for thread-safe propagation
    and Pydantic for validation and serialization.

    Key features:
    - Deadline management with monotonic time validation
    - Metadata storage for arbitrary key-value pairs
    - Retry tracking and step identification
    - OpenTelemetry span integration
    - Automatic context propagation through modules
    - Context manager support for automatic cleanup

    The Context enforces the use of monotonic time for deadlines to ensure
    consistent behavior across system clock changes.

    Example:
        # Create context with timeout
        ctx = Context(deadline=time.monotonic() + 30)

        # Add metadata
        ctx.metadata["user_id"] = "12345"

        # Access current context
        current = Context.current()

        # Use as context manager
        with Context.with_(timeout=30, user_id="12345"):
            # Context is automatically set and reset
            result = await some_operation()
    """

    model_config = pydantic.ConfigDict(extra="ignore")

    __current_ctx: ClassVar[ContextVar["Context"]] = ContextVar("__current_ctx")

    # ------------------------------------------------------------------
    # Core fields
    # ------------------------------------------------------------------
    deadline: float | None = None  # epoch seconds
    metadata: dict[str, Any] = pydantic.Field(default_factory=dict)

    retry_count: int = 0
    step_id: str = pydantic.Field(default_factory=lambda: uuid.uuid4().hex)
    span: Any | None = None  # OpenTelemetry span (optional)

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------
    _token: Token | None = None  # Internal token for context manager

    def __enter__(self) -> "Context":
        """Enters the context manager, setting this context as current.

        This method sets this Context instance as the current context
        and stores the token for later cleanup in __exit__.

        Returns:
            Self for method chaining

        Example:
            ctx = Context(timeout=30)
            with ctx:
                # This context is now current
                current = Context.current()
        """
        self._token = self.__current_ctx.set(self)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exits the context manager, resetting to previous context.

        This method resets the context to the previous state using
        the stored token, ensuring proper cleanup regardless of
        how the context manager is exited.

        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
        """
        if self._token is not None:
            self.__current_ctx.reset(self._token)
            self._token = None

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    @pydantic.field_validator("deadline")  # type: ignore[misc]
    def validate_deadline(cls, v: float | None) -> float | None:
        """Validates that deadline uses monotonic time.

        This validator ensures that deadlines are specified using monotonic
        time (time.monotonic()) rather than wall clock time (time.time()).
        This prevents issues with system clock changes affecting deadline
        calculations.

        Args:
            v: Deadline value to validate

        Returns:
            The validated deadline value

        Raises:
            ValueError: If deadline uses wall clock time instead of monotonic time
        """
        if v is not None and _is_wall_clock_time(v):
            raise ValueError("'deadline' must be monotonic time")
        return v

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------
    @staticmethod
    def from_kwargs(src: dict[str, Any] | None) -> "Context":
        """Extracts or builds a Context from a kwargs dictionary.

        This method processes a kwargs dictionary to extract or build a Context
        object. It handles several key transformations:

        1. If 'ctx' key contains a Context object, it uses that as the base
        2. Converts 'timeout' (seconds) to absolute 'deadline' using monotonic time
        3. Copies non-private keys (not starting with "_") into metadata
        4. Removes consumed keys from the source dict to prevent leakage

        Args:
            src: Source dictionary containing context-related keys, or None

        Returns:
            A Context object built from the source dictionary

        Raises:
            TypeError: If src is not a dict or None
            ValueError: If both 'deadline' and 'timeout' are specified
            TypeError: If 'ctx' is not a Context object

        Example:
            kwargs = {"timeout": 30, "user_id": "12345"}
            ctx = Context.from_kwargs(kwargs)
            # ctx.deadline will be set to time.monotonic() + 30
            # ctx.metadata will contain {"user_id": "12345"}
            # kwargs will be modified to remove consumed keys
        """
        if src is None:
            return Context()
        if not isinstance(src, dict):
            raise TypeError("from_kwargs expects a dict or None")

        # Only one of these should be set
        if "deadline" in src and "timeout" in src:
            raise ValueError("'deadline' and 'timeout' cannot be set at the same time")

        # 1. Explicit Context supplied?
        ctx = src.pop("ctx", None)
        if ctx is None:
            ctx = Context()
        if not isinstance(ctx, Context):
            raise TypeError("'ctx' must be a Context object")
        # Collect all arguments into the Context
        # and create a new Context object
        ctx_kwargs = ctx.model_dump()
        ctx_kwargs.update(src)
        ctx = ctx.model_validate(ctx_kwargs)

        # 2. Pop all the fields -- they are already in the Context
        for key in Context.model_fields.keys():
            src.pop(key, None)

        # 3. Timeout -> deadline
        # We already checked that deadline and timeout are not set at the same time
        # timeout = src.pop("timeout", None)
        if (timeout := src.pop("timeout", None)) is not None:
            ctx.deadline = time.monotonic() + timeout

        # 4. Capture non-private kwargs as metadata
        meta = {k: v for k, v in list(src.items()) if not k.startswith("_")}
        ctx.metadata.update(**meta)

        # Remove copied keys so they don't leak to downstream Modules
        for k in meta.keys():
            src.pop(k, None)

        return ctx  # type: ignore[no-any-return]

    # ------------------------------------------------------------------
    # Context management
    # ------------------------------------------------------------------
    @classmethod
    def current(cls) -> "Context":
        """Gets the current context from the contextvars stack.

        This method retrieves the current Context from the contextvars stack.
        If no context exists, it creates a new default Context and sets it
        as the current context.

        Returns:
            The current Context object

        Example:
            ctx = Context.current()
            print(f"Current deadline: {ctx.deadline}")
        """
        return cls.get()

    @classmethod
    def set(cls, **kwargs: Any) -> Token:
        """Sets a new context as the current context.

        This method creates a new Context from the provided kwargs and
        sets it as the current context in the contextvars stack. It returns
        a token that can be used to reset the context later.

        Args:
            **kwargs: Keyword arguments to build the Context from

        Returns:
            A token that can be used to reset the context

        Example:
            token = Context.set(timeout=30, user_id="12345")
            try:
                # Current context has timeout and user_id
                ctx = Context.current()
            finally:
                Context.reset(token)
        """
        ctx = Context.from_kwargs(kwargs)
        return cls.__current_ctx.set(ctx)

    @classmethod
    def with_(cls, **kwargs: Any) -> "Context":
        """Creates a context manager for temporary context settings.

        This method creates a Context object that can be used as a context
        manager. When entered, it sets the context as current, and when
        exited, it automatically resets to the previous context.

        The new context inherits from the current context, so metadata
        and other fields are properly merged.

        Args:
            **kwargs: Keyword arguments to build the Context from

        Returns:
            A Context object that can be used as a context manager

        Example:
            with Context.with_(timeout=30, user_id="12345"):
                # Context is automatically set and reset
                result = await some_operation()
        """
        # Start with current context as base
        current_ctx = cls.get()
        kwargs["ctx"] = current_ctx
        return cls.from_kwargs(kwargs)

    @classmethod
    def get(cls) -> "Context":
        """Gets the current context, creating a new one if none exists.

        This method retrieves the current Context from the contextvars stack.
        If no context exists, it creates a new default Context and sets it
        as the current context before returning it.

        Returns:
            The current Context object

        Example:
            ctx = Context.get()
            if ctx.deadline and time.monotonic() > ctx.deadline:
                raise TimeoutError("Request deadline exceeded")
        """
        try:
            return cls.__current_ctx.get()
        except LookupError:
            ctx = Context()
            cls.__current_ctx.set(ctx)
            return ctx

    @classmethod
    def reset(cls, token: Token) -> None:
        """Resets the context to a previous state using a token.

        This method resets the contextvars stack to the state represented
        by the provided token. This is typically used to restore the context
        after temporarily setting a new context.

        Args:
            token: Token returned from a previous Context.set() call

        Example:
            token = Context.set(timeout=30)
            try:
                # Use the new context
                result = await some_operation()
            finally:
                Context.reset(token)  # Restore previous context
        """
        return cls.__current_ctx.reset(token)
