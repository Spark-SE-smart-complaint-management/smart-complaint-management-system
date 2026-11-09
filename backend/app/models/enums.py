import enum


class Role(str, enum.Enum):
    COMPLAINANT = "Complainant"
    STAFF = "Staff"
    ADMIN = "Administrator"


class Status(str, enum.Enum):
    NEW = "New"
    ASSIGNED = "Assigned"
    IN_PROGRESS = "In Progress"
    ESCALATED = "Escalated"
    RESOLVED = "Resolved"
    CLOSED = "Closed"
    REOPENED = "Reopened"


class Priority(str, enum.Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class SLAStatus(str, enum.Enum):
    ON_TRACK = "On Track"
    AT_RISK = "At Risk"
    BREACHED = "Breached"
