import asyncio, inspect, anyio, contextvars
_current_ctx = contextvars.ContextVar("_current_ctx")

class Module:
    _static_cfg: dict[str, object] = {}
    def with_(self, **cfg):
        self._static_cfg |= cfg
        return self

    async def __call__(self, *args, **kwargs):
        kwargs = {**self._static_cfg, **kwargs}
        ctx_token = _current_ctx.set(Context.from_kwargs(kwargs.pop("_ctx", None)))
        try:
            fn = inspect.unwrap(self.forward)
            if inspect.iscoroutinefunction(fn):
                return await fn(*args, **kwargs)
            return await anyio.to_thread.run_sync(fn, *args, **kwargs)
        finally:
            _current_ctx.reset(ctx_token)

    def forward(self, *args, **kwargs):
        raise NotImplementedError
