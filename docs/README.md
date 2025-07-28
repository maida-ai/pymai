# pymai Documentation

This directory contains the Sphinx documentation for the pymai project.

## Local Development

### Prerequisites

Make sure you have the development dependencies installed:

```bash
poetry install --with dev
```

### Building Documentation

To build the documentation locally:

```bash
cd docs
make html
```

The built documentation will be available in `_build/html/`.

### Serving Documentation Locally

To serve the documentation locally for preview:

```bash
cd docs
make serve
```

This will start a local server at http://localhost:8000.

### Cleaning Build Artifacts

To clean build artifacts:

```bash
cd docs
make clean
```

## GitHub Actions

The documentation is automatically built and deployed to GitHub Pages via the `.github/workflows/sphinx-docs.yml` workflow.

The workflow:
1. Triggers on pushes to `main` and `develop` branches
2. Sets up Python 3.11 and Poetry
3. Installs dependencies including Sphinx
4. Generates API documentation from docstrings
5. Builds the documentation
6. Deploys to GitHub Pages (only on `main` branch)

## Documentation Structure

- `conf.py` - Sphinx configuration
- `index.rst` - Main documentation entry point
- `modules.rst` - API reference documentation
- `architecture.rst` - Architecture documentation (converted from markdown)

## Adding Documentation

### Adding New Modules

To document new modules, add them to `modules.rst`:

```rst
.. automodule:: mai.new_module
   :members:
   :undoc-members:
   :show-inheritance:
```

### Writing Docstrings

Follow Google-style docstrings for best compatibility with Sphinx:

```python
def my_function(param1: str, param2: int) -> bool:
    """Short description of the function.

    Longer description if needed.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ValueError: When something goes wrong
    """
    pass
```

### Type Hints

Always use type hints in your code as they will be automatically included in the documentation.
