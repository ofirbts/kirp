from app.agent.agent import agent

class NegotiationEngine:
    def negotiate(self, query):
        a1 = agent.query(query)
        a2 = agent.query(query)

        if len(a1) > len(a2):
            return a1
        return a2
