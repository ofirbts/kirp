import type { MetaAgentPlan } from "./types";

/**
 * Meta‑Agent orchestrator placeholder.
 *
 * Later this will:
 * - Inspect the query and context
 * - Decide which agents to invoke and in what order
 * - Combine their results into a single answer
 *
 * For Phase 2.5 it only returns InsightAgent as the selected agent.
 */
export function prepareMetaAgent(_input?: {
  query?: string;
  tenant_id?: string;
  space_id?: string;
}): MetaAgentPlan {
  return {
    agent: "InsightAgent",
    reason: "Default insight agent for Ask/Think queries (Phase 2.5 placeholder).",
  };
}

