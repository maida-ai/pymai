# **`pymai` | Architecture Draft (UX + Workflow Vision, 2025‑07‑25)**

| Version | Description   | Author        |
| ------- | ------------- | ------------- |
| 0.1     | Initial Draft | Maida.AI Team |

## 1 Purpose & Scope
`pymai` is a **tiny‑yet‑powerful Python framework** for composing AI agents today and orchestrating **durable, distributed workflows** tomorrow.
Version 0.1 focuses on ergonomic, in‑process pipelines that feel like ordinary function calls. Later milestones extend the identical graphs across processes, edge devices, and clusters via a Temporal‑style runtime.

Key qualities

* **Minimal onboarding** – subclass one `Module`, implement `forward()` (sync *or* async), chain Modules like Python functions.
* **Durable workflows** – automatic retries, back‑off, checkpoints (road‑mapped).
* **Backend agnostic** – swap in‑process calls for XCP RPC without touching business logic.


## 2 Design Principles

| ID       | Principle                                 | Rationale                                                         |
| -------- | ----------------------------------------- | ----------------------------------------------------------------- |
| **DP‑1** | **Single abstraction** – unified `Module` | One class to learn.                                               |
| **DP‑2** | **Sync/Async auto‑detection**             | Author plain Python; runtime off‑loads blockers to threads.       |
| **DP‑3** | **Type‑safe, boilerplate‑free I/O**       | `pydantic.TypeAdapter` auto‑casts user types ←→ `Payload`.        |
| **DP‑4** | **Invisible Context via `contextvars`**   | Deadlines, auth, tracing without polluting every signature.       |
| **DP‑5** | **Observability first**                   | Rich `TraceHandle` + OpenTelemetry by default.                    |
| **DP‑6** | **Configurable Modules**                  | `.with_(**cfg)` attaches static or per‑call settings.             |
| **DP‑7** | **Micro‑kernel core**                     | Core ≤ 2 kLOC; heavy lifting lives in back‑ends under `mai/core`. |
| **DP‑8** | **Durable workflows**                     | Steps replay‑able, resumable, idempotent across nodes.            |


## 3 Core Abstractions
### 3.1 `mai.layers.Module` (unified)

```python
import asyncio, inspect, anyio, contextvars
_current_ctx = contextvars.ContextVar("_current_ctx")

class Module:
    _static_cfg: dict[str, object] = {}

    # attach static overrides → obj.with_(timeout=1.0)
    def with_(self, **cfg):
        self._static_cfg |= cfg; return self

    async def __call__(self, *args, **kwargs):
        # merge static & call‑time config
        kwargs = {**self._static_cfg, **kwargs}
        ctx_token = _current_ctx.set(Context.from_kwargs(kwargs.pop("_ctx", None)))
        try:
            fn = inspect.unwrap(self.forward)
            if inspect.iscoroutinefunction(fn):
                return await fn(*args, **kwargs)
            # run sync work in a thread to keep the event loop responsive
            return await anyio.to_thread.run_sync(fn, *args, **kwargs)
        finally:
            _current_ctx.reset(ctx_token)

    def forward(self, *args, **kwargs):
        """Override in subclasses; may be sync or async."""
        raise NotImplementedError
```

### 3.2 `Layer`, `Payload`
*Layers* are atomic async callables; `Payload` is a strongly‑typed envelope auto‑generated from user types.

### 3.3 `Graph`
Declarative DAG around interconnected Modules; optimiser folds trivial chains, inserts casting layers, and later emits **WorkflowPlans**.

### 3.4 `Engine`
Local asyncio + thread‑pool scheduler (v0.1). Road‑map: pluggable **WorkflowRuntime** providing persistence, retries, and distributed execution.

### 3.5 `TraceHandle`
Per‑call object exposing start/stop time, payload sizes, error metadata; integrates with OTLP exporters.

### 3.6 **Why `Context` Matters**
`Context` is the request‑scoped object created inside `__call__` and stored in the `_current_ctx` variable.
It is **not** required by `asyncio`; instead it carries cross‑cutting concerns that make agent graphs production‑grade:

