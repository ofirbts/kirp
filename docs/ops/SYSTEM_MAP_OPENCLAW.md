# SYSTEM_MAP

Purpose:
- compact operational map for boundaries and ownership.

Core areas:
1. authentication and authorization
2. business data flow
3. error and logging flow
4. deployment and rollback pipeline
5. testing pipeline

Operational guardrails:
- no contract-breaking changes without explicit approval
- default handoff: Builder -> Reviewer/Tester -> Integrator -> Release Guard
