"""Tests for the Context class."""

import time

import pytest

from mai.types.context import Context


class TestContext:
    """Test cases for the Context class."""

    def test_context_creation(self):
        """Test basic context creation."""
        ctx = Context()
        assert ctx.deadline is None
        assert ctx.metadata == {}
        assert ctx.retry_count == 0
        assert ctx.step_id is not None

    def test_context_with_deadline(self):
        """Test context creation with deadline."""
        deadline = time.monotonic() + 30
        ctx = Context(deadline=deadline)
        assert ctx.deadline == deadline

    def test_context_with_metadata(self):
        """Test context creation with metadata."""
        metadata = {"user_id": "12345", "session_id": "abc123"}
        ctx = Context(metadata=metadata)
        assert ctx.metadata == metadata

    def test_deadline_validation_wall_clock_time(self):
        """Test that wall clock time is rejected for deadlines."""
        with pytest.raises(ValueError, match="'deadline' must be monotonic time"):
            Context(deadline=time.time() + 30)

    def test_deadline_validation_monotonic_time(self):
        """Test that monotonic time is accepted for deadlines."""
        deadline = time.monotonic() + 30
        ctx = Context(deadline=deadline)
        assert ctx.deadline == deadline

    def test_from_kwargs_basic(self):
        """Test from_kwargs with basic parameters."""
        kwargs = {"timeout": 30, "user_id": "12345"}
        ctx = Context.from_kwargs(kwargs)

        assert ctx.deadline is not None
        assert ctx.deadline > time.monotonic()
        assert ctx.metadata["user_id"] == "12345"
        assert "timeout" not in kwargs  # Should be consumed
        assert "user_id" not in kwargs  # Should be consumed

    def test_from_kwargs_with_existing_context(self):
        """Test from_kwargs with existing context."""
        existing_ctx = Context(metadata={"existing": "value"})
        kwargs = {"ctx": existing_ctx, "timeout": 30, "new_key": "new_value"}
        ctx = Context.from_kwargs(kwargs)

        assert ctx.metadata["existing"] == "value"
        assert ctx.metadata["new_key"] == "new_value"
        assert ctx.deadline is not None

    def test_from_kwargs_deadline_and_timeout_conflict(self):
        """Test that deadline and timeout cannot be set together."""
        kwargs = {"deadline": time.monotonic() + 30, "timeout": 30}
        with pytest.raises(ValueError, match="'deadline' and 'timeout' cannot be set at the same time"):
            Context.from_kwargs(kwargs)

    def test_context_manager_basic(self):
        """Test basic context manager functionality."""
        with Context.with_(timeout=30, user_id="12345") as ctx:
            current = Context.current()
            assert current is ctx
            assert current.metadata["user_id"] == "12345"
            assert current.deadline is not None

    def test_context_manager_cleanup(self):
        """Test that context is properly reset after context manager exit."""
        # Set up initial context
        initial_ctx = Context(metadata={"initial": "value"})
        token = Context.set(metadata=initial_ctx.metadata)

        # Use context manager
        with Context.with_(timeout=30, user_id="12345"):
            current = Context.current()
            assert current.metadata["user_id"] == "12345"

        # Verify we're back to initial context
        final_ctx = Context.current()
        assert final_ctx.metadata["initial"] == "value"
        assert "user_id" not in final_ctx.metadata

        # Clean up
        Context.reset(token)

    def test_context_manager_exception_handling(self):
        """Test that context is reset even when exceptions occur."""
        # Set up initial context
        initial_ctx = Context(metadata={"initial": "value"})
        token = Context.set(metadata=initial_ctx.metadata)

        # Use context manager with exception
        try:
            with Context.with_(timeout=30, user_id="12345"):
                current = Context.current()
                assert current.metadata["user_id"] == "12345"
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Verify we're back to initial context
        final_ctx = Context.current()
        assert final_ctx.metadata["initial"] == "value"
        assert "user_id" not in final_ctx.metadata

        # Clean up
        Context.reset(token)

    def test_context_manager_nested(self):
        """Test nested context managers."""
        with Context.with_(timeout=30, outer="value") as outer_ctx:
            assert Context.current() is outer_ctx
            assert Context.current().metadata["outer"] == "value"

            with Context.with_(timeout=60, inner="value") as inner_ctx:
                assert Context.current() is inner_ctx
                assert Context.current().metadata["inner"] == "value"
                # The outer metadata should be inherited
                assert Context.current().metadata["outer"] == "value"

            # Back to outer context
            assert Context.current() is outer_ctx
            assert "inner" not in Context.current().metadata

    def test_context_manager_direct_instance(self):
        """Test using a Context instance directly as a context manager."""
        ctx = Context(timeout=30, metadata={"user_id": "12345"})

        with ctx:
            current = Context.current()
            assert current is ctx
            assert current.metadata["user_id"] == "12345"

    def test_set_and_reset_methods(self):
        """Test the set and reset methods for backward compatibility."""
        token = Context.set(timeout=30, user_id="12345")
        try:
            current = Context.current()
            assert current.metadata["user_id"] == "12345"
        finally:
            Context.reset(token)

        # Verify context is reset
        final_ctx = Context.current()
        assert "user_id" not in final_ctx.metadata

    def test_get_method_creates_default(self):
        """Test that get() creates a default context if none exists."""
        # Clear any existing context by setting a token and resetting
        token = Context.set()
        Context.reset(token)

        ctx = Context.get()
        assert isinstance(ctx, Context)
        assert ctx.deadline is None
        assert ctx.metadata == {}

    def test_current_method_alias(self):
        """Test that current() is an alias for get()."""
        ctx1 = Context.current()
        ctx2 = Context.get()
        assert ctx1 is ctx2
