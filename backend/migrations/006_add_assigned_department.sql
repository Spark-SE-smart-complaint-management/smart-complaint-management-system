-- Issue #6 / REQ-22: supports assignment to a department without selecting
-- an individual staff member. Apply once to an existing database.
ALTER TABLE complaints ADD COLUMN assigned_department VARCHAR(50) NULL;
CREATE INDEX ix_complaints_assigned_department ON complaints (assigned_department);
