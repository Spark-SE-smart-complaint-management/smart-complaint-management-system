# Activity Diagram – Complaint Management Workflow

## Description
This activity diagram represents the workflow followed by the Smart Complaint Management System from complaint submission to resolution.

```mermaid
flowchart TD
    A([Start]) --> B["Citizen Registers / Logs In"]
    B --> C["Submit Complaint"]
    C --> D["Validate Complaint Details"]
    D --> E{"Valid Complaint?"}

    E -- No --> F["Display Validation Error"]
    F --> C

    E -- Yes --> G["Check Duplicate Complaint"]
    G --> H{"Duplicate?"}

    H -- Yes --> I["Display Duplicate Warning"]
    I --> Z([End])

    H -- No --> J["Save Complaint"]
    J --> K["Suggest Complaint Category"]
    K --> L["Administrator / Staff Reviews Complaint"]
    L --> M["Assign Complaint to Staff"]
    M --> N["Staff Reviews Complaint"]
    N --> O["Update Complaint Status"]
    O --> P{"Issue Resolved?"}

    P -- No --> Q["Continue Processing"]
    Q --> R{"SLA Breached?"}
    R -- Yes --> S["Escalate Complaint"]
    S --> N
    R -- No --> N

    P -- Yes --> T["Mark Complaint as Resolved"]
    T --> U["Notify Citizen"]
    U --> V["Close Complaint"]
    V --> W([End])
```

## Activity Explanation

1. Citizen logs in and submits a complaint.
2. The system validates the complaint details.
3. Duplicate complaints are checked.
4. A valid complaint is stored in the database.
5. The system can suggest a suitable category.
6. The complaint is reviewed and assigned to staff.
7. Staff investigates and updates the complaint status.
8. If unresolved, processing continues and SLA monitoring may trigger escalation.
9. Once resolved, the citizen is notified.
10. The complaint is closed.

