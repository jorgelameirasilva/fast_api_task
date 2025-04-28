from typing import Optional

from sqlalchemy.orm import Session

from app.db.models.task import Task
from app.db.repositories.base import BaseRepository
from app.schemas.task import TaskCreate, TaskUpdate


class TaskRepository(BaseRepository[Task, TaskCreate, TaskUpdate]):
    """Repository for Task operations"""

    def __init__(self):
        super().__init__(Task)

    def get_by_title(self, db: Session, *, title: str) -> Optional[Task]:
        """Get a task by title"""
        return db.query(Task).filter(Task.title == title).first()


task_repository = TaskRepository()
