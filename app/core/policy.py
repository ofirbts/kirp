class PolicyViolation(Exception):
    pass


class PolicyEngine:
    def __init__(self, rules: dict):
        self.rules = rules

    def check(self, action: str, payload: dict):
        if action not in self.rules:
            raise PolicyViolation(f"Action {action} not allowed")

        rule = self.rules[action]
        if rule(payload) is False:
            raise PolicyViolation(f"Policy blocked action {action}")
