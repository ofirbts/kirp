import time


class ExecutionTimeout(Exception):
    pass


def run_with_timeout(fn, timeout_sec=5):
    start = time.time()
    result = fn()

    if time.time() - start > timeout_sec:
        raise ExecutionTimeout("Execution timed out")

    return result
