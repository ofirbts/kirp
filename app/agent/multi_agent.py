from app.agent.agent import agent

class PlannerAgent:
    def plan(self, query):
        return {"steps": ["research", "critique", "write"]}

class ResearchAgent:
    def research(self, query):
        return agent.query(query)

class CriticAgent:
    def critique(self, text):
        return {"critique": "no issues found"}

class WriterAgent:
    def write(self, research, critique):
        return f"Final answer:\n{research}"

class MultiAgentOrchestrator:
    def run(self, query):
        planner = PlannerAgent()
        plan = planner.plan(query)

        researcher = ResearchAgent()
        research = researcher.research(query)

        critic = CriticAgent()
        critique = critic.critique(research)

        writer = WriterAgent()
        return writer.write(research, critique)
