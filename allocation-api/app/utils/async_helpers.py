"""Helper functions for async operations"""

import asyncio
from typing import Any, Callable, TypeVar

T = TypeVar('T')


def run_async(coro_func: Callable[..., Any], *args, **kwargs) -> Any:
    """
    Run an async function in a sync context
    
    Args:
        coro_func: Async function to run
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function
        
    Returns:
        Result of the async function
    """
    loop = None
    try:
        # Try to get the current event loop
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No loop is running, create a new one
        pass
    
    if loop and loop.is_running():
        # If we're already in an async context, create a new task
        import concurrent.futures
        import threading
        
        result = None
        exception = None
        
        def run_in_thread():
            nonlocal result, exception
            try:
                # Create a new event loop for this thread
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                result = new_loop.run_until_complete(coro_func(*args, **kwargs))
                new_loop.close()
            except Exception as e:
                exception = e
        
        thread = threading.Thread(target=run_in_thread)
        thread.start()
        thread.join()
        
        if exception:
            raise exception
        return result
    else:
        # No loop is running, we can create one
        return asyncio.run(coro_func(*args, **kwargs))