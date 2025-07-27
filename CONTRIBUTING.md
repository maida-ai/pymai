# Contributing to pymai

Thank you for your interest in contributing to **pymai**! This document provides guidelines and instructions for contributing to the project.

## 🎯 Project Vision

**pymai** is a tiny-yet-powerful Python framework for composable AI agents and durable workflows. We aim to provide:

- **PyTorch-like modularity** - Drop-in layers that compose naturally
- **Strongly-typed I/O** - Pydantic-based data transfer with "Know your types; Fail if unsure" principle
- **Zero boilerplate** - Write `forward()` once (sync or async), chain like functions
- **Production-ready** - Built-in observability, context propagation, and durability
- **Backend agnostic** - Swap implementations without touching business logic

## 🚀 Quick Start

### Development Setup

```bash
# Clone the repository
git clone https://github.com/maida-ai/pymai.git
cd pymai

# Install in editable mode with dev dependencies
pip install -e .[dev]

# Install pre-commit hooks
pre-commit install

# Verify setup
pytest -q
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=mai --cov-report=html

# Run specific test file
pytest tests/test_layers.py

# Run benchmarks (if any)
PYTHONPATH=. python benchmarks/poc_*.py
```

## 📝 Code Style & Standards

### Python Style Guide

We follow **PEP 8** with these specific rules:

- **Line length**: 120 characters (modern screen-friendly)
- **Import sorting**: isort with Black compatibility
- **Type hints**: Required for all public APIs
- **Docstrings**: Google style for all public methods
- **String formatting**: f-strings preferred over .format() or %
- **Path handling**: pathlib.Path over os.path
- **Type annotations**: Use | for union types (Python 3.10+)

### Tools & Configuration

Our code quality is enforced by:

- **Black** - Code formatting
- **Ruff** - Fast linting and import sorting
- **MyPy** - Static type checking
- **Pre-commit** - Automated checks on commit

### Running Code Quality Checks

```bash
# Format code
black mai/ tests/ examples/

# Lint code
ruff check mai/ tests/ examples/

# Type check
mypy mai/

# Run all checks
pre-commit run --all-files
```

### Modern Development Workflow

```bash
# Watch files for changes (auto-run tests)
watchmedo auto-restart --patterns="*.py" --recursive -- pytest -f

# Rich terminal output for better readability
python -m rich.console

# Type checking with better error messages
mypy mai/ --show-error-codes --pretty
```

## 🏗️ Architecture Principles

### Core Design Principles

1. **DP-1: Single abstraction** - Unified `Module` class
2. **DP-2: Sync/Async auto-detection** - Runtime handles blocking operations
3. **DP-3: Type-safe I/O** - Pydantic adapters for zero-copy data flow with "Know your types; Fail if unsure" principle
4. **DP-4: Invisible Context** - `contextvars` for cross-cutting concerns
5. **DP-5: Observability first** - Rich tracing and metrics by default
6. **DP-6: Configurable Modules** - `.with_(**cfg)` for static overrides
7. **DP-7: Micro-kernel core** - Core $\leq$ 2kLOC, heavy lifting in backends
8. **DP-8: Durable workflows** - Replay-able, resumable, idempotent steps

### Module Development Guidelines

When creating new Modules:

```python
from mai.layers import Module
from mai.types import InputType, OutputType  # Strongly typed Pydantic models
from pydantic import BaseModel

class InputType(BaseModel):
    """Strongly typed input specification."""
    text: str
    max_length: int = 100

class OutputType(BaseModel):
    """Strongly typed output specification."""
    processed_text: str
    word_count: int
    confidence: float

class MyModule(Module):
    """Brief description of what this module does.

    Longer description if needed, explaining the module's purpose,
    inputs, outputs, and any important implementation details.
    """

    def __init__(self, param1: str, param2: int = 42):
        """Initialize the module with configuration.

        Args:
            param1: Description of parameter 1
            param2: Description of parameter 2, defaults to 42
        """
        super().__init__()
        self.param1 = param1
        self.param2 = param2

    def forward(self, input_data: InputType) -> OutputType:
        """Process the input and return the result.

        Args:
            input_data: Strongly typed input with validation

        Returns:
            Strongly typed output with validation

        Raises:
            ValueError: When input validation fails
        """
        # Implementation here - types are guaranteed by Pydantic
        return OutputType(
            processed_text=f"{input_data.text[:input_data.max_length]}",
            word_count=len(input_data.text.split()),
            confidence=0.95
        )
```

### Testing Guidelines

- **Unit tests**: Required for all new functionality
- **Type validation tests**: Ensure Pydantic models work correctly
- **Integration tests**: For complex workflows and edge cases
- **Edge case testing**: Test invalid inputs and type mismatches
- **Benchmarks**: For performance-critical components
- **Test coverage**: Aim for >90% coverage on new code

