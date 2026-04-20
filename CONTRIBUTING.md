# Contributing to Aegis Orbit

This repository uses a strict PR-first workflow for both humans and AI agents.

## Non-negotiable contribution rules

1. Never push directly to `main`.
2. Create and work on a branch named `feature/<task-name>` or `fix/<task-name>`.
3. Keep changes scoped to the task. Do not include unrelated edits.
4. Run required checks before requesting merge:
   - Frontend: `cd frontend && npm run lint && npm run build`
   - Backend: `cd backend && pytest`
5. Push only the feature/fix branch.
6. Open a PR to `main`.
7. Do not merge or bypass protections until:
   - all required CI checks pass
   - required approval is present
8. Merge only after rule #7 is satisfied.

## Required PR output from AI agents

At completion, AI agents must report:

- branch name
- files changed
- PR URL

## Repository safety policy

- Branch protection rules are the source of merge truth.
- If branch protection is stricter than this document, follow branch protection.
- Bypass merges are not allowed in normal delivery flow.
