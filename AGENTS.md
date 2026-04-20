# AGENTS Instructions (Repository Root)

This file defines strict contribution behavior for all AI agents working in this repository.

## Mandatory workflow

1. Never push directly to `main`.
2. Create and use `feature/<task-name>` or `fix/<task-name>`.
3. Make changes only on that branch.
4. Run required checks before finishing:
   - Frontend: `cd frontend && npm run lint && npm run build`
   - Backend: `cd backend && pytest`
5. Push only the feature/fix branch.
6. Open a PR to `main`.
7. Do not merge or bypass protections; wait for required CI and approval.
8. Keep changes scoped to the task; no unrelated edits.

## Required final output

- branch name
- files changed
- PR URL

## Enforcement

- Branch protection and CI are the enforceable gatekeepers.
- If any instruction conflicts with branch protection, branch protection wins.
