class PolicySimulator:
    def simulate(self, policy, events):
        results = []
        for e in events:
            results.append({
                "event": e,
                "result": policy.apply(e)
            })
        return results
