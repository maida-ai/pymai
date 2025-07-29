"""Tests for the Context class."""

import time

import pytest

from mai.types.context import Context


class TestContextCreation:
    """Test cases for Context creation and validation."""

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


class TestContextFromKwargs:
    """Test cases for the from_kwargs method."""

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


class TestContextManagement:
    """Test cases for Context management methods (set, reset, get, current)."""

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


class TestContextManagerProtocol:
    """Test cases for the context manager protocol (__enter__ and __exit__)."""

    def test_enter_method_basic(self):
        """Test basic __enter__ method functionality."""
        ctx = Context(metadata={"test": "value"})

        # Clear any existing context
        token = Context.set()
        Context.reset(token)

        # Test __enter__ sets the context as current
        entered_ctx = ctx.__enter__()
        assert entered_ctx is ctx
        assert Context.current() is ctx
        assert Context.current().metadata["test"] == "value"

        # Clean up
        ctx.__exit__(None, None, None)

    def test_enter_method_returns_self(self):
        """Test that __enter__ returns the context instance."""
        deadline = time.monotonic() + 30
        ctx = Context(deadline=deadline, metadata={"user_id": "12345"})

        # Clear any existing context
        token = Context.set()
        Context.reset(token)

        result = ctx.__enter__()
        assert result is ctx
        assert result.metadata["user_id"] == "12345"
        assert result.deadline == deadline

        # Clean up
        ctx.__exit__(None, None, None)

    def test_enter_method_stores_token(self):
        """Test that __enter__ stores the token for later cleanup."""
        ctx = Context(metadata={"test": "value"})

        # Clear any existing context
        token = Context.set()
        Context.reset(token)

        # Before __enter__, _token should be None
        assert ctx._token is None

        ctx.__enter__()

        # After __enter__, _token should be set
        assert ctx._token is not None

        # Clean up
        ctx.__exit__(None, None, None)

    def test_exit_method_basic(self):
        """Test basic __exit__ method functionality."""
        ctx = Context(metadata={"test": "value"})

        # Clear any existing context and set initial context
        initial_ctx = Context(metadata={"initial": "value"})
        token = Context.set(metadata=initial_ctx.metadata)

        # Enter the context
        ctx.__enter__()
        assert Context.current() is ctx
        assert Context.current().metadata["test"] == "value"

        # Exit the context
        ctx.__exit__(None, None, None)

        # Should be back to initial context
        final_ctx = Context.current()
        assert final_ctx.metadata["initial"] == "value"
        assert "test" not in final_ctx.metadata

        # Clean up
        Context.reset(token)

    def test_exit_method_with_exception(self):
        """Test __exit__ method with exception parameters."""
        ctx = Context(metadata={"test": "value"})

        # Clear any existing context and set initial context
        initial_ctx = Context(metadata={"initial": "value"})
        token = Context.set(metadata=initial_ctx.metadata)

        # Enter the context
        ctx.__enter__()
        assert Context.current() is ctx

        # Exit with exception info
        exception = ValueError("Test exception")
        ctx.__exit__(ValueError, exception, None)

        # Should still be back to initial context
        final_ctx = Context.current()
        assert final_ctx.metadata["initial"] == "value"
        assert "test" not in final_ctx.metadata

        # Clean up
        Context.reset(token)

    def test_exit_method_clears_token(self):
        """Test that __exit__ clears the stored token."""
        ctx = Context(metadata={"test": "value"})

        # Clear any existing context
        token = Context.set()
        Context.reset(token)

        # Enter and verify token is set
        ctx.__enter__()
        assert ctx._token is not None

        # Exit and verify token is cleared
        ctx.__exit__(None, None, None)
        assert ctx._token is None

    def test_exit_method_with_none_token(self):
        """Test __exit__ method when _token is None."""
        ctx = Context(metadata={"test": "value"})

        # Ensure _token is None
        ctx._token = None

        # Should not raise any exception
        ctx.__exit__(None, None, None)
        assert ctx._token is None


class TestContextManagerUsage:
    """Test cases for high-level context manager usage."""

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
        deadline = time.monotonic() + 30
        ctx = Context(deadline=deadline, metadata={"user_id": "12345"})

        with ctx:
            current = Context.current()
            assert current is ctx
            assert current.metadata["user_id"] == "12345"

    def test_context_manager_with_exception_handling_direct(self):
        """Test context manager with exception handling."""
        ctx = Context(metadata={"test": "value"})

        # Clear any existing context and set initial context
        initial_ctx = Context(metadata={"initial": "value"})
        token = Context.set(metadata=initial_ctx.metadata)

        # Test with exception
        try:
            with ctx:
                assert Context.current() is ctx
                assert Context.current().metadata["test"] == "value"
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Should be back to initial context
        final_ctx = Context.current()
        assert final_ctx.metadata["initial"] == "value"
        assert "test" not in final_ctx.metadata

        # Clean up
        Context.reset(token)

    def test_context_manager_multiple_enter_exit(self):
        """Test multiple enter/exit cycles on the same context."""
        ctx = Context(metadata={"test": "value"})

        # Clear any existing context
        token = Context.set()
        Context.reset(token)

        # First enter/exit cycle
        ctx.__enter__()
        assert Context.current() is ctx
        ctx.__exit__(None, None, None)

        # Second enter/exit cycle
        ctx.__enter__()
        assert Context.current() is ctx
        ctx.__exit__(None, None, None)

        # Should still work correctly
        assert Context.current() is not ctx

    def test_context_manager_nested_direct_instances(self):
        """Test nested context managers with direct Context instances."""
        ctx1 = Context(metadata={"outer": "value1"})
        ctx2 = Context(metadata={"inner": "value2"})

        # Clear any existing context
        token = Context.set()
        Context.reset(token)

        with ctx1:
            assert Context.current() is ctx1
            assert Context.current().metadata["outer"] == "value1"

            with ctx2:
                assert Context.current() is ctx2
                assert Context.current().metadata["inner"] == "value2"
                # Outer metadata should not be inherited in direct instances
                assert "outer" not in Context.current().metadata

            # Back to outer context
            assert Context.current() is ctx1
            assert "inner" not in Context.current().metadata

    def test_context_manager_with_deadline(self):
        """Test context manager with deadline setting."""
        deadline = time.monotonic() + 30
        ctx = Context(deadline=deadline, metadata={"test": "value"})

        # Clear any existing context
        token = Context.set()
        Context.reset(token)

        with ctx:
            current = Context.current()
            assert current is ctx
            assert current.deadline == deadline
            assert current.metadata["test"] == "value"

    def test_context_manager_with_retry_count(self):
        """Test context manager with retry count."""
        ctx = Context(retry_count=3, metadata={"test": "value"})

        # Clear any existing context
        token = Context.set()
        Context.reset(token)

        with ctx:
            current = Context.current()
            assert current is ctx
            assert current.retry_count == 3
            assert current.metadata["test"] == "value"

    def test_context_manager_with_step_id(self):
        """Test context manager with custom step_id."""
        step_id = "custom-step-123"
        ctx = Context(step_id=step_id, metadata={"test": "value"})

        # Clear any existing context
        token = Context.set()
        Context.reset(token)

        with ctx:
            current = Context.current()
            assert current is ctx
            assert current.step_id == step_id
            assert current.metadata["test"] == "value"
