import httpx
from datetime import datetime

FASTAPI_URL = "http://127.0.0.1:8000"

def test_create_task():
    print("--- Testing POST /tasks/ ---")
    payload = {
        "title": "Test Task from httpx",
        "description": "Testing via httpx client",
        "status": "todo",
        "due_date": "2026-04-15T10:00:00"
    }
    response = httpx.post(f"{FASTAPI_URL}/tasks/", json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.json()}")
    assert response.status_code == 201
    return response.json()["id"] # Return the created task ID for later use

def test_read_tasks(task_id):
    print("\n--- Testing GET /tasks/ ---")
    response = httpx.get(f"{FASTAPI_URL}/tasks/")
    print(f"Status Code: {response.status_code}")
    tasks = response.json()
    print(f"Response Body (all tasks): {tasks}")
    assert response.status_code == 200
    assert isinstance(tasks, list)

    print(f"\n--- Testing GET /tasks/ (filter by status='todo') ---")
    response_filtered = httpx.get(f"{FASTAPI_URL}/tasks/", params={"status": "todo"})
    print(f"Status Code: {response_filtered.status_code}")
    tasks_filtered = response_filtered.json()
    print(f"Response Body (filtered tasks): {tasks_filtered}")
    assert response_filtered.status_code == 200
    # Add more assertions here if needed

    print(f"\n--- Testing GET /tasks/{task_id} ---")
    response_single = httpx.get(f"{FASTAPI_URL}/tasks/{task_id}")
    print(f"Status Code: {response_single.status_code}")
    print(f"Response Body (single task): {response_single.json()}")
    assert response_single.status_code == 200
    assert response_single.json()["id"] == task_id

def test_update_task(task_id):
    print(f"\n--- Testing PUT /tasks/{task_id} ---")
    payload = {
        "status": "doing",
        "description": "Updated via httpx"
    }
    response = httpx.put(f"{FASTAPI_URL}/tasks/{task_id}", json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.json()}")
    assert response.status_code == 200
    assert response.json()["status"] == "doing"

def test_delete_task(task_id):
    print(f"\n--- Testing DELETE /tasks/{task_id} ---")
    response = httpx.delete(f"{FASTAPI_URL}/tasks/{task_id}")
    print(f"Status Code: {response.status_code}")
    assert response.status_code == 204 # DELETE usually returns 204 No Content

if __name__ == "__main__":
    # Test the workflow
    try:
        created_task_id = test_create_task()
        test_read_tasks(created_task_id)
        test_update_task(created_task_id)
        test_delete_task(created_task_id)
        print("\n--- All tests passed (basic workflow)! ---")
    except Exception as e:
        print(f"\n--- An error occurred during testing: {e} ---")