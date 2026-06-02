# /implement-safe

Implement only approved scope with explicit safety checks.

Flow:
1. restate approved scope
2. list touched files before edits
3. apply minimal change
4. run required checks
5. return change report: what / why / risk / verify

Rules:
- no scope expansion without approval
- no new architectural layers
- request approval before API/DB/infra/auth/data-flow changes
