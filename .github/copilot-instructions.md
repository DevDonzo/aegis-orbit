# Copilot Instructions

Follow `AGENTS.md` and `CONTRIBUTING.md` in the repository root.

Non-negotiable:

1. Never push directly to `main`.
2. Work only on `feature/*` or `fix/*` branches.
3. Run required checks and verify integrity before finishing.
4. **Smart Validation**: You are responsible for ensuring nothing breaks. Before merging, you MUST:
   - Run full local lint/build/test suites.
   - Add new tests for every change (fixes must have reproduction tests).
   - Verify that your changes do not regress existing features.
5. Open PR to `main`.
6. Once CI passes and your internal validation is complete, you are authorized to merge autonomously.
7. Keep changes scoped to the active task.
