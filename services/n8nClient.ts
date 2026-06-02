// n8n client adapter for KIRP Intelligence OS (V1)
// -----------------------------------------------
// Thin wrapper around HTTP endpoints that front n8n (or any workflow
// orchestrator) for triggering workflows and listing runs:
//   - GET  /api/workflows/{id}/runs
//   - POST /api/workflows/{id}/trigger

"use client";

import type { WorkflowRun, WorkflowRunStatus } from "@/lib/types";
import { apiClient } from "@/lib/apiClient";
import type { ListWorkflowRunsResponse } from "@/lib/types";

export interface WorkflowRunFilter {
  status?: WorkflowRunStatus;
  from?: string;
  to?: string;
}

const NOW = new Date();

const MOCK_WORKFLOW_RUNS: WorkflowRun[] = [
  {
    id: "run_mock_plan_daily_1",
    workflowId: "wf_1",
    startedAt: new Date(NOW.getTime() - 5 * 60_000).toISOString(),
    finishedAt: new Date(NOW.getTime() - 4.5 * 60_000).toISOString(),
    status: "success",
    triggeredBy: "schedule",
    triggerRef: "cron:0 8 * * *",
    input: { tenantId: "default", spaceId: "prod" },
    output: { ok: true },
    logs: [
      "[08:00:00] workflow started",
      "[08:00:00] planner agent invoked",
      "[08:00:01] workflow completed",
    ],
  },
  {
    id: "run_mock_execute_tasks_1",
    workflowId: "wf_2",
    startedAt: new Date(NOW.getTime() - 2 * 60_000).toISOString(),
    finishedAt: undefined,
    status: "running",
    triggeredBy: "event",
    triggerRef: "evt_mock_2",
    input: { decisionId: "DEC-2026-01-001" },
    output: undefined,
    logs: [
      "[08:03:00] workflow started",
      "[08:03:01] executor agent invoked",
    ],
  },
];

export async function triggerWorkflow(
  workflowId: string,
  payload: Record<string, unknown>,
): Promise<WorkflowRun> {
  const res = await apiClient.triggerWorkflow(workflowId, {
    input: payload,
    tenantId: "default",
    spaceId: "prod",
  });

  const now = new Date().toISOString();
  const run: WorkflowRun = {
    id: res.data.runId,
    workflowId,
    startedAt: now,
    finishedAt: undefined,
    status: res.data.status,
    triggeredBy: "manual",
    triggerRef: undefined,
    input: payload,
    output: undefined,
    logs: ["[now] workflow trigger accepted by backend"],
  };

  return run;
}

export async function getWorkflowRuns(
  workflowId: string,
  filters: WorkflowRunFilter = {},
): Promise<WorkflowRun[]> {
  const res: ListWorkflowRunsResponse = await apiClient.listWorkflowRuns(
    workflowId,
    {
      status: filters.status,
      from: filters.from,
      to: filters.to,
    },
  );
  return res.data;
}

