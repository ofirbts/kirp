class HumanApproval:
    def require(self, decision):
        return {
            "decision": decision,
            "status": "pending_human_review"
        }
