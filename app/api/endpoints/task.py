from fastapi import APIRouter, Depends, status
from loguru import logger
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.task import Task, TaskCreate
from app.services.task_service import task_service

router = APIRouter()


@router.get("", response_model=list[Task], status_code=status.HTTP_200_OK)
async def get_tasks(
    db: Session = Depends(get_db),
):
    """
    Get all tasks
    """
    logger.info("Fetching tasks")
    tasks = task_service.get_tasks(db)
    return tasks


@router.get("/{task_id}", response_model=Task, status_code=status.HTTP_200_OK)
async def get_task(task_id: int, db: Session = Depends(get_db)):
    """
    Get a task by ID
    """
    logger.info(f"Fetching task with ID: {task_id}")
    return task_service.get_task(db, task_id=task_id)


@router.post("", response_model=Task, status_code=status.HTTP_201_CREATED)
async def create_task(task_in: TaskCreate, db: Session = Depends(get_db)):
    """
    Create a new task
    """
    logger.info(f"Creating task: {task_in.title}")
    return task_service.create_task(db, task_in=task_in)
