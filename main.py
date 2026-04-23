# -*- coding: utf-8 -*-

from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from sqlalchemy import func
from sqlalchemy.orm import Session

import ai_service
import database
import models
import rag_service

app = FastAPI(
    title="Personal Task Management API",
    description="Manage your personal tasks with FastAPI and Pydantic",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5000", "http://localhost:5000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    database.init_db()
    database.ensure_task_order_column()
    database.ensure_task_ai_columns()
    print("Application startup event finished.")


def get_next_order(db: Session) -> int:
    max_order = db.query(func.max(models.TaskDB.order)).scalar()
    if not max_order:
        return 1
    return int(max_order) + 1


def _build_task_db(payload: dict, order: int) -> models.TaskDB:
    normalized = models.task_payload_to_db(payload)
    normalized["order"] = order
    return models.TaskDB(**normalized)


def _get_task_or_404(task_id: int, db: Session) -> models.TaskDB:
    db_task = db.query(models.TaskDB).filter(models.TaskDB.id == task_id).first()
    if db_task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return db_task


def _resequence_task_orders(db: Session) -> None:
    remaining_tasks = (
        db.query(models.TaskDB)
        .order_by(models.TaskDB.order.asc(), models.TaskDB.id.asc())
        .all()
    )
    for index, task in enumerate(remaining_tasks, start=1):
        task.order = index


def _remove_deleted_dependencies(db: Session, removed_ids: set[int]) -> None:
    if not removed_ids:
        return

    remaining_tasks = db.query(models.TaskDB).all()
    for task in remaining_tasks:
        dependency_ids = models.parse_dependency_ids(task.dependency_ids)
        filtered_ids = [dependency_id for dependency_id in dependency_ids if dependency_id not in removed_ids]
        if filtered_ids != dependency_ids:
            task.dependency_ids = models.serialize_dependency_ids(filtered_ids)


@app.get("/")
async def read_root():
    return {"message": "Welcome to the AI Task Manager API!"}


@app.post("/tasks/", response_model=models.Task, status_code=status.HTTP_201_CREATED)
def create_task(task: models.TaskCreate, db: Session = Depends(database.get_db)):
    try:
        payload = task.model_dump()
        db_task = _build_task_db(payload, get_next_order(db))
        db.add(db_task)
        db.commit()
        db.refresh(db_task)
        rag_service.save_task_experience(db_task)
        return db_task
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {exc}",
        ) from exc


@app.get("/tasks/", response_model=list[models.Task])
def read_tasks(
    status_filter: Optional[models.TaskStatus] = Query(None, alias="status"),
    start_date: Optional[datetime] = Query(None, alias="start_date"),
    end_date: Optional[datetime] = Query(None, alias="end_date"),
    db: Session = Depends(database.get_db),
):
    query = db.query(models.TaskDB)

    if status_filter:
        query = query.filter(models.TaskDB.status == status_filter.value)
    if start_date:
        query = query.filter(models.TaskDB.due_date >= start_date)
    if end_date:
        query = query.filter(models.TaskDB.due_date <= end_date)

    return query.order_by(models.TaskDB.order.asc(), models.TaskDB.id.asc()).all()


@app.get("/tasks/{task_id}", response_model=models.Task)
def read_task(task_id: int, db: Session = Depends(database.get_db)):
    return _get_task_or_404(task_id, db)


@app.put("/tasks/{task_id}", response_model=models.Task)
def update_task(task_id: int, task_update: models.TaskUpdate, db: Session = Depends(database.get_db)):
    db_task = _get_task_or_404(task_id, db)

    try:
        update_data = task_update.model_dump(exclude_unset=True)
        update_data.pop("order", None)
        update_data = models.task_payload_to_db(update_data)

        for key, value in update_data.items():
            setattr(db_task, key, value)

        db.commit()
        db.refresh(db_task)
        rag_service.save_task_experience(db_task)
        return db_task
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {exc}",
        ) from exc


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(database.get_db)):
    db_task = _get_task_or_404(task_id, db)

    tasks_to_remove = [db_task]
    child_tasks = (
        db.query(models.TaskDB)
        .filter(models.TaskDB.parent_task_id == db_task.id)
        .order_by(models.TaskDB.order.asc(), models.TaskDB.id.asc())
        .all()
    )
    tasks_to_remove.extend(child_tasks)

    removed_ids = {task.id for task in tasks_to_remove}

    for task in tasks_to_remove:
        db.delete(task)

    _remove_deleted_dependencies(db, removed_ids)
    _resequence_task_orders(db)
    db.commit()
    return


