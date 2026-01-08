from app.rag.retrieval_pipeline import retrieval_pipeline

class BenchmarkSuite:
    def retrieval_quality(self, queries):
        results = []
        for q in queries:
            # raw_results נדרש – ניתן להעביר רשימה ריקה
            ctx = retrieval_pipeline(q, raw_results=[])
            results.append({
                "query": q,
                "context_len": len(ctx),
            })
        return results

    def agent_quality(self, agent, queries):
        results = []
        for q in queries:
            ans = agent.query(q)
            results.append({
                "query": q,
                "answer_len": len(ans),
            })
        return results
