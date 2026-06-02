# /deploy-check

Run pre-deploy checks:

1. health check status
2. runtime version check
3. migration plan present when needed
4. rollback command and trigger are defined
5. confirm release check in isolated worktree for significant changes
6. confirm Release Guard review is complete
7. if runtime or tooling mismatch exists, propose `/config` update explicitly

Return:
- ready or blocked
- blockers list
- exact remediation sequence
