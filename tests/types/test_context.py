"""Tests for the Context class."""

import time
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from mai.types.context import Context


class TestContextCreation:
    """Test Context object creation and basic properties."""

    def test_default_context(self):
        """Test creating a Context with default values."""
        ctx = Context()
        assert ctx.deadline is None
        assert ctx.metadata == {}
        assert ctx.retry_count == 0
        assert isinstance(ctx.step_id, str)
        assert len(ctx.step_id) > 0
        assert ctx.span is None

    def test_validate_deadline(self):
        """Test that deadline is validated."""
        # Check None is OK
        ctx = Context(deadline=None)
        assert ctx.deadline is None

        # Check wall clock time is not OK
        with pytest.raises(ValidationError, match="monotonic time"):
            Context(deadline=time.time() + 10.0)

        # Check monotonic time is OK
        ctx = Context(deadline=time.monotonic() + 10.0)
        assert ctx.deadline is not None
        assert ctx.deadline > time.monotonic()
        assert ctx.deadline <= time.monotonic() + 10.1  # Allow small timing variance

    def test_custom_context(self):
        """Test creating a Context with custom values."""
        deadline = time.monotonic() + 10.0
        metadata = {"user_id": "123", "session": "abc"}
        span = Mock()

        ctx = Context(deadline=deadline, metadata=metadata, retry_count=2, step_id="test-step-123", span=span)

        assert ctx.deadline == deadline
        assert ctx.metadata == metadata
        assert ctx.retry_count == 2
        assert ctx.step_id == "test-step-123"
        assert ctx.span == span

    def test_unique_step_ids(self):
        """Test that each Context gets a unique step_id by default."""
        ctx1 = Context()
        ctx2 = Context()
        assert ctx1.step_id != ctx2.step_id


class TestFromKwargs:
    """Test the from_kwargs static method."""

    def test_none_input(self):
        """Test from_kwargs with None input."""
        ctx = Context.from_kwargs(None)
        assert isinstance(ctx, Context)
        assert ctx.deadline is None
        assert ctx.metadata == {}

    def test_empty_dict_input(self):
        """Test from_kwargs with empty dict."""
        ctx = Context.from_kwargs({})
        assert isinstance(ctx, Context)
        assert ctx.deadline is None
        assert ctx.metadata == {}

    def test_timeout_to_deadline(self):
        """Test that timeout is converted to absolute deadline."""
        start_time = time.monotonic()
        ctx = Context.from_kwargs({"timeout": 5.0})

        assert ctx.deadline is not None
        assert ctx.deadline > start_time
        assert ctx.deadline <= start_time + 5.1  # Allow small timing variance

    def test_explicit_context_ctx_key(self):
        """Test that explicit Context in 'ctx' key is returned."""
        original_ctx = Context(deadline=time.monotonic() + 10)
        original_dump = original_ctx.model_dump()

        result = Context.from_kwargs({"ctx": original_ctx, "other": "value"})

        # Non-destructive check
        assert result is not original_ctx
        for key in original_dump.keys():
            assert getattr(original_ctx, key) == original_dump[key]

        # Check the values are copied
        for key in original_dump.keys():
            if key == "metadata":
                assert result.metadata == {"other": "value"}
            else:
                assert getattr(result, key) == getattr(original_ctx, key)

    def test_metadata_extraction(self):
        """Test that non-private kwargs are extracted to metadata."""
        ctx = Context.from_kwargs(
            {"user_id": "123", "session": "abc", "timeout": 5.0, "_private": "should_not_be_included"}
        )

        assert ctx.metadata == {"user_id": "123", "session": "abc"}
        assert ctx.deadline is not None

    def test_metadata_excludes_private_keys(self):
        """Test that keys starting with '_' are excluded from metadata."""
        ctx = Context.from_kwargs({"public": "value", "_private": "hidden", "__very_private": "also_hidden"})

        assert ctx.metadata == {"public": "value"}
        assert "_private" not in ctx.metadata
        assert "__very_private" not in ctx.metadata

    def test_kwargs_consumption(self):
        """Test that consumed keys are removed from the input dict."""
        src = {"timeout": 5.0, "user_id": "123", "_private": "hidden"}

        Context.from_kwargs(src)

        # All non-private keys should be consumed
        assert "timeout" not in src
        assert "user_id" not in src
        # Private keys should remain
        assert "_private" in src

    def test_invalid_input_type(self):
        """Test that invalid input types raise TypeError."""
        with pytest.raises(TypeError, match="from_kwargs expects a dict or None"):
            Context.from_kwargs("not a dict")  # type: ignore[arg-type]

        with pytest.raises(TypeError, match="from_kwargs expects a dict or None"):
            Context.from_kwargs(123)  # type: ignore[arg-type]

    def test_explicit_context_priority(self):
        """Test that kwargs have higher priority than explicit Context."""
        deadline = time.monotonic() + 10
        original_ctx = Context(deadline=deadline)
        result = Context.from_kwargs({"ctx": original_ctx, "timeout": 5.0, "user_id": "123"})

        assert result is not original_ctx
        assert result.deadline != deadline
        assert result.deadline - deadline < 1.0  # type: ignore[operator]
        assert result.metadata == {"user_id": "123"}


