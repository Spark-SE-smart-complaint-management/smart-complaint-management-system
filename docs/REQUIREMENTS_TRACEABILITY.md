# Requirements traceability

This index maps functional SRS requirements to their implementation issues and verification evidence. It includes later-sprint work for handoff. Search test names in `backend/tests/`.

| SRS requirements | Issue | Evidence | Sprint / status |
| --- | --- | --- | --- |
| REQ-1–5: identity, authentication, authorization | [#2](https://github.com/Spark-SE-smart-complaint-management/smart-complaint-management-system/issues/2) | `backend/app/routers/auth.py`, `users.py`, `deps.py`; `tests/test_auth.py` | Sprint 1; merged PR #17 |
| REQ-6–11: complaint submission and validation | [#3](https://github.com/Spark-SE-smart-complaint-management/smart-complaint-management-system/issues/3) | `backend/app/routers/complaints.py`; `tests/test_complaints.py` | Sprint 1; merged PR #19 |
| REQ-12–16: category, priority, SLA policy | [#4](https://github.com/Spark-SE-smart-complaint-management/smart-complaint-management-system/issues/4) | `backend/app/routers/categories.py`, `triage.py`, `services/sla.py`; `tests/test_categories_sla.py` | Sprint 1; merged PR #18 |
| REQ-17–21: status transitions, history, reopen | [#5](https://github.com/Spark-SE-smart-complaint-management/smart-complaint-management-system/issues/5) | `backend/app/routers/complaint_status.py`; `tests/test_complaint_status.py` | Sprint 1; merged PR #20 |
| REQ-22–25: assignment and workload | [#6](https://github.com/Spark-SE-smart-complaint-management/smart-complaint-management-system/issues/6) | `backend/app/routers/assignments.py`; `tests/test_assignments.py`; `docs/issue-6-assignment.md` | Sprint 1; merged PR #22 |
| REQ-26–30: SLA escalation | [#7](https://github.com/Spark-SE-smart-complaint-management/smart-complaint-management-system/issues/7) | No implementation/test file identified on current `main` | Sprint 2; pending |
| REQ-31–34: SLA monitoring/reporting | [#8](https://github.com/Spark-SE-smart-complaint-management/smart-complaint-management-system/issues/8) | SLA deadline/status groundwork in `backend/app/services/sla.py`; reporting tests not identified | Sprint 2; pending |
| REQ-35–38: dashboards and exports | [#9](https://github.com/Spark-SE-smart-complaint-management/smart-complaint-management-system/issues/9) | No implementation/test file identified on current `main` | Sprint 2; pending |
| REQ-39–42: notifications | [#11](https://github.com/Spark-SE-smart-complaint-management/smart-complaint-management-system/issues/11) | `backend/app/models/notification.py`, `backend/app/services/notify.py`; event delivery remains with issue #11 | Sprint 2; pending |
| REQ-43–44: comments and attachments | [#10](https://github.com/Spark-SE-smart-complaint-management/smart-complaint-management-system/issues/10) | `backend/app/routers/comments.py`, `attachments.py`; `tests/test_comments_attachments.py` | Sprint 2; merged PR #21 |

## Non-functional requirements

| NFR area | Issue | Current evidence / gap |
| --- | --- | --- |
| Security, privacy, audit | [#12](https://github.com/Spark-SE-smart-complaint-management/smart-complaint-management-system/issues/12) | Controls and deployment gaps in [Security and privacy controls](SECURITY_AND_PRIVACY.md). Exact SRS NFR identifiers need confirmation against the source SRS before final acceptance. |
| CI, integration, regression | [#14](https://github.com/Spark-SE-smart-complaint-management/smart-complaint-management-system/issues/14) | `.github/workflows/backend-tests.yml` runs lint, Python compile, and the complete backend suite. Branch protection must be enabled by an organization admin. |
| Reliability, performance, accessibility | [#13](https://github.com/Spark-SE-smart-complaint-management/smart-complaint-management-system/issues/13) | Sprint 2 owner; measurable targets and full workflow validation are pending. |
| Integration and demo readiness | [#15](https://github.com/Spark-SE-smart-complaint-management/smart-complaint-management-system/issues/15) | Sprint 2 owner; end-to-end demo and runbook are pending. |

Attach passing CI/test evidence to each implementation PR. Do not mark a row complete until its tests pass on the merged revision and deployment-only controls are configured.
