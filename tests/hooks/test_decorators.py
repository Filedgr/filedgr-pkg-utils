import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from filedgr_pkg_utils.hooks.decorators import (
    post_action, pre_action, on_failure, measure_time, fire_and_forget, transform_input, transform_output
)


def test_sync_post_action_always_triggers():
    """Test that a basic sync callback is triggered with the correct result and inputs."""
    mock_callback = MagicMock()

    @post_action(callback=mock_callback)
    def calculate(a, b):
        return a + b

    result = calculate(2, 3)

    assert result == 5
    # The callback should receive (result, *args, **kwargs)
    mock_callback.assert_called_once_with(5, 2, 3)


def test_sync_post_action_with_condition():
    """Test that the callback is ONLY triggered if the condition evaluates to True."""
    mock_callback = MagicMock()

    # Condition: only trigger if the result is greater than 10
    def is_greater_than_10(res, *args, **kwargs):
        return res > 10

    @post_action(callback=mock_callback, condition=is_greater_than_10)
    def calculate(a, b):
        return a + b

    # Test failure condition (5 is not > 10)
    res1 = calculate(2, 3)
    assert res1 == 5
    mock_callback.assert_not_called()

    # Test passing condition (15 is > 10)
    res2 = calculate(10, 5)
    assert res2 == 15
    mock_callback.assert_called_once_with(15, 10, 5)


def test_post_action_kwargs_extraction():
    """Test that kwargs are perfectly forwarded to both the condition and callback."""
    mock_callback = MagicMock()
    mock_condition = MagicMock(return_value=True)

    @post_action(callback=mock_callback, condition=mock_condition)
    def process_document(file_path: str, user_id: str, notify: bool = False):
        return "DOC_123"

    # Call the function with a mix of args and kwargs
    process_document("/path.pdf", user_id="bob", notify=True)

    # Verify both hooks received the exact same footprint
    mock_condition.assert_called_once_with("DOC_123", "/path.pdf", user_id="bob", notify=True)
    mock_callback.assert_called_once_with("DOC_123", "/path.pdf", user_id="bob", notify=True)


def test_sync_func_with_async_callback_raises():
    """Test that combining a sync function with an async callback throws a clear error."""
    async def async_cb(res, *args, **kwargs):
        pass

    @post_action(callback=async_cb)
    def sync_func():
        return "success"

    with pytest.raises(RuntimeError, match="Cannot use an async callback with a synchronous function"):
        sync_func()


@pytest.mark.asyncio
async def test_async_func_async_callback():
    """Test an entirely asynchronous pipeline."""
    mock_callback = AsyncMock()

    @post_action(callback=mock_callback)
    async def async_fetch(item_id):
        return f"Data_{item_id}"

    result = await async_fetch(99)

    assert result == "Data_99"
    mock_callback.assert_awaited_once_with("Data_99", 99)


@pytest.mark.asyncio
async def test_async_func_sync_callback():
    """Test an async function triggering a quick sync callback (like a logger)."""
    mock_callback = MagicMock()

    @post_action(callback=mock_callback)
    async def async_process():
        return "Done"

    result = await async_process()

    assert result == "Done"
    # MagicMock uses assert_called_once_with (not awaited)
    mock_callback.assert_called_once_with("Done")


@pytest.mark.asyncio
async def test_async_func_with_condition():
    """Test conditional execution in an async wrapper."""
    mock_callback = AsyncMock()

    # We want to fire the callback only if `is_admin` is True
    def condition_is_admin(res, *args, **kwargs):
        return kwargs.get("is_admin", False)

    @post_action(callback=mock_callback, condition=condition_is_admin)
    async def async_save(data, is_admin=False):
        return True

    # Not admin - should not await callback
    await async_save("data1", is_admin=False)
    mock_callback.assert_not_called()

    # Is admin - should await callback
    await async_save("data2", is_admin=True)
    mock_callback.assert_awaited_once_with(True, "data2", is_admin=True)


def test_pre_action_sync():
    mock_cb = MagicMock()

    @pre_action(callback=mock_cb)
    def my_func(a, b):
        return a + b

    assert my_func(2, 3) == 5
    mock_cb.assert_called_once_with(2, 3)


@pytest.mark.asyncio
async def test_pre_action_async():
    mock_cb = AsyncMock()

    @pre_action(callback=mock_cb)
    async def my_func(user_id):
        return True

    await my_func(user_id=99)
    mock_cb.assert_awaited_once_with(user_id=99)


def test_on_failure_sync():
    mock_cb = MagicMock()

    @on_failure(callback=mock_cb, exceptions=(ValueError,))
    def flaky_func(trigger_error):
        if trigger_error:
            raise ValueError("Boom!")
        return "Safe"

    # Should not trigger on success
    assert flaky_func(False) == "Safe"
    mock_cb.assert_not_called()

    # Should trigger on failure and re-raise
    with pytest.raises(ValueError, match="Boom!"):
        flaky_func(True)

    # Callback receives (Exception, *args, **kwargs)
    args, _ = mock_cb.call_args
    assert isinstance(args[0], ValueError)
    assert args[1] is True


@pytest.mark.asyncio
async def test_measure_time_async():
    mock_cb = MagicMock()

    @measure_time(callback=mock_cb)
    async def slow_func():
        await asyncio.sleep(0.1)
        return "Result"

    result = await slow_func()
    assert result == "Result"

    # Verify callback args: (duration_ms, result)
    called_args, _ = mock_cb.call_args
    duration_ms = called_args[0]
    returned_res = called_args[1]

    assert 90 <= duration_ms <= 150  # Roughly 100ms
    assert returned_res == "Result"


@pytest.mark.asyncio
async def test_fire_and_forget_async():
    execution_flag = False

    @fire_and_forget
    async def bg_task():
        nonlocal execution_flag
        await asyncio.sleep(0.1)
        execution_flag = True

    # Call it (it shouldn't block, should return None immediately)
    result = await bg_task()
    assert result is None
    assert execution_flag is False  # Hasn't finished yet

    # Wait for the event loop to process the background task
    await asyncio.sleep(0.15)
    assert execution_flag is True


def test_fire_and_forget_sync():
    import time
    execution_flag = False

    @fire_and_forget
    def bg_task():
        nonlocal execution_flag
        time.sleep(0.1)
        execution_flag = True

    result = bg_task()
    assert result is None
    assert execution_flag is False

    time.sleep(0.15)
    assert execution_flag is True


def test_transform_input_sync():
    def strip_strings(*args, **kwargs):
        # Convert all string args to uppercase
        new_args = tuple(a.upper() if isinstance(a, str) else a for a in args)
        return new_args, kwargs

    @transform_input(transformer=strip_strings)
    def echo(val):
        return val

    # The input "hello" gets intercepted, transformed to "HELLO", and passed to echo
    assert echo("hello") == "HELLO"


@pytest.mark.asyncio
async def test_transform_output_async():
    async def wrap_in_dict(result, *args, **kwargs):
        return {"data": result, "status": "ok"}

    @transform_output(transformer=wrap_in_dict)
    async def get_data():
        return [1, 2, 3]

    final_result = await get_data()
    assert final_result == {"data": [1, 2, 3], "status": "ok"}
