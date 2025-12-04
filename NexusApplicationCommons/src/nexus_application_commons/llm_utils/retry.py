import asyncio
import random
from functools import wraps
from typing import Any, Callable, Coroutine, TypeVar, Union, cast

from typing_extensions import ParamSpec

P = ParamSpec("P")
T = TypeVar("T")


def exponential_backoff_retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
):
    def decorator(
        func: Callable[P, Union[T, Coroutine[Any, Any, T]]],
    ) -> Callable[P, Coroutine[Any, Any, T]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            retries = 0
            while True:
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await cast(Callable[P, Coroutine[Any, Any, T]], func)(
                            *args, **kwargs
                        )
                    return await asyncio.to_thread(cast(Callable[P, T], func), *args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries > max_retries:
                        raise e

                    delay = initial_delay * (exponential_base ** (retries - 1))

                    # Add jitter to prevent thundering herd problem
                    if jitter:
                        delay = delay * (0.5 + random.random())

                    await asyncio.sleep(delay)

        return wrapper

    return decorator
