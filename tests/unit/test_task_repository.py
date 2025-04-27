from sqlalchemy.orm import Session

from app.db.repositories.task import task_repository
from app.schemas.task import TaskCreate


def test_create_task(db: Session):
    task_in = TaskCreate(
        title="Test Task", description="Test Description"
    )
    task = task_repository.create(db, obj_in=task_in)

    assert task.title == "Test Task"
    assert task.description == "Test Description"
    assert task.id is not None


def test_get_task(db: Session):
    task_in = TaskCreate(
        title="Test Task", description="Test Description"
    )
    created_task = task_repository.create(db, obj_in=task_in)

    task = task_repository.get(db, id=created_task.id)

    assert task.id == created_task.id
    assert task.title == created_task.title
    assert task.description == created_task.description


def test_get_all_tasks(db: Session):
    task_1 = TaskCreate(title="Task 1", description="Description 1")
    task_2 = TaskCreate(title="Task 2", description="Description 2")
    task_repository.create(db, obj_in=task_1)
    task_repository.create(db, obj_in=task_2)

    tasks = task_repository.get_all(db)

    assert len(tasks) == 2
    assert tasks[0].title == "Task 1"
    assert tasks[1].title == "Task 2"


def test_get_by_title(db: Session):
    task_in = TaskCreate(title="Unique Title", description="Test Description")
    task_repository.create(db, obj_in=task_in)

    task = task_repository.get_by_title(db, title="Unique Title")

    assert task is not None
    assert task.title == "Unique Title"
