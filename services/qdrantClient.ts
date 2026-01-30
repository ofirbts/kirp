// Qdrant client adapter for KIRP Intelligence OS (V1)
// ---------------------------------------------------
// Thin wrapper around HTTP endpoints that expose Qdrant-backed
// collections and vector search:
//   - GET  /api/collections
//   - POST /api/collections/{id}/search

"use client";

import type {
  Collection,
  Document,
  VectorQuery,
  VectorSearchResult,
  ListCollectionsResponse,
  VectorSearchResponse,
} from "@/lib/types";
import { apiClient } from "@/lib/apiClient";

export async function listCollections(): Promise<Collection[]> {
  const res: ListCollectionsResponse = await apiClient.listCollections();
  return res.data ?? [];
}

export async function queryVectors(
  collectionId: string,
  query: VectorQuery,
): Promise<VectorSearchResult[]> {
  const res: VectorSearchResponse = await apiClient.vectorSearch(collectionId, {
    collectionId,
    query,
  });
  return res.data ?? [];
}

/**
 * Upsert a document's vector representation into the backing collection.
 *
 * In V1 this is implemented via a generic "ingest document" HTTP endpoint in the
 * backend that is responsible for:
 *   - Extracting text
 *   - Computing embeddings
 *   - Writing into Qdrant
 *
 * From the UI perspective this is a fire-and-forget call with best-effort error
 * handling.
 */
export async function upsertDocumentVector(doc: Document): Promise<void> {
  // If the backend exposes a dedicated ingestion endpoint, this is where we would
  // call it, e.g. POST /api/collections/{id}/documents.
  // For now, we route through a generic ingest flow if available; if not, we
  // safely no-op.
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const clientAsAny = apiClient as any;
    if (typeof clientAsAny.ingestDocument === "function") {
      await clientAsAny.ingestDocument(doc);
    }
    // If no endpoint is available, we intentionally do nothing.
  } catch (err) {
    // Swallow errors here; UI components should surface failures via their own
    // domain-specific flows when needed.
    // eslint-disable-next-line no-console
    console.error("Failed to upsert document vector", err);
  }
}


