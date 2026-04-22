# AGENTS Instructions (Repository Root)

This file defines strict contribution behavior for all AI agents working in this repository.

## Mandatory workflow

1. Never push directly to `main`.
2. Create and use `feature/<task-name>` or `fix/<task-name>`.
3. Make changes only on that branch.
4. Run required checks before finishing:
   - Frontend: `cd frontend && npm run lint && npm run build`
   - Backend: `cd backend && pytest`
5. **Verification & Integrity Mandate**:
   - AI agents are responsible for the stability of the `main` branch.
   - You MUST run local validation (lint, build, tests) before opening a PR.
   - For every bug fix, you MUST add a reproduction test case.
   - For every feature, you MUST add unit/integration tests.
   - Do not merge if any local or CI check fails.
6. Push only the feature/fix branch.
7. Open a PR to `main`.
8. Once CI is green and you have verified local integrity, you are authorized to merge the PR autonomously.
8. Keep changes scoped to the task; no unrelated edits.

## Required final output

- branch name
- files changed
- PR URL

## Enforcement

- Branch protection and CI are the enforceable gatekeepers.
- If any instruction conflicts with branch protection, branch protection wins.
