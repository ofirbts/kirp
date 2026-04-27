# /test

Run the standard verification pipeline for OpenClaw changes:

1. `npm run lint`
2. `npm run build`
3. `python3 -m pytest tests/ -q --tb=short`
4. Run critical integration tests relevant to touched flows
5. If any step fails, run `/debug` with the first failing test or command and touched files
6. Use filtered search only (path, type, glob) to avoid noisy scans

Return:
- pass or fail per step
- first failure root cause
- minimal next fix action
- `/debug` findings when failure occurs
