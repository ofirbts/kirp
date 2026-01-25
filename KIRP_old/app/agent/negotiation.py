from app.agent.agent import agent

class NegotiationEngine:
    def resolve(self, answers):
        scored = sorted(answers, key=lambda x: x.get("confidence", 0), reverse=True)
        return scored[0]
