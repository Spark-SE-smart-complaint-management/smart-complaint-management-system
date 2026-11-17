# Class Diagram – Smart Complaint Management System

## Description
This class diagram represents the major database entities and their relationships.

```mermaid
classDiagram
    class User {
        +int id
        +string name
        +string email
        +string phone
        +string password_hash
        +Role role
        +string department
        +bool is_active
        +register()
        +login()
    }

    class Complaint {
        +int id
        +string reference_id
        +int complainant_id
        +string title
        +string description
        +int category_id
        +Priority priority
        +Status status
        +int assignee_id
        +datetime sla_deadline
        +create()
        +updateStatus()
    }

    class Category {
        +int id
        +string name
        +string department
        +bool is_active
    }

    class Comment {
        +int id
        +int complaint_id
        +int author_id
        +string content
        +datetime created_at
    }

    class Attachment {
        +int id
        +int complaint_id
        +int uploaded_by
        +string original_filename
        +string stored_filename
        +string content_type
        +int file_size
    }

    class Notification {
        +int id
        +int user_id
        +string event
        +string message
        +string channel
        +string delivery_status
        +bool is_read
    }

    class AuditLog {
        +int id
        +int complaint_id
        +int actor_id
        +string action
        +string from_value
        +string to_value
        +string trigger_type
    }

    class SLAPolicy {
        +int id
        +int category_id
        +Priority priority
        +int duration_hours
    }

    class EscalationHierarchy {
        +int id
        +int category_id
        +string department
        +int level
        +int assignee_id
        +string role_name
        +bool is_active
    }

    User "1" --> "0..*" Complaint : submits
    User "0..1" --> "0..*" Complaint : assigned to
    Category "1" --> "0..*" Complaint : categorizes
    Complaint "1" --> "0..*" Comment : has
    User "1" --> "0..*" Comment : writes
    Complaint "1" --> "0..*" Attachment : contains
    User "1" --> "0..*" Attachment : uploads
    User "1" --> "0..*" Notification : receives
    Complaint "0..1" --> "0..*" AuditLog : records
    User "0..1" --> "0..*" AuditLog : performs
    Category "1" --> "0..*" SLAPolicy : defines
    Category "0..1" --> "0..*" EscalationHierarchy : configures
    User "0..1" --> "0..*" EscalationHierarchy : assigned to
```

## Main Classes

- User: Stores user details and role information.
- Complaint: Stores complaint details, status, priority, assignment, and SLA information.
- Category: Defines complaint categories.
- Comment: Stores discussion related to complaints.
- Attachment: Stores uploaded complaint file metadata.
- Notification: Stores notification details and delivery status.
- AuditLog: Maintains a history of important system actions.
- SLAPolicy: Defines SLA durations for categories and priorities.
- EscalationHierarchy: Defines escalation levels and targets.
