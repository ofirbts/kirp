# /refactor-safe

Run a behavior-preserving refactor flow:

1. restate unchanged behavior contract
2. apply minimal structural change
3. run lint and tests
4. confirm no contract delta

Return:
- behavior unchanged confirmation
- readability or maintainability gains
- evidence from tests
