# Sequence Diagram – Complaint Submission

## Description
This diagram illustrates how a complaint is submitted, validated, stored, and acknowledged by the system.

```mermaid
sequenceDiagram
    actor Citizen
    participant UI as React Frontend
    participant API as FastAPI Backend
    participant Auth as Authentication
    participant Router as Complaint Router
    participant DB as Database
    participant Notify as Notification Service

    Citizen->>UI: Enter complaint details
    UI->>API: POST /complaints
    API->>Auth: Validate JWT token
    Auth-->>API: User authenticated

    API->>Router: Forward complaint request
    Router->>Router: Validate complaint details

    alt Invalid complaint data
        Router-->>UI: Return validation error
        UI-->>Citizen: Display error message
    else Valid complaint data
        Router->>DB: Check category and duplicates
        DB-->>Router: Return validation results

        alt Duplicate complaint
            Router-->>UI: Return conflict response
            UI-->>Citizen: Display duplicate warning
        else Valid new complaint
            Router->>DB: Save complaint
            Router->>DB: Record audit log
            Router->>Notify: Create submission notification
            Notify->>DB: Save notification
            Router->>DB: Commit transaction
            DB-->>Router: Confirm saved data
            Router-->>API: Return complaint details
            API-->>UI: HTTP 201 Created
            UI-->>Citizen: Display success and reference ID
        end
    end
```

## Sequence Explanation

1. The citizen enters complaint information in the React frontend.
2. The frontend sends a POST request to the FastAPI backend.
3. The backend verifies the user's JWT authentication.
4. The complaint router validates the submitted information.
5. The system checks the category and duplicate complaints.
6. Valid complaints are saved in the database.
7. An audit log and notification record are created.
8. The backend returns a successful response with the complaint reference ID.

**Expected response:** HTTP 201 Created for a successfully submitted complaint.
