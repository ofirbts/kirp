from .notion_impl import RealNotionService
from .null import NullNotionService

def get_notion_service():
    service = RealNotionService()
    if service.enabled():
        return service
    return NullNotionService()

notion = get_notion_service()
