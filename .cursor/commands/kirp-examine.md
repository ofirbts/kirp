# /kirp-examine

Run a read-only KIRP audit using the **KIRP-Examiner** subagent (`.cursor/subagents/KIRP-Examiner.md`).

## How to start the examiner

1. Open a **new Cursor chat** in this repo (keeps examination separate from implementation).
2. Paste the prompt below (fill brackets).
3. Optional: rename the chat to `KIRP Examiner` for easy return.

## Examiner prompt (copy)

```
You are KIRP-Examiner. Read and follow `.cursor/subagents/KIRP-Examiner.md` exactly.

Examination mode: read-only. Do not edit files.

Scope: [e.g. entire repo | src/foo | PR diff | last commit | specific feature]
Question: [e.g. pre-merge audit | tenant safety on ingest path | explain risks for interview]

Steps:
1. Read authority docs listed in KIRP-Examiner.md for this scope.
2. Trace code paths relevant to the scope; run checklist items 1–10.
3. Run focused tests only if environment allows; otherwise list exact commands as UNVERIFIED.
4. Produce the mandatory "KIRP Examination Report" format from the subagent file.

Task status: Active agent = KIRP-Examiner | Next = complete checklist then verdict.
```

## When to use

- Before merge or release on touched critical flows
- After a feature slice touching tenant, events, governance, agents, or pipeline
- When you need a defensible PASS/FAIL with evidence for review or interview prep

## Subagent split (complex work)

- **KIRP-Examiner** — audit (this command)
- **Builder** — approved fixes only
- **Reviewer-Tester** — tests and regression after fixes
- **Release-Guard** — merge/deploy gates when shipping
