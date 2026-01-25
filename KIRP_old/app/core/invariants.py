import logging

logger = logging.getLogger(__name__)

def assert_invariant(condition: bool, msg: str):
    """
    Ensures that a critical system condition is met.
    If not, logs the error and raises an AssertionError.
    """
    if not condition:
        logger.error(f"INVARIANT VIOLATION: {msg}")
        raise AssertionError(msg)
