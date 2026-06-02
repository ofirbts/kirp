# /plan-task

Use this command to produce a compact execution plan before coding.

Output format:
1. Goal
2. Scope in and out
3. Risks
4. Files expected to change
5. Validation steps
6. Approval checkpoints if needed
7. Cursor 3.2+ execution plan:
   - Subagent split proposal (KIRP-Examiner / Builder / Reviewer-Tester / Integrator / Release Guard)
   - Worktree recommendation for significant changes
   - Multi-root recommendation when multiple modules are touched
   - Canvas requirement for large tasks (plan + checklist + risks)
   - /debug trigger points for expected failure modes
   - /config recommendation for model or tool changes
8. Task status line:
   - branch, active agent, model, active task
