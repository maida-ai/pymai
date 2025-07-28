import time
import uuid
from contextvars import ContextVar, Token
from typing import Any, ClassVar

import pydantic


def _is_wall_clock_time(t: float) -> bool:
    """Checks if time.time() was used.

    We will use a 10 year difference between monotonic
    and wall clock. If the difference is greater than 10 years,
    we can assume that time.time() was used.
    """
    ONE_YEAR_IN_SECONDS = 365 * 24 * 60 * 60
    threshold = 10 * ONE_YEAR_IN_SECONDS
    return abs(t - time.monotonic()) > threshold


class Context(pydantic.BaseModel):
    """Request-scoped carrier for deadlines, tracing, auth, retries, etc."""

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
    # Validation
    # ------------------------------------------------------------------
    @pydantic.field_validator("deadline")  # type: ignore[misc]
    def validate_deadline(cls, v: float | None) -> float | None:
        if v is not None and _is_wall_clock_time(v):
            raise ValueError("'deadline' must be monotonic time")
        return v

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------
    @staticmethod
    def from_kwargs(src: dict[str, Any] | None) -> "Context":
        """Extract (or build) a **Context** from a kwargs dict.

        * If `ctx` holds a *Context* object, return it.
        * Consumes `timeout` (seconds) -> absolute `deadline`.
        * Copies remaining **non-private** keys (not starting with "_") into
          `metadata` so they propagate through the graph.
        * Pops the consumed keys from *src* so they won't reach user
          `forward()` signatures.

        Note: This is a destructuve function: The input dict is modified.
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
        """Get the current context."""
        return cls.get()

    @classmethod
    def set(cls, **kwargs: Any) -> Token:
        ctx = Context.from_kwargs(kwargs)
        return cls.__current_ctx.set(ctx)

    @classmethod
    def get(cls) -> "Context":
        try:
            return cls.__current_ctx.get()
        except LookupError:
            ctx = Context()
            cls.__current_ctx.set(ctx)
            return ctx

    @classmethod
    def reset(cls, token: Token) -> None:
        return cls.__current_ctx.reset(token)
