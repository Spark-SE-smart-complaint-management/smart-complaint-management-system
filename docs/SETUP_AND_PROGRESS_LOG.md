## Phase 2: Issue #4 (REQ-12 to 16) - Categorization, priority, SLA policy
Branch: feature/4-categories-sla

New files: app/routers/categories.py, app/routers/triage.py, app/services/sla.py,
app/services/categorizer.py, app/schemas_category.py, tests/test_categories_sla.py
Changed files: app/main.py (2 routers registered), app/seed.py (default categories + SLA matrix)

Decisions:
- SLA deadline = complaint.created_at + policy hours (recomputed on change).
- No policy or no priority/category -> deadline is null.
- At Risk when >= 80% of SLA has elapsed (AT_RISK_FRACTION in services/sla.py); #8 can reuse classify_sla().
- Closed complaints cannot be re-triaged (409).
- Changing a policy does not retroactively change existing complaints.

Status: done, 44 tests passing. Next: #6 assignment (feature/6-assignment).