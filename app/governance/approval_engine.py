from app.services.notion import NotionGateway

class ApprovalEngine:
    def __init__(self):
        self.notion = NotionGateway()

    def request_approval(self, action: dict, trace_id: str):
        return self.notion.create_record(
            {
                "title": action["title"],
                "type": "Approval",
                "status": "Pending",
                "requires_approval": True,
                "confidence": action.get("confidence", 0.0),
            },
            trace_id
        )
