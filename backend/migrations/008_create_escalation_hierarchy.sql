-- Issue #7 / REQ-26
-- Configurable escalation hierarchy per category or department.

CREATE TABLE escalation_hierarchies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    category_id INTEGER NULL,
    department VARCHAR(50) NULL,

    level INTEGER NOT NULL CHECK (level >= 1),

    assignee_id INTEGER NULL,
    role_name VARCHAR(50) NOT NULL,

    is_active INTEGER NOT NULL DEFAULT 1,

    CONSTRAINT fk_escalation_category
        FOREIGN KEY (category_id) REFERENCES categories(id),

    CONSTRAINT fk_escalation_assignee
        FOREIGN KEY (assignee_id) REFERENCES users(id),

    CONSTRAINT ck_escalation_scope
        CHECK (
            (category_id IS NOT NULL AND department IS NULL)
            OR
            (category_id IS NULL AND department IS NOT NULL)
        )
);

-- Prevent duplicate levels within a category hierarchy.
CREATE UNIQUE INDEX uq_escalation_category_level
    ON escalation_hierarchies(category_id, level)
    WHERE category_id IS NOT NULL;

-- Prevent duplicate levels within a department hierarchy.
CREATE UNIQUE INDEX uq_escalation_department_level
    ON escalation_hierarchies(department, level)
    WHERE department IS NOT NULL;

CREATE INDEX ix_escalation_category
    ON escalation_hierarchies(category_id);

CREATE INDEX ix_escalation_department
    ON escalation_hierarchies(department);