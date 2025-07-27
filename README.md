# pymai

**Tiny-yet-powerful Python framework for composable AI agents and durable workflows.**


## ✨ Key Features

* **Unified `Module` abstraction** -- located in `mai.layers`; write `forward()` once (sync **or** async) and chain Modules like plain functions.
* **Invisible Context** -- deadlines, tracing, auth, and per-request overrides propagate via `contextvars`; no boilerplate parameters.
* **Zero-copy I/O** -- user dataclasses/Pydantic models auto-cast to internal `Payload` envelopes.
* **Observability-first** -- OpenTelemetry spans and rich error metadata out of the box.
* **Workflow-ready** -- roadmap includes a Temporal-style engine for retries, checkpoints, and distributed execution.
* **Backend agility** -- high-performance kernels in Cython, Rust, or C++ live under `mai/core`, swap in without touching business logic.


## 🚀 Quick Start

```bash
# 1. Install (editable mode for hacking)
$ git clone https://github.com/maida-ai/pymai
$ cd pymai && pip install -e .[dev]

# 2. Run the toy pipeline demo
$ python examples/similarity_demo.py
```

### Example Snippet

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
    def __init__(self, metric: Metric):
        super().__init__(); self.metric = metric
    def forward(self, a: Embedding, b: Embedding) -> float:
        return self.metric.compute(a, b)

pipeline = Sequential(Tokenize(tok), Embed(embedder), Similarity(sim))
score = await pipeline(text=["hello world", "Hello, world!"])
print(score)
```

*Notice*: no explicit Context object--timeouts, tracing, and overrides ride an internal `Context` created automatically.


## 🏗️ Folder Structure

```
mai/
 ├─ layers/        # Atomic Layers + unified Module (torch/nn analogue)
 ├─ core/          # Optimised back-ends (Cython/Rust/C++), runtime engine & tracing
 ├─ types/         # Strongly-typed data definitions & adapters
 ├─ models/        # High-level model wrappers (tokenisers, embedders...)
 ├─ metrics/       # Metric Modules (similarity, classification metrics...)
 ├─ contrib/       # Community bridges (LangChain, OpenAI, etc.)
 └─ third-party/   # Vendored sub-modules (e.g., XCP transport)
```


## 📅 Roadmap

| Version | Highlights                                                                 | Target   |
| ------- | -------------------------------------------------------------------------- | -------- |
| **0.1** | Core abstractions (`mai.layers`), local Engine (`mai.core`), demo pipeline | Aug 2025 |
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
