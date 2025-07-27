import time
import uuid
from typing import Any

from pydantic import BaseModel, Field


class Context(BaseModel):
    """Request-scoped carrier for deadlines, tracing, auth, retries, etc."""

    # ------------------------------------------------------------------
    # Core fields
    # ------------------------------------------------------------------
    deadline: float | None = None  # epoch seconds
    metadata: dict[str, Any] = Field(default_factory=dict)
    retry_count: int = 0
    step_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    span: Any | None = None  # OpenTelemetry span (optional)

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------
    @staticmethod
    def from_kwargs(src: dict[str, Any] | None) -> "Context":
        """Extract (or build) a **Context** from a kwargs dict.

        * If `_ctx` **or** `ctx` holds a *Context* object, return it.
        * Consumes `timeout` (seconds) -> absolute `deadline`.
        * Copies remaining **non-private** keys (not starting with "_") into
          `metadata` so they propagate through the graph.
        * Pops the consumed keys from *src* so they won't reach user
          `forward()` signatures.
        """
        if src is None:
            return Context()
        if not isinstance(src, dict):
            raise TypeError("from_kwargs expects a dict or None")

        # 1. Explicit Context supplied?
        for key in ("_ctx", "ctx"):
            obj = src.get(key)
            if isinstance(obj, Context):
                src.pop(key)
                return obj

        # 2. Deadline from timeout
        timeout = src.pop("timeout", None)
        deadline = time.time() + timeout if timeout else None

        # 3. Capture non-private kwargs as metadata
        meta: dict[str, Any] = {k: v for k, v in list(src.items()) if not k.startswith("_")}
        # Remove copied keys so they don't leak to downstream Modules
        for k in meta.keys():
            src.pop(k, None)

        return Context(deadline=deadline, metadata=meta)
