import time
import tracemalloc
import functools
import inspect
from datetime import datetime

def format_datetime(date: datetime) -> str:
    return date.strftime('%Y-%m-%dT%H:%M:%SZ')

def get_qualified_path(obj) -> str:
    """
    Returns the full module path of a class, function, or method.
    Example: 'myproject.module.submodule.MyClass'
    """
    return f"{obj.__module__}.{obj.__qualname__}"

def footprint(time_limit_seconds=2.0, memory_limit_mb=100.0):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tracemalloc.start()
            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            end_time = time.perf_counter()
            ts = (end_time - start_time)

            cls_name = None
            if args:
                possible_self_or_cls = args[0]
                if inspect.isclass(possible_self_or_cls):
                    cls_name = possible_self_or_cls.__name__
                elif hasattr(possible_self_or_cls, '__class__'):
                    cls_name = possible_self_or_cls.__class__.__name__

            if ts > time_limit_seconds or peak > memory_limit_mb * 1024 * 1024:
                location = f"{cls_name + '.' if cls_name else ''}{func.__name__}"
                print(
                    f">>> {location}: runtime: {ts:.2f}s, memory: {peak / 1024 / 1024:.2f}MB",
                    flush=True
                )

            return result
        return wrapper
    return decorator

