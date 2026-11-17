# Use Case Diagram – Smart Complaint Management System

## Description
This diagram represents the interactions between the three main actors: Citizen (Complainant), Staff, and Administrator.

```mermaid
flowchart LR
    Citizen["Citizen / Complainant"]
    Staff["Staff"]
    Admin["Administrator"]

    subgraph System["Smart Complaint Management System"]
        UC1(["Register / Login"])
        UC2(["Submit Complaint"])
        UC3(["Track Complaint"])
        UC4(["View Notifications"])
        UC5(["Add Comments"])
        UC6(["View Assigned Complaints"])
        UC7(["Update Complaint Status"])
        UC8(["Manage Complaints"])
        UC9(["Assign / Reassign Complaints"])
        UC10(["Manage Users"])
        UC11(["Manage Categories"])
        UC12(["View Reports"])
        UC13(["Configure Escalations"])
        UC14(["Manage SLA Policies"])
    end

    Citizen --> UC1
    Citizen --> UC2
    Citizen --> UC3
    Citizen --> UC4
    Citizen --> UC5

    Staff --> UC1
    Staff --> UC6
    Staff --> UC7
    Staff --> UC5

    Admin --> UC1
    Admin --> UC8
    Admin --> UC9
    Admin --> UC10
    Admin --> UC11
    Admin --> UC12
    Admin --> UC13
    Admin --> UC14
```

## Actors

- Citizen: Registers, submits complaints, tracks progress, and receives notifications.
- Staff: Views assigned complaints, updates complaint status, and communicates through comments.
- Administrator: Manages users, complaints, assignments, categories, reports, SLA policies, and escalations.
