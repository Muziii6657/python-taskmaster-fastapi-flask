# -*- coding: utf-8 -*-

import os
from datetime import datetime

import httpx
from flask import Flask, flash, redirect, render_template, request, url_for


app = Flask(__name__, template_folder="templates")
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")

FASTAPI_BASE_URL = os.getenv("FASTAPI_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def _extract_api_error(exc: httpx.HTTPStatusError) -> str:
    try:
        payload = exc.response.json()
    except ValueError:
        return f"FastAPI request failed: HTTP {exc.response.status_code}"

    detail = payload.get("detail")
    if isinstance(detail, list):
        return "; ".join(str(item) for item in detail)
    if detail:
        return str(detail)
    return f"FastAPI request failed: HTTP {exc.response.status_code}"


def _due_date_for_input(value: str | None) -> str:
    if not value:
        return ""

    normalized = value.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
        return dt.strftime("%Y-%m-%dT%H:%M")
    except ValueError:
        return value[:16]


def _safe_float(value: str | None) -> float | None:
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _build_payload_from_form(form_data) -> dict:
    title = (form_data.get("title") or "").strip()
    description = (form_data.get("description") or "").strip() or None
    status = (form_data.get("status") or "todo").strip() or "todo"
    due_date = (form_data.get("due_date") or "").strip()
    execution_notes = (form_data.get("execution_notes") or "").strip() or None
    actual_hours = _safe_float(form_data.get("actual_hours"))

    if due_date and len(due_date) == 16:
        due_date = f"{due_date}:00"

    return {
        "title": title,
        "description": description,
        "status": status,
        "due_date": due_date or None,
        "execution_notes": execution_notes,
        "actual_hours": actual_hours,
    }


def _task_sort_key(task: dict) -> tuple[int, int]:
    order_value = task.get("order") or 0
    task_id = task.get("id") or 0
    return int(order_value), int(task_id)


def _build_task_groups(tasks: list[dict]) -> list[dict]:
    indexed_tasks = {task["id"]: {**task, "child_tasks": []} for task in tasks}
    roots: list[dict] = []

    for task in sorted(indexed_tasks.values(), key=_task_sort_key):
        parent_id = task.get("parent_task_id")
        parent = indexed_tasks.get(parent_id) if parent_id else None
        if parent is None:
            roots.append(task)
            continue
        parent["child_tasks"].append(task)

    for root in roots:
        root["child_tasks"].sort(key=_task_sort_key)
        root["has_children"] = bool(root["child_tasks"])
        root["child_count"] = len(root["child_tasks"])
        root["priority_display"] = root.get("ai_suggested_priority") or "-"
        root["estimated_hours_display"] = root.get("estimated_hours") or "-"

        for index, child in enumerate(root["child_tasks"], start=1):
            child["display_index"] = index
            child["priority_display"] = child.get("ai_suggested_priority") or "-"
            child["estimated_hours_display"] = child.get("estimated_hours") or "-"
            child["can_move_up"] = index > 1
            child["can_move_down"] = index < len(root["child_tasks"])

    roots.sort(key=_task_sort_key)
    return roots


@app.route("/")
def index():
    task_groups = []
    error_message = None

    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{FASTAPI_BASE_URL}/tasks/")
            response.raise_for_status()
            tasks = response.json()
            if not isinstance(tasks, list):
                error_message = "FastAPI returned invalid task list format."
                task_groups = []
            else:
                task_groups = _build_task_groups(tasks)
    except httpx.RequestError:
        error_message = "Cannot connect to FastAPI. Please start backend first."
    except httpx.HTTPStatusError as exc:
        error_message = f"FastAPI request failed: HTTP {exc.response.status_code}"
    except ValueError:
        error_message = "Failed to parse JSON response from FastAPI."

    return render_template("index.html", task_groups=task_groups, error_message=error_message)


@app.route("/create_task", methods=["GET", "POST"])
def create_task():
    if request.method == "GET":
        return render_template("create_task.html", form_data={}, fastapi_base_url=FASTAPI_BASE_URL)

    payload = _build_payload_from_form(request.form)

    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.post(f"{FASTAPI_BASE_URL}/tasks/", json=payload)
            response.raise_for_status()
        flash("Task created successfully.", "success")
        return redirect(url_for("index"))
    except httpx.RequestError:
        flash("Cannot connect to FastAPI. Please start backend first.", "error")
    except httpx.HTTPStatusError as exc:
        flash(_extract_api_error(exc), "error")

    return render_template("create_task.html", form_data=request.form, fastapi_base_url=FASTAPI_BASE_URL)


@app.route("/edit_task/<int:task_id>", methods=["GET", "POST"])
def edit_task(task_id: int):
    if request.method == "POST":
        payload = _build_payload_from_form(request.form)
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.put(f"{FASTAPI_BASE_URL}/tasks/{task_id}", json=payload)
                response.raise_for_status()
            flash("Task updated successfully.", "success")
            return redirect(url_for("index"))
        except httpx.RequestError:
            flash("Cannot connect to FastAPI. Please start backend first.", "error")
        except httpx.HTTPStatusError as exc:
            flash(_extract_api_error(exc), "error")

        task = {
            "id": task_id,
            "title": request.form.get("title", ""),
            "description": request.form.get("description", ""),
            "status": request.form.get("status", "todo"),
            "due_date_input": request.form.get("due_date", ""),
            "execution_notes": request.form.get("execution_notes", ""),
            "actual_hours": request.form.get("actual_hours", ""),
        }
        return render_template("edit_task.html", task=task)

    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{FASTAPI_BASE_URL}/tasks/{task_id}")
            response.raise_for_status()
            task = response.json()
            task["due_date_input"] = _due_date_for_input(task.get("due_date"))
            return render_template("edit_task.html", task=task)
    except httpx.RequestError:
        flash("Cannot connect to FastAPI. Please start backend first.", "error")
    except httpx.HTTPStatusError as exc:
        flash(_extract_api_error(exc), "error")

    return redirect(url_for("index"))


@app.route("/delete_task/<int:task_id>", methods=["POST"])
def delete_task(task_id: int):
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.delete(f"{FASTAPI_BASE_URL}/tasks/{task_id}")
            response.raise_for_status()
        flash("Task deleted successfully.", "success")
    except httpx.RequestError:
        flash("Cannot connect to FastAPI. Please start backend first.", "error")
    except httpx.HTTPStatusError as exc:
        flash(_extract_api_error(exc), "error")

    return redirect(url_for("index"))


@app.route("/move_task/<int:task_id>/<string:direction>", methods=["POST"])
def move_task(task_id: int, direction: str):
    if direction not in {"up", "down"}:
        flash("Invalid move direction.", "error")
        return redirect(url_for("index"))

    api_path = "move_up" if direction == "up" else "move_down"
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.post(f"{FASTAPI_BASE_URL}/tasks/{task_id}/{api_path}/")
            response.raise_for_status()
        flash("Task order updated.", "success")
    except httpx.RequestError:
        flash("Cannot connect to FastAPI. Please start backend first.", "error")
    except httpx.HTTPStatusError as exc:
        flash(_extract_api_error(exc), "error")

    return redirect(url_for("index"))


if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host="127.0.0.1", port=5000, debug=debug_mode)

