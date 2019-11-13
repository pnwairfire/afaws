import asyncio
import functools

async def run_in_loop_executor(func, *args, **kwargs):
    loop = asyncio.get_running_loop()
    func = functools.partial(func, *args, **kwargs)
    return await loop.run_in_executor(None, func)
