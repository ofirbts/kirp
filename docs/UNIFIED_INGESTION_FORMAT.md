# Unified ingestion event format

Every connector (Gmail, Calendar, Notion, Slack, WhatsApp, webhooks) produces the same payload shape. Flow: Connector → /api/v1/ingest (or Kafka) → EventPipeline → EventStore → RAG → SchemaEngine.

## Payload fields

- **tenant_id** (string, required)
- **space_id** (string, required)
- **user_id** (string, required)
- **source** (string): gmail | calendar | notion | slack | whatsapp | email | webhook
- **content** (string)
- **metadata** (object): must include **external_id** (string) for idempotency; may include trace_id, from, channel, etc.

## Idempotency

- **external_id** + **source** + tenant_id: EventStore.find_by_external_id; connector sync skips if exists.
- **cursor** per user: Gmail page_token, Calendar sync_token stored in ConnectorSyncLogStore.last_sync_result.

## Flow

1. Connector fetches data → normalizes to payload above.
2. POST /api/v1/ingest or emit to Kafka → EventPipeline.run().
3. Governance check → Store (Mongo) → Embed → Qdrant → Life-object extraction → SchemaEngine.upsert_node.
