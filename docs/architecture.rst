.. _architecture:

Architecture
============

**pymai** | Architecture Draft (UX + Workflow Vision, 2025-07-25)

+----------+-------------+----------------+
| Version  | Description | Author         |
+----------+-------------+----------------+
| 0.1      | Initial Draft | Maida.AI Team |
+----------+-------------+----------------+

Purpose & Scope
---------------

**pymai** is a **tiny-yet-powerful Python framework** for composing AI agents today and orchestrating **durable, distributed workflows** tomorrow. Version 0.1 ships ergonomic, in-process pipelines that feel like ordinary function calls; later milestones extend the same graphs across processes, edge devices, and clusters via a Temporal-style runtime.

Design Principles
-----------------

+----+----------------------------------------+---------------------------------------------------------------+
| ID | Principle                              | Rationale                                                     |
+----+----------------------------------------+---------------------------------------------------------------+
| DP-1 | **Single abstraction** -- unified `Module` | One class to learn.                                           |
| DP-2 | **Sync/Async auto-detection**             | Author plain Python; runtime off-loads blockers to threads.   |
| DP-3 | **Type-safe, boilerplate-free I/O**       | `pydantic.TypeAdapter` auto-casts user types <-> `Payload`.   |
| DP-4 | **Invisible Context**                     | Deadlines, tracing, auth via `contextvars`; no signature noise. |
| DP-5 | **Concurrency-safe isolation**            | Parallel branches inherit but don't leak Context changes.     |
| DP-6 | **Observability first**                   | Rich `TraceHandle` + OpenTelemetry by default.                |
| DP-7 | **Configurable Modules**                  | `.with_(**cfg)` attaches static or per-call settings.         |
| DP-8 | **Micro-kernel core**                     | Core ≤ 2 kLOC; heavy lifting lives in `mai/core`.            |
| DP-9 | **Durable workflows**                     | Steps replay-able, idempotent, resumable across nodes.        |
+----+----------------------------------------+---------------------------------------------------------------+

Core Abstractions
-----------------

mai.layers.Module (unified per-instance cfg)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import asyncio, inspect, anyio
    from typing import Any
    from mai.types import Context  # defined below

    class Module:
        """Base class for every *pymai* layer."""

        def __init__(self) -> None:
            # per-instance defaults (timeout, threshold, etc.)
            self._static_cfg: dict[str, Any] = {}

        def with_(self, **cfg):
            """Attach defaults; chainable."""
            self._static_cfg.update(cfg)
            return self

        async def __call__(self, *args, **kwargs):
            merged = {**self._static_cfg, **kwargs}
            token = Context.set(**merged)
            try:
                fn = inspect.unwrap(self.forward)
                if inspect.iscoroutinefunction(fn):
                    return await fn(*args, **merged)
                return await anyio.to_thread.run_sync(fn, *args, **merged)
            finally:
                Context.reset(token)

        def forward(self, *args, **kwargs):
            raise NotImplementedError

Context -- request-scoped & concurrency-safe
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`Context` captures deadlines, trace spans, auth, retries--**one instance per top-level call**. Stored in a `contextvars.ContextVar`, every async task or thread created *after* `Context.set(...)` receives **its own snapshot**, ensuring that parallel branches and delayed or conditional layers remain isolated.

**Key features:**
- **Deadlines** must be specified in monotonic time (not wall clock time)
- **Metadata** propagation for request-scoped data
- **Retry tracking** and **step identification**
- **OpenTelemetry span** integration
- **Context management** via `Context.set()`, `Context.get()`, `Context.reset()`

.. code-block:: python

    class Context(pydantic.BaseModel):
        """Request-scoped carrier for deadlines, tracing, auth, retries, etc."""

        deadline: float | None = None  # monotonic time only
        metadata: dict[str, Any] = pydantic.Field(default_factory=dict)
        retry_count: int = 0
        step_id: str = pydantic.Field(default_factory=lambda: uuid.uuid4().hex)
        span: Any | None = None  # OpenTelemetry span (optional)

        @classmethod
        def set(cls, **kwargs: Any) -> Token: ...
        @classmethod
        def get(cls) -> "Context": ...
        @classmethod
        def reset(cls, token: Token) -> None: ...

Layer & Payload
~~~~~~~~~~~~~~~

*Layers* are atomic async callables; **`Payload`** is a strongly-typed envelope auto-generated from user types to ensure safe, structured data flow.

Graph (DAG)
~~~~~~~~~~~

A declarative wrapper that turns interconnected Modules into an executable DAG--optimising chains, inserting casting layers, and emitting a **WorkflowPlan** for replay and persistence.

Engine
~~~~~~

Local asyncio + thread-pool scheduler powering **Sequential**, **Parallel**, **BlockingDelay**, **NonBlockingDelay**, and **Conditional** composites. Parallel branches inherit the same `Context`; blocking delays pause within the same task without affecting siblings.

TraceHandle
~~~~~~~~~~~

Per-call object exposing timings, payload sizes, and error metadata; integrates with OpenTelemetry exporters.
