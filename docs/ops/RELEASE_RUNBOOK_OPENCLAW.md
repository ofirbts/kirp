# RELEASE_RUNBOOK

Pre-merge:
- lint, build, and tests pass
- reviewer or tester signoff

Pre-deploy:
- health check
- runtime version check
- migration plan when needed
- rollback command and trigger

Release flow:
1. run `/deploy-check`
2. Release Guard validation
3. deploy
4. post-deploy health and version verification
