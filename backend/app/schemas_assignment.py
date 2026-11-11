from pydantic import BaseModel, Field, model_validator


class ComplaintAssignmentIn(BaseModel):
    staff_id: int | None = None
    department: str | None = Field(default=None, min_length=1, max_length=50)
    reason: str | None = Field(default=None, min_length=1, max_length=500)

    @model_validator(mode="after")
    def exactly_one_target(self):
        if (self.staff_id is None) == (self.department is None):
            raise ValueError("Provide exactly one of staff_id or department")
        if self.department is not None:
            self.department = self.department.strip()
            if not self.department:
                raise ValueError("Department cannot be blank")
        if self.reason is not None:
            self.reason = self.reason.strip() or None
        return self


class AutoAssignmentIn(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class AssignmentOut(BaseModel):
    complaint_id: int
    assignee_id: int | None
    assigned_department: str | None
    status: str
    assignment_type: str
    message: str
