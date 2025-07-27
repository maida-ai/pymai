import contextvars
import inspect
from typing import Any, Self

import anyio

from mai.types import Context

_current_ctx: contextvars.ContextVar[Context] = contextvars.ContextVar("_current_ctx")


class Module:
    def __new__(cls, *args: Any, **kwargs: Any) -> Self:
        instance = super().__new__(cls)
        instance._static_cfg = {}
        return instance

    def __init__(self, *args: Any, **kwargs: Any):
        # We need init to avoid mypy complaining about _static_cfg being undefined
        # Practically, it is defined in __new__
        self._static_cfg: dict[str, Any] = {}

    def with_(self, **cfg: Any) -> Self:
        """Attach static config overrides (timeout, threshold, etc.)."""
        self._static_cfg |= cfg
        return self

    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        # merge static + call-time settings
        kwargs = {**self._static_cfg, **kwargs}
        ctx_token = _current_ctx.set(Context.from_kwargs(kwargs))
        try:
            fn = inspect.unwrap(self.forward)
            if inspect.iscoroutinefunction(fn):
                return await fn(*args, **kwargs)
            # run sync forward in a worker thread so event loop stays responsive
            return await anyio.to_thread.run_sync(fn, *args, **kwargs)
        finally:
            _current_ctx.reset(ctx_token)

    def forward(self, *args: Any, **kwargs: Any) -> Any:
        """Override in subclasses; may be sync or async."""
        raise NotImplementedError
