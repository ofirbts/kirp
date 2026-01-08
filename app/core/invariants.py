class InvariantViolation(Exception):
    pass


def assert_invariant(condition: bool, msg: str):
    if not condition:
        raise InvariantViolation(msg)
