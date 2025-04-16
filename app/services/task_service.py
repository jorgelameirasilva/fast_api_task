from sqlalchemy.orm import Session

from app.db.repositories.task import task_repository
from app.exceptions.base import NotFoundException
from app.schemas.task import Task, TaskCreate


class TaskService:
    """Service for task operations"""

    def get_task(self, db: Session, task_id: int) -> Task:
        """Get a task by ID"""
        task = task_repository.get(db, id=task_id)
        if not task:
            raise NotFoundException(f"Task with ID {task_id} not found")
        return task

    def get_tasks(self, db: Session, skip: int = 0, limit: int = 100) -> list[Task]:
        """Get all tasks with pagination"""
        return task_repository.get_all(db, skip=skip, limit=limit)

    def create_task(self, db: Session, task_in: TaskCreate) -> Task:
        """Create a new task"""
        return task_repository.create(db, obj_in=task_in)


task_service = TaskService()
