// Kafka client adapter for KIRP Intelligence OS (V1)
// --------------------------------------------------
// Thin wrapper around HTTP endpoints that expose Kafka-backed events.
// Source of truth:
//   - /api/events
//   - /api/events/dlq

"use client";

import type { Event, EventFilter, ListEventsResponse } from "@/lib/types";
import { apiClient } from "@/lib/apiClient";

/**
 * Fetch events from the primary event stream.
 * Delegates to GET /api/events with the same filter shape.
 */
export async function fetchEvents(filters: EventFilter = {}): Promise<Event[]> {
  const res: ListEventsResponse = await apiClient.listEvents(filters);
  return res.data;
}

/**
 * Fetch events from the dead-letter queue.
 * Delegates to GET /api/events/dlq.
 */
export async function fetchDlqEvents(
  filters: EventFilter = {},
): Promise<Event[]> {
  const res: ListEventsResponse = await apiClient.listDlqEvents(filters);
  return res.data;
}

/**
 * Subscribe to a topic.
 *
 * For V1, this is implemented as a simple polling loop over /api/events
 * and calls the handler with the full event list on each poll. Consumers
 * can diff based on ids if they need incremental updates.
 */
export async function subscribeToTopic(
  topic: string,
  handler: (events: Event[]) => void,
  {
    intervalMs = 10_000,
    filters = {},
  }: { intervalMs?: number; filters?: EventFilter } = {},
): Promise<void> {
  let cancelled = false;

  const loop = async () => {
    while (!cancelled) {
      try {
        const res = await apiClient.listEvents({ ...filters, topic });
        handler(res.data);
      } catch (err) {
        // eslint-disable-next-line no-console
        console.error("kafkaClient.subscribeToTopic polling error", err);
      }
      await new Promise((resolve) => setTimeout(resolve, intervalMs));
    }
  };

  void loop();

  // Return a promise that resolves immediately; caller can manage lifecycle
  // by closing over `cancelled` if needed in a higher-level helper.
  return Promise.resolve();
}


