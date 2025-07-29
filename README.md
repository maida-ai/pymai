[![codecov](https://codecov.io/github/maida-ai/pymai/graph/badge.svg?token=ORFLBUT5HP)](https://codecov.io/github/maida-ai/pymai)
[![unittests](https://github.com/maida-ai/pymai/actions/workflows/tests.yml/badge.svg)](https://github.com/maida-ai/pymai/actions/workflows/tests.yml)
[![documentation](https://github.com/maida-ai/pymai/actions/workflows/sphinx-docs.yml/badge.svg)](https://github.com/maida-ai/pymai/actions/workflows/sphinx-docs.yml)


# pymai

**Tiny-yet-powerful Python framework for composable AI agents and durable workflows.**


## ✨ Key Features

* **Unified `Module` abstraction** -- located in `mai.layers`; write `forward()` once (sync **or** async) and chain Modules like plain functions.
* **Invisible Context** -- deadlines, tracing, auth, and per-request overrides propagate via `contextvars`; no boilerplate parameters.
* **Composite Modules** -- `Sequential`, `Parallel`, `Conditional`, `Delay`, `Retry` for complex workflows without Engine API exposure.
* **Zero-copy I/O** -- user dataclasses/Pydantic models auto-cast to internal `Payload` envelopes.
* **Observability-first** -- OpenTelemetry spans and rich error metadata out of the box.
* **Workflow-ready** -- roadmap includes a Temporal-style engine for retries, checkpoints, and distributed execution.
* **Backend agility** -- high-performance kernels in Cython, Rust, or C++ live under `mai/core`, swap in without touching business logic.


## 🚀 Quick Start

```bash
# 1. Install (editable mode for hacking)
$ git clone https://github.com/maida-ai/pymai
$ cd pymai && pip install -e .[dev]

# 2. Run the invisible execution demo
$ python examples/invisible_execution_demo.py
```

### Example Snippet

```python
from mai.layers import Module, Sequential, Parallel, Conditional, Retry
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
    def __init__(self, metric: Metric):
        super().__init__(); self.metric = metric
    def forward(self, a: Embedding, b: Embedding) -> float:
        return self.metric.compute(a, b)

# Complex workflow with invisible execution
pipeline = Sequential(
    Tokenize(tok),
    Embed(embedder),
    Parallel(
        Retry(Similarity(sim_metric), max_retries=2).with_(timeout=5.0),
        Retry(Similarity(sim_metric), max_retries=2).with_(timeout=3.0)
    ),
    Conditional(
        condition=lambda score: score > 0.7,
        true_module=lambda score: f"High similarity: {score:.2f}",
        false_module=lambda score: f"Low similarity: {score:.2f}"
    )
)

score = await pipeline(text=["hello world", "Hello, world!"])
print(score)
```

*Notice*: no explicit Engine API--timeouts, tracing, and overrides ride an internal `Context` created automatically.


## 🏗️ Folder Structure

```
mai/
 ├─ layers/        # Atomic Layers + unified Module + Composite Modules
 ├─ core/          # Optimised back-ends (Cython/Rust/C++), invisible execution
 ├─ types/         # Strongly-typed data definitions & adapters
 ├─ models/        # High-level model wrappers (tokenisers, embedders...)
 ├─ metrics/       # Metric Modules (similarity, classification metrics...)
 ├─ contrib/       # Community bridges (LangChain, OpenAI, etc.)
 └─ third-party/   # Vendored sub-modules (e.g., XCP transport)
```


## 📅 Roadmap

| Version | Highlights                                                                 | Target   |
| ------- | -------------------------------------------------------------------------- | -------- |
| **0.1** | Core abstractions (`mai.layers`), Composite modules, invisible execution | Aug 2025 |
| 0.2     | `Graph` optimiser + YAML loader                                            | Sep 2025 |
| 0.3     | XCP transport adapter                                                      | Oct 2025 |
| 0.4     | Quantised micro-model library                                              | Nov 2025 |
| 0.5     | **Distributed Workflow Engine**                                            | Jan 2026 |


## 🤝 Contributing

Pull requests are welcome! Please read **CONTRIBUTING.md** for linting rules, branch strategy, and CLA.

### Dev Environment

```bash
pip install -e .[dev]
pre-commit install  # black, ruff, mypy
pytest -q           # run unit tests
```


## 📄 License

Apache 2.0 -- see `LICENSE` for details.

---

> Made with ♥ by the **Maida.AI Team**
