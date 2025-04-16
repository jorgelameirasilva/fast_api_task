from fastapi.testclient import TestClient


def test_create_task(client: TestClient, task_payload):
    response = client.post("/api/tasks", json=task_payload)

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == task_payload["title"]
    assert data["description"] == task_payload["description"]
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_get_task(client: TestClient, task_payload):
    create_response = client.post("/api/tasks", json=task_payload)
    task_id = create_response.json()["id"]

    response = client.get(f"/api/tasks/{task_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task_id
    assert data["title"] == task_payload["title"]
    assert data["description"] == task_payload["description"]


def test_get_all_tasks(client: TestClient):
    task1 = {"title": "Task 1", "description": "Description 1", "is_completed": False}
    task2 = {"title": "Task 2", "description": "Description 2", "is_completed": True}

    client.post("/api/tasks", json=task1)
    client.post("/api/tasks", json=task2)

    response = client.get("/api/tasks")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    titles = [task["title"] for task in data]
    assert "Task 1" in titles
    assert "Task 2" in titles

