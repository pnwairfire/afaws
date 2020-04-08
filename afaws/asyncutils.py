import asyncio
import functools

async def run_in_loop_executor(func, *args, **kwargs):
    loop = asyncio.get_running_loop()
    func = functools.partial(func, *args, **kwargs)
    return await loop.run_in_executor(None, func)

RETRY_WAIT = 10
MAX_ATTEMPTS = (60 / RETRY_WAIT) * 5 # retry for up to 5 minutes
async def run_with_retries(func, args, kwargs, exception_to_raise,
        exceptions_whitelist=None, exception_module_name_whitelist=None,
        retry_wait=RETRY_WAIT, max_attempts=MAX_ATTEMPTS):
    attempts = 0
    while True:
        try:
            await func(*args, **kwargs)
            return

        except Exception as e:
            if exceptions_whitelist and not isinstance(e, exceptions_whitelist):
                raise
            if (exception_module_name_whitelist and
                    e.__class__.__module__ not in exception_module_name_whitelist):
                raise

            attempts += 1
            if attempts >= max_attempts:
                logging.error("%sth failure. Aborting.", max_attempts)
                raise exception_to_raise(str(e))

            logging.info("Failed. Waiting %s seconds before retrying", retry_wait)
            await asyncio.sleep(retry_wait)
