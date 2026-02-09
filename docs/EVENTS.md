# Event Types (Canonical)

## Base fields (mandatory)
tenant_id: str  
space_id: str  
user_id: str  
source: str  
trace_id: str | None  
parent_event_id: UUID | None  
version: int  

## ingest.v1
content: str

## agent_run.v1
agent_id: str  
input: dict

