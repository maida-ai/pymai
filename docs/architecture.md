# **`pymai` | Architecture Draft (UX + Workflow Vision, 2025-07-25)**

| Version | Description   | Author        |
| ------- | ------------- | ------------- |
| 0.1     | Initial Draft | Maida.AI Team |

## 1 Purpose & Scope

`pymai` is a **tiny-yet-powerful Python framework** for composing AI agents today and orchestrating **durable, distributed workflows** tomorrow. Version 0.1 ships ergonomic, in-process pipelines that feel like ordinary function calls; later milestones extend the same graphs across processes, edge devices, and clusters via a Temporal-style runtime.

## 2 Design Principles

| ID   | Principle                                 | Rationale                                                       |
| ---- | ----------------------------------------- | --------------------------------------------------------------- |
| DP-1 | **Single abstraction** -- unified `Module` | One class to learn.                                             |
| DP-2 | **Sync/Async auto-detection**             | Author plain Python; runtime off-loads blockers to threads.     |
| DP-3 | **Type-safe, boilerplate-free I/O**       | `pydantic.TypeAdapter` auto-casts user types <-> `Payload`.      |
| DP-4 | **Invisible Context**                     | Deadlines, tracing, auth via `contextvars`; no signature noise. |
| DP-5 | **Concurrency-safe isolation**            | Parallel branches inherit but don't leak Context changes.       |
| DP-6 | **Observability first**                   | Rich `TraceHandle` + OpenTelemetry by default.                  |
| DP-7 | **Configurable Modules**                  | `.with_(**cfg)` attaches static or per-call settings.           |
| DP-8 | **Micro-kernel core**                     | Core $\leq$ 2 kLOC; heavy lifting lives in `mai/core`.               |
| DP-9 | **Durable workflows**                     | Steps replay-able, idempotent, resumable across nodes.          |

## 3 Core Abstractions

\### 3.1 `mai.layers.Module` (unified per-instance cfg)

```python
import asyncio, inspect, anyio, contextvars
from typing import Any
from mai.types import Context  # defined below

_current_ctx: contextvars.ContextVar[Context] = contextvars.ContextVar("_current_ctx")

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
        ctx = Context.from_kwargs(merged)
        token = _current_ctx.set(ctx)
        try:
            fn = inspect.unwrap(self.forward)
            if inspect.iscoroutinefunction(fn):
                return await fn(*args, **merged)
            return await anyio.to_thread.run_sync(fn, *args, **merged)
        finally:
            _current_ctx.reset(token)

    def forward(self, *args, **kwargs):
        raise NotImplementedError
```

\### 3.2 `Context` -- request-scoped & concurrency-safe
`Context` captures deadlines, trace spans, auth, retries--**one immutable instance per top-level call**. Stored in a `contextvars.ContextVar`, every async task or thread created *after* `_current_ctx.set(...)` receives **its own snapshot**, ensuring that parallel branches and delayed or conditional layers remain isolated.

```python
from __future__ import annotations
import time, uuid
from pydantic import BaseModel, Field
from typing import Any, Dict

class Context(BaseModel, frozen=True):
    """Immutable request-scoped carrier for deadlines, tracing, auth, etc."""
    deadline: float | None = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    retry_count: int = 0
    step_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    span: Any | None = None

    # ----- construction helper -------------------------------------
    @staticmethod
    def from_kwargs(src: Dict[str, Any] | None) -> "Context":
        if src is None:
            return Context()
        if not isinstance(src, dict):
            raise TypeError("from_kwargs expects dict | None")

        # explicit override
        for key in ("_ctx", "ctx"):
            ctx = src.get(key)
            if isinstance(ctx, Context):
                src.pop(key)
                return ctx

        deadline = None
        if (t := src.pop("timeout", None)) is not None:
            deadline = time.time() + t

        meta = {k: v for k, v in list(src.items()) if not k.startswith("_")}
        for k in meta:
            src.pop(k, None)

        return Context(deadline=deadline, metadata=meta)

    # immutable update helpers --------------------------------------
    def with_metadata(self, **extra) -> "Context":
        nm = {**self.metadata, **extra}
        return self.copy(update={"metadata": nm})

    def bumped_retry(self) -> "Context":
        return self.copy(update={"retry_count": self.retry_count + 1})
```

\### 3.3 `Layer` & `Payload`
*Layers* are atomic async callables; **`Payload`** is a strongly-typed envelope auto-generated from user types to ensure safe, structured data flow.

\### 3.4 `Graph` (DAG)
A declarative wrapper that turns interconnected Modules into an executable DAG--optimising chains, inserting casting layers, and emitting a **WorkflowPlan** for replay and persistence.

