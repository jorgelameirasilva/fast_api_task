from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class TaskBase(BaseModel):
    """Base schema for Task with common attributes"""

    title: str = Field(
        ..., min_length=1, max_length=100, description="The title of the task"
    )
    description: Optional[str] = Field(
        None, description="The detailed description of the task"
    )


class TaskCreate(TaskBase):
    """Schema for creating a new Task"""

    pass


class TaskInDBBase(TaskBase):
    """Schema for Task stored in DB"""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Task(TaskInDBBase):
    """Schema for Task response"""

    pass
