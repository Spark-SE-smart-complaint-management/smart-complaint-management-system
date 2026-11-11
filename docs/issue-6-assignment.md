# Issue #6 — Complaint Assignment (REQ-22 to REQ-25)

## Implemented API

All endpoints require an Administrator JWT.

- `POST /complaints/{complaint_id}/assign`: assign to exactly one target.
  - Staff: `{"staff_id": 12}`
  - Department: `{"department": "Water"}`
  - Reassignment: include `reason` (required when an existing owner is replaced).
- `POST /complaints/{complaint_id}/auto-assign`: use category-to-department mapping and select the least-loaded active staff member.

## Defined workload policy

Current workload is the count of non-archived complaints assigned to each active staff member whose status is not Resolved or Closed. The least-loaded person is selected; ties are broken by ascending user ID for deterministic behavior. The category's `department` field is the mapping source.

## Assignment semantics

A complaint has either `assignee_id` or `assigned_department`, never both. Staff assignment creates an in-app notification for that staff member. Department assignment creates an in-app notification for every active staff member in that department. Both set status to `Assigned`. Assignment and reassignment are appended to the existing audit log, with old/new owner, actor, trigger type and reason.

## Existing database migration

Run `backend/migrations/006_add_assigned_department.sql` once against an existing database before deploying this version. New test databases receive the field through SQLAlchemy metadata creation.

## Notes

The SRS specifies the feature but does not prescribe the workload formula, tie-breaking rule, or department notification recipients. The deterministic policy above is the implementation choice documented here. Email delivery is not claimed: the repository currently has an in-app Notification table, so REQ-24 is implemented using the existing in-app notification mechanism.