\### 3.5 `Engine`
Local asyncio + thread-pool scheduler powering **Sequential**, **Parallel**, **BlockingDelay**, **NonBlockingDelay**, and **Conditional** composites. Parallel branches inherit the same immutable `Context`; blocking delays pause within the same task without affecting siblings.

\### 3.6 `TraceHandle`
Per-call object exposing timings, payload sizes, and error metadata; integrates with OpenTelemetry exporters.

## 4 Developer Quick-Start

```python
from mai.layers import Module, Sequential, Parallel, BlockingDelay
from mai.types   import RawText, TokenizedText, Embedding
from mai.models  import Tokenizer, EmbeddingModel
from mai.metrics import Metric

# --- Atomic Modules --------------------------------------------------
class Tokenize(Module):
    def __init__(self, tok: Tokenizer):
        super().__init__(); self.tok = tok
    def forward(self, text: RawText) -> TokenizedText:
        return self.tok.tokenize(text)

class Embed(Module):
    def __init__(self, model: EmbeddingModel):
        super().__init__(); self.model = model
    def forward(self, tokens: TokenizedText) -> Embedding:
        return self.model.embed(tokens)

class Agent1(Module):
    def __init__(self, metric: Metric):
        super().__init__(); self.metric = metric
    async def forward(self, embedding: Embedding) -> float:
        # imagine a remote call
        return self.metric.compute(embedding)

class Agent2(Module):
    def __init__(self, metric: Metric):
        super().__init__(); self.metric = metric
    def forward(self, embedding: Embedding) -> float:
        return self.metric.compute(embedding)

class Aggregate(Module):
    def forward(self, *scores: float) -> float:
        return sum(scores) / len(scores)

class Humanize(Module):
    def __init__(self, threshold: float = 0.8):
        super().__init__(); self.threshold = threshold
    def forward(self, score: float) -> str:
        return f"Similarity score is {'high' if score >= self.threshold else 'low'} ({score:.2f})"

# --- Pipeline --------------------------------------------------------

pipeline = Sequential(
    Tokenize(tokenizer),
    Embed(embedding_model),
    Parallel(
        Agent1(sim_metric).with_(timeout=0.5),
        Agent2(sim_metric).with_(timeout=0.3)
    ),
    Aggregate(),
    BlockingDelay(seconds=0.1),
    Humanize().with_(threshold=0.75)
).with_(timeout=1.0)

result = await pipeline(text=["hello world", "Hello, world!"])
print(result)
```

*Highlights*

* **Parallel** executes `Agent1` and `Agent2` concurrently with isolated Context snapshots.
* **BlockingDelay** pauses the pipeline without leaking state between tasks.
* User code remains clean; all deadlines and tracing data ride the hidden `Context`.

## 5 Execution Model

1. **Build phase** -- instantiate Modules/Layers or load a YAML spec -> produces a `Graph`.
2. **Compile phase** -- optimiser folds trivial chains, inserts casting and async boundaries, emits a **WorkflowPlan**.
3. **Run phase (local)** -- `Engine` drives asyncio and threads; Context deadlines enforced; Parallel branches inherit immutable Context.
4. **Run phase (distributed, future)** -- WorkflowPlan executed by Temporal-lite runtime with durable state, retries, and remote executors.
5. **Trace export** -- spans and logs emitted via OTLP JSON.

## 6 Folder Structure

```
mai/
 ├─ layers/        # Atomic Layers + unified Module
 ├─ core/          # Optimised back-ends & runtime (Parallel, Delay, etc.)
 ├─ types/         # Strongly-typed data (Context, Payload...)
 ├─ models/        # Model wrappers (tokenizers, embedders...)
 ├─ metrics/       # Metric Modules
 ├─ contrib/       # Community bridges
 └─ third-party/   # Vendored sub-modules (e.g., XCP)
```

## 7 Roadmap

| Milestone | Target                                         | ETA            |
| --------- | ---------------------------------------------- | -------------- |
| **M-0**   | Core abstractions, Parallel & Delay primitives | **Aug 05 '25** |
| **M-1**   | Graph optimiser + YAML loader                  | **Sep 10 '25** |
| **M-2**   | XCP transport adapter                          | **Oct 30 '25** |
| **M-3**   | Quantised micro-models                         | **Nov 30 '25** |
| **M-4**   | Distributed Workflow Engine                    | **Jan 31 '26** |

## 8 Open Questions

1. **Aggregation API** -- unify `axis` + optional `aggregate` callable?
2. **Thread-pool strategy** -- per-Module vs global executors?
3. **Persistence format** -- SQLite vs RocksDB for workflow history?
4. **Security** -- sandbox untrusted Modules once remote.
5. **Rust kernel feasibility** -- benchmark sub-10 ms latency loop.
