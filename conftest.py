# Root conftest: async test support via hookimpl
# Works around broken pytest-asyncio in nix store path isolation
import asyncio
import functools
import inspect

import pytest


def pytest_collection_modifyitems(items):
    """Convert async test functions to sync by wrapping with asyncio.run()."""
    for item in items:
        if isinstance(item, pytest.Function) and inspect.iscoroutinefunction(item.obj):
            orig = item.obj

            @functools.wraps(orig)
            def make_sync(fn=orig):
                @functools.wraps(fn)
                def wrapper(*args, **kwargs):
                    return asyncio.run(fn(*args, **kwargs))
                return wrapper

            item.obj = make_sync()
