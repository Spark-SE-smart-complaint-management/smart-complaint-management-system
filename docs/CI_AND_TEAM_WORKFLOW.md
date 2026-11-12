# CI and team workflow

## Pull request checks

`.github/workflows/backend-tests.yml` installs pinned backend dependencies on Python 3.11, checks formatting with `ruff format --check app tests`, runs Ruff lint, compiles backend and test modules, and runs the full pytest suite. It triggers for pull requests targeting `main` and pushes to `main` or `feature/**`. A failed step blocks the workflow and exposes its log in Actions.

### Organization admin setup

For `main`, enable branch protection or a repository ruleset that:

1. Requires a pull request before merging.
2. Requires the `Backend tests / backend-tests` status check from the **Backend tests** workflow.
3. Optionally requires the branch to be up to date before merging.
4. Restricts force pushes and branch deletion.

The connected GitHub App cannot administer branch protection here. An organization admin must apply the settings and verify the status-check name after the first successful run.

## Branches and reviews

- Create a focused branch such as `feature/12-security-controls` from the latest `main`.
- Keep one coherent issue per pull request and link it with `Closes #12` (or the relevant issue).
- Include a summary, checks run and results, required deployment steps, and screenshots when a UI change makes them useful.
- Request review from a module owner for cross-module changes. Resolve review feedback before merge; follow the team's approval policy.
- Update from `main` and rerun checks when another module changes a shared model, router, dependency, or migration.

## Integration and regression strategy

The backend suite uses isolated in-memory SQLite (`backend/tests/conftest.py`) and covers authentication, complaint creation, category/SLA, status history, assignment, comments, and attachments. Run the full suite before proposing a merge. For each new module, test its contract and at least one cross-module path that uses shared data, then keep the full suite in CI. Production database, migration, and external-service checks are not simulated by the SQLite suite.

## Sprint handoff and demo exit criteria

Before a demo, use a clean checkout and document Python version, setup, environment variables, seed steps, migration order, API URL, and the CI run/commit used. Use synthetic records and credentials only. Demonstrate only flows whose issue tests pass; list unfinished requirements and environment controls explicitly. Sprint 2's full citizen-to-resolution demo and dataset are tracked in issue #15.
