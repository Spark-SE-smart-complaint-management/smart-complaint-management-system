from pydantic import BaseModel, ConfigDict, Field, model_validator


class EscalationHierarchyIn(BaseModel):
    category_id: int | None = Field(default=None, gt=0)
    department: str | None = Field(default=None, max_length=50)
    level: int = Field(ge=1)
    assignee_id: int | None = Field(default=None, gt=0)
    role_name: str = Field(min_length=1, max_length=50)
    is_active: bool = True

    @model_validator(mode="after")
    def validate_scope(self):
        if (self.category_id is None) == (self.department is None):
            raise ValueError(
                "Provide exactly one of category_id or department"
            )

        if self.department is not None:
            self.department = self.department.strip()
            if not self.department:
                raise ValueError("Department cannot be blank")

        self.role_name = self.role_name.strip()
        if not self.role_name:
            raise ValueError("Role name cannot be blank")

        return self


class EscalationHierarchyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int | None
    department: str | None
    level: int
    assignee_id: int | None
    role_name: str
    is_active: bool