class TestContextManagement:
    """Test context variable management methods."""

    def test_set_and_get(self):
        """Test setting and getting current context."""
        ctx = Context(deadline=time.monotonic() + 10)
        token = Context.set(deadline=ctx.deadline, metadata=ctx.metadata)

        try:
            current = Context.get()
            assert current.deadline == ctx.deadline, f"{current} != {ctx}"
            assert current.metadata == ctx.metadata
        finally:
            Context.reset(token)

    def test_reset_restores_previous(self):
        """Test that reset restores the previous context."""
        # Set initial context
        ctx1 = Context(metadata={"level": "1"})
        token1 = Context.set(metadata=ctx1.metadata)

        try:
            # Set nested context
            ctx2 = Context(metadata={"level": "2"})
            token2 = Context.set(metadata=ctx2.metadata)

            # Verify current is ctx2
            current = Context.get()
            assert current.metadata["level"] == "2"

            # Reset to ctx1
            Context.reset(token2)
            current = Context.get()
            assert current.metadata["level"] == "1"

        finally:
            Context.reset(token1)

    def test_context_isolation(self):
        """Test that contexts are isolated between different calls."""
        ctx1 = Context(metadata={"id": "1"})
        ctx2 = Context(metadata={"id": "2"})

        token1 = Context.set(metadata=ctx1.metadata)
        try:
            assert Context.get().metadata["id"] == "1"
        finally:
            Context.reset(token1)

        token2 = Context.set(metadata=ctx2.metadata)
        try:
            assert Context.get().metadata["id"] == "2"
        finally:
            Context.reset(token2)

    def test_default_context_when_none_set(self):
        """Test that get() returns a default context when none is set."""
        # This test assumes that get() returns a default Context when none is set
        # The actual behavior depends on the ContextVar implementation
        try:
            ctx = Context.get()
            assert isinstance(ctx, Context)
        except LookupError:
            # This is also valid behavior for ContextVar
            pass


# class TestContextImmutability:
#     """Test that Context objects are immutable (frozen)."""

#     def test_context_is_frozen(self):
#         """Test that Context objects cannot be modified after creation."""
#         ctx = Context(metadata={"key": "value"})

#         # Attempting to modify should raise an error
#         with pytest.raises((TypeError, AttributeError)):
#             ctx.metadata["new_key"] = "new_value"

#         with pytest.raises((TypeError, AttributeError)):
#             ctx.deadline = time.monotonic() + 10

#     def test_metadata_is_immutable(self):
#         """Test that metadata dict is immutable."""
#         ctx = Context(metadata={"key": "value"})

#         # The metadata dict itself should be immutable or frozen
#         with pytest.raises((TypeError, AttributeError)):
#             ctx.metadata["new_key"] = "new_value"


class TestContextEdgeCases:
    """Test edge cases and error conditions."""

    def test_zero_timeout(self):
        """Test that zero timeout is handled correctly."""
        ctx = Context.from_kwargs({"timeout": 0.0})
        assert ctx.deadline is not None
        assert ctx.deadline >= time.monotonic() - 1e-3  # Allow small timing variance

    def test_negative_timeout(self):
        """Test that negative timeout is handled correctly."""
        ctx = Context.from_kwargs({"timeout": -1.0})
        assert ctx.deadline is not None
        assert ctx.deadline < time.monotonic()  # Deadline in the past

    def test_large_timeout(self):
        """Test that large timeout values are handled correctly."""
        ctx = Context.from_kwargs({"timeout": 1000000.0})
        assert ctx.deadline is not None
        assert ctx.deadline > time.monotonic()

    def test_complex_metadata_types(self):
        """Test that complex types in metadata are handled correctly."""
        complex_metadata = {
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
            "tuple": (1, 2, 3),
            "bool": True,
            "none": None,
        }

        ctx = Context.from_kwargs(complex_metadata.copy())
        print(f"===> DEBUG: {ctx.metadata=}")
        print(f"===> DEBUG: {complex_metadata=}")
        assert ctx.metadata == complex_metadata

    def test_unicode_metadata(self):
        """Test that unicode characters in metadata are handled correctly."""
        unicode_metadata = {"emoji": "🚀", "chinese": "你好", "greek": "αβγ"}

        ctx = Context.from_kwargs(unicode_metadata.copy())
        assert ctx.metadata == unicode_metadata


class TestContextIntegration:
    """Test Context integration with Module-like patterns."""

    def test_context_with_module_like_usage(self):
        """Test Context usage pattern similar to Module.__call__."""
        # Simulate Module.__call__ pattern
        kwargs = {"timeout": 5.0, "user_id": "123", "threshold": 0.8}

        ctx = Context.from_kwargs(kwargs)
        token = Context.set(deadline=ctx.deadline, metadata=ctx.metadata)

        try:
            # Simulate work within context
            current = Context.get()
            assert current.deadline is not None
            assert current.metadata["user_id"] == "123"
            assert current.metadata["threshold"] == 0.8
        finally:
            Context.reset(token)

    def test_context_merging_pattern(self):
        """Test the merging pattern used in Module.__call__."""
        # Static config (like Module._static_cfg)
        static_config = {"timeout": 10.0, "base_threshold": 0.5}

        # Call-time kwargs
        call_kwargs = {"timeout": 5.0, "user_id": "123"}

        # Merge static + call-time (call-time overrides static)
        merged = {**static_config, **call_kwargs}

        ctx = Context.from_kwargs(merged)

        # timeout should be from call_kwargs (5.0), not static_config (10.0)
        assert ctx.deadline is not None
        assert ctx.metadata["user_id"] == "123"
        assert ctx.metadata["base_threshold"] == 0.5
