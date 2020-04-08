import asyncio
import logging
import functools

async def run_in_loop_executor(func, *args, **kwargs):
    loop = asyncio.get_running_loop()
    func = functools.partial(func, *args, **kwargs)
    return await loop.run_in_executor(None, func)

RETRY_WAIT = 10
MAX_ATTEMPTS = (60 / RETRY_WAIT) * 5 # retry for up to 5 minutes
async def run_with_retries(func, args, kwargs, is_async, exception_to_raise,
        extra_exception_args=[], exceptions_whitelist=None,
        exception_module_name_whitelist=None, log_msg_prefix=None,
        retry_wait=RETRY_WAIT, max_attempts=MAX_ATTEMPTS):
    log_msg_prefix = log_msg_prefix or func.__name__
    attempts = 0
    while True:
        try:
            if is_async:
                await func(*args, **kwargs)
            else:
                func(*args, **kwargs)
            return

        except Exception as e:
            if ((exceptions_whitelist and not isinstance(e, exceptions_whitelist))
                    or (exception_module_name_whitelist and
                        e.__class__.__module__ not in exception_module_name_whitelist)):
                logging.error("%s - unexpected failure: %s. Aborting.",
                    log_msg_prefix, e)

            attempts += 1
            if attempts >= max_attempts:
                logging.error("%s -  %sth failure. Aborting.", log_msg_prefix,
                    max_attempts)
                raise exception_to_raise(str(e), *extra_exception_args)

            logging.info("%s - Failed. Waiting %s seconds before retrying",
                log_msg_prefix, retry_wait)
            await asyncio.sleep(retry_wait)
