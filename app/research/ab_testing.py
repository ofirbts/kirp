from app.agent.agent import agent

class ABTester:
    def run(self, agent_a, agent_b, queries):
        results = []
        for q in queries:
            a = agent_a.query(q)
            b = agent_b.query(q)
            results.append({
                "query": q,
                "A": a,
                "B": b,
                "winner": "A" if len(a) > len(b) else "B"
            })
        return results
