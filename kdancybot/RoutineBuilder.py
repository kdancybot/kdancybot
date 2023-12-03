import asyncio


async def _loop_routine(func, delay=60, args=()):
    while True:
        await func(*args)
        await asyncio.sleep(delay)


async def _start_single_routine(**kwargs):
    task = asyncio.create_task(_loop_routine(**kwargs))
    return task


async def start_routines(*args):
    return {
        routine["func"].__name__: asyncio.create_task(_loop_routine(**routine))
        for routine in args
    }