@app.post("/tasks/{task_id}/move_up/", response_model=models.Task)
def move_task_up(task_id: int, db: Session = Depends(database.get_db)):
    current_task = _get_task_or_404(task_id, db)
    previous_task = (
        db.query(models.TaskDB)
        .filter(models.TaskDB.parent_task_id == current_task.parent_task_id)
        .filter(models.TaskDB.order < current_task.order)
        .order_by(models.TaskDB.order.desc())
        .first()
    )

    if previous_task is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task is already at top")

    current_order = current_task.order
    current_task.order = previous_task.order
    previous_task.order = current_order

    db.commit()
    db.refresh(current_task)
    return current_task


@app.post("/tasks/{task_id}/move_down/", response_model=models.Task)
def move_task_down(task_id: int, db: Session = Depends(database.get_db)):
    current_task = _get_task_or_404(task_id, db)
    next_task = (
        db.query(models.TaskDB)
        .filter(models.TaskDB.parent_task_id == current_task.parent_task_id)
        .filter(models.TaskDB.order > current_task.order)
        .order_by(models.TaskDB.order.asc())
        .first()
    )

    if next_task is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task is already at bottom")

    current_order = current_task.order
    current_task.order = next_task.order
    next_task.order = current_order

    db.commit()
    db.refresh(current_task)
    return current_task


@app.post("/api/ai/breakdown-task", response_model=models.TaskBreakdownResponse)
def breakdown_task(request: models.TaskBreakdownRequest, db: Session = Depends(database.get_db)):
    experiences = rag_service.search_similar_tasks(
        db,
        " ".join(part for part in [request.goal, request.description or ""] if part),
    )
    try:
        return ai_service.generate_task_breakdown(request, experiences)
    except ai_service.AIServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@app.post("/api/ai/save-breakdown", response_model=list[models.Task], status_code=status.HTTP_201_CREATED)
def save_breakdown(request: models.TaskBreakdownSaveRequest, db: Session = Depends(database.get_db)):
    try:
        current_order = get_next_order(db)
        root_payload = {
            "title": request.root_task.title,
            "description": request.root_task.description,
            "due_date": request.root_task.due_date,
            "status": models.TaskStatus.TODO,
            "parent_task_id": None,
            "dependency_ids": [],
            "ai_generated": True,
        }
        root_task = _build_task_db(root_payload, current_order)
        db.add(root_task)
        db.flush()

        created_subtasks: list[models.TaskDB] = []
        for index, subtask in enumerate(request.subtasks, start=1):
            task_payload = {
                "title": subtask.title,
                "description": subtask.description,
                "status": models.TaskStatus.TODO,
                "parent_task_id": root_task.id,
                "dependency_ids": [],
                "ai_suggested_priority": subtask.priority,
                "estimated_hours": subtask.estimated_hours,
                "ai_generated": True,
            }
            task_db = _build_task_db(task_payload, current_order + index)
            db.add(task_db)
            created_subtasks.append(task_db)

        db.flush()

        for index, subtask in enumerate(request.subtasks):
            dependency_ids = []
            for dependency_index in subtask.dependencies:
                if 1 <= dependency_index <= len(created_subtasks):
                    dependency_ids.append(created_subtasks[dependency_index - 1].id)
            created_subtasks[index].dependency_ids = models.serialize_dependency_ids(dependency_ids)

        db.commit()

        created_items = [root_task, *created_subtasks]
        for item in created_items:
            db.refresh(item)
        return created_items
    except ValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save AI breakdown: {exc}",
        ) from exc