| Concern                  | Delivered by `Context`                                                | Example                                                     |
| ------------------------ | --------------------------------------------------------------------- | ----------------------------------------------------------- |
| Deadlines & cancellation | `ctx.deadline` lets deep layers short‑circuit before global timeout.  | A tokeniser aborts early when only 20 ms remain.            |
| Tracing & metrics        | `ctx.span` used by every Module to add nested OpenTelemetry spans.    | Logs and metrics align across an entire workflow.           |
| Retries / back‑off       | `ctx.retry_count`, `ctx.step_id` enable deterministic replay.         | Workflow step checks that it hasn’t emailed the user twice. |
| Auth, locale, tenancy    | `ctx.tenant_id`, `ctx.jwt` propagate without leaking into signatures. | Downstream store picks correct bucket.                      |
| Override knobs           | Values set via `.with_(threshold=0.8)` travel automatically.          | `Humanize` Module receives `threshold` five hops later.     |

Developers **see `Context` only if they ask for it**:

```python
from mai import get_current_context
ctx = get_current_context()
```

or by adding it to `forward(self, ctx: Context, ...)`.


## 4 Developer Quick‑Start

```python
from mai.layers import Module, Sequential
from mai.types   import RawText, TokenizedText, Embedding
from mai.models  import Tokenizer, EmbeddingModel
from mai.metrics import Metric

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

class Similarity(Module):
    def __init__(self, metric: Metric, axis: int = 0):
        super().__init__(); self.metric = metric; self.axis = axis
    def forward(self, *embeddings: Embedding) -> float:
        return self.metric.compute(*embeddings, axis=self.axis)

class Humanize(Module):
    def __init__(self, metric: Metric, template: str | None = None):
        super().__init__(); self.metric = metric; self.template = template
    def forward(self, score: float, over_threshold: bool) -> str:
        return self.metric.explain(score, template=self.template, over_threshold=over_threshold)

similarity_pipeline = Sequential(
    Tokenize(tokenizer),
    Embed(embedding_model),
    Similarity(similarity_metric, axis=1),
    Humanize(similarity_metric,
             template=r"Similarity score is {'close' if {over_threshold} else 'not close'} ({score=})")
).with_(timeout=1.0, threshold=0.8)

result = await similarity_pipeline(text=["hello world", "Hello, world!"])
```

*No explicit `Context`; the pipeline remains ordinary Python code.*


## 5 Execution Model

1. **Build** – instantiate Modules/Layers ⇒ optional YAML spec ⇒ `Graph`.
2. **Compile** – optimiser folds chains, inserts casting & async boundaries; emits **WorkflowPlan**.
3. **Run (local)** – `Engine` schedules coroutines & threads, enforces deadlines.
4. **Run (distributed)** – WorkflowPlan submitted to Temporal‑lite runtime; steps persisted, retried, executed near data.
5. **Trace export** – spans/logs via OTLP JSON; future: step history replay.


## 6 Package Layout (after folder revision)

```
mai/
 ├─ layers/        # Atomic Layers + unified Module (torch/nn analogue)
 ├─ core/          # Optimised back‑ends (Cython/Rust/Scala/C++), runtime engine, tracing
 ├─ types/         # Strongly‑typed data classes & adapters
 ├─ models/        # High‑level model wrappers (tokenisers, embedder layers, etc.)
 ├─ metrics/       # Metric Modules (similarity, classification metrics…)
 ├─ contrib/       # Community bridges (LangChain, OpenAI, etc.)
 └─ third‑party/   # Vendored sub‑modules (e.g., XCP)
```

*Note*: The local runtime lives under **`mai/core/runtime`**; future XCP transport will reside in `third‑party/xcp` until promoted.


## 7 Roadmap

| Milestone | Target                                                                       | ETA            |
| --------- | ---------------------------------------------------------------------------- | -------------- |
| **M‑0**   | Core abstractions in `mai.layers`, local Engine in `mai.core`, demo pipeline | **Aug 05 ’25** |
| **M‑1**   | `Graph` optimiser + YAML loader                                              | **Sep 10 ’25** |
| **M‑2**   | XCP transport adapter in `third‑party/xcp`                                   | **Oct 30 ’25** |
| **M‑3**   | Quantised micro‑model library in `mai.models`                                | **Nov 30 ’25** |
| **M‑4**   | **Distributed Workflow Engine** (Temporal‑lite) in `mai.core.workflow`       | **Jan 31 ’26** |


## 8 Open Questions

1. **Aggregation API** – unify `axis` + optional `aggregate` callable?
2. **Thread‑pool strategy** – per‑Module vs global executors?
3. **Persistence format** – SQLite vs RocksDB for Workflow history?
4. **Security** – sandbox untrusted Modules once remote.
5. **Rust kernel feasibility** – benchmark sub‑10 ms latency loop.
