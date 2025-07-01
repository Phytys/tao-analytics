import asyncio
from concurrent.futures import ThreadPoolExecutor

_EXEC = ThreadPoolExecutor(max_workers=4)

def run_blocking(func, *args, **kwargs):
    loop = asyncio.get_running_loop()
    return loop.run_in_executor(_EXEC, lambda: func(*args, **kwargs)) 