```python
import pytest
from mai.layers import Module

class TestMyModule:
    """Test suite for MyModule."""

    def test_initialization(self):
        """Test module initialization with various parameters."""
        module = MyModule("test", 123)
        assert module.param1 == "test"
        assert module.param2 == 123

    def test_forward_sync(self):
        """Test synchronous forward pass."""
        module = MyModule("test")
        result = module.forward("input")
        assert result == "expected_output"

    @pytest.mark.asyncio
    async def test_forward_async(self):
        """Test asynchronous forward pass."""
        module = MyModule("test")
        result = await module("input")
        assert result == "expected_output"

    def test_type_validation(self):
        """Test Pydantic type validation."""
        module = MyModule("test")

        # Test valid input
        valid_input = InputType(text="Hello world", max_length=50)
        result = module.forward(valid_input)
        assert isinstance(result, OutputType)

        # Test invalid input (should raise validation error)
        with pytest.raises(ValueError):
            invalid_input = InputType(text="", max_length=-1)  # Invalid max_length
            module.forward(invalid_input)
```

## 🔒 Strong Typing Principles

### "Know your types; Fail if unsure"

**pymai** enforces a strict typing discipline to ensure data integrity and catch errors early:

#### Core Principles

1. **Explicit Type Definitions**: All module inputs and outputs must be defined as Pydantic models
2. **Runtime Validation**: Pydantic validates all data at runtime, failing fast on type mismatches
3. **Zero Ambiguity**: No `Any` types in public APIs - every type must be explicit
4. **Type Safety**: Compile-time and runtime type checking for all data flows

#### Best Practices

- **Define Pydantic models** for all data structures passed between modules
- **Use field validators** to enforce business rules and constraints
- **Leverage type hints** throughout the codebase for better IDE support
- **Test type validation** explicitly to ensure models work as expected

#### Common Patterns

```python
from pydantic import BaseModel, Field, validator

class TextInput(BaseModel):
    """Strongly typed text input with validation."""
    text: str = Field(..., min_length=1, max_length=1000)
    language: str = Field(default="en", regex="^[a-z]{2}$")

    @validator('text')
    def validate_text(cls, v):
        if not v.strip():
            raise ValueError("Text cannot be empty or whitespace only")
        return v.strip()

class TextOutput(BaseModel):
    """Strongly typed text output."""
    processed_text: str
    word_count: int = Field(ge=0)
    confidence: float = Field(ge=0.0, le=1.0)
    metadata: dict = Field(default_factory=dict)
```

#### Type Safety Benefits

- **Early Error Detection**: Catch type mismatches before they cause runtime failures
- **Self-Documenting Code**: Types serve as living documentation
- **IDE Support**: Better autocomplete, refactoring, and error detection
- **Refactoring Safety**: Changes to types are caught by the type system
- **API Contracts**: Clear contracts between modules and components

## 🔄 Development Workflow

### Branch Strategy

- **main**: Production-ready code
- **develop**: Integration branch for features
- **feature/***: New features and enhancements
- **fix/***: Bug fixes
- **docs/***: Documentation updates

### Commit Message Format

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): description

[optional body]

[optional footer]
```

Examples:
- `feat(layers): add new Transformer module`
- `fix(core): resolve memory leak in async execution`
- `docs(readme): update installation instructions`
- `test(metrics): add comprehensive test coverage`

### Pull Request Process

1. **Create feature branch** from `develop`
2. **Write tests** for new functionality
3. **Update documentation** if needed
4. **Run all checks** locally
5. **Submit PR** with clear description
6. **Address review feedback**
7. **Merge** after approval

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
```

## 🐛 Bug Reports

When reporting bugs, please include:

1. **Environment details**: Python version, OS, dependencies
2. **Reproduction steps**: Clear, minimal example
3. **Expected vs actual behavior**
4. **Error messages and stack traces**
5. **Minimal working example** (if possible)

## 💡 Feature Requests

For feature requests:

1. **Clear problem statement** - What are you trying to solve?
2. **Proposed solution** - How should it work?
3. **Use cases** - Who benefits and how?
4. **Implementation ideas** - Any technical considerations?

## 📚 Documentation

### Writing Documentation

- **API docs**: Use Google-style docstrings
- **Examples**: Include working code snippets
- **Architecture**: Update `docs/architecture.md` for design changes
- **Tutorials**: Add to `examples/` directory

### Documentation Structure

```
docs/
├── architecture.md      # System design and principles
├── api/                 # API reference
├── tutorials/           # Step-by-step guides
└── examples/            # Working code examples
```

## 🏆 Recognition

Contributors will be recognized in:

- **README.md** - For significant contributions
- **Release notes** - For each release
- **Contributors list** - In project documentation

## 📞 Getting Help

- **Issues**: Use GitHub issues for bugs and feature requests
- **Discussions**: Use GitHub discussions for questions and ideas
- **Email**: Contact the maintainers for sensitive matters

## 📄 License

By contributing to pymai, you agree that your contributions will be licensed under the Apache 2.0 License.

---

Thank you for contributing to **pymai**! 🚀
