# main.py

from fastapi import FastAPI, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime # 确保导入 datetime
from pydantic import ValidationError

# Import modules
import models # 导入你的模型
import database # 导入数据库函数

app = FastAPI(
    title="Personal Task Management API",
    description="Manage your personal tasks with FastAPI and Pydantic",
    version="1.0.0",
)

# 在应用启动时执行数据库初始化
@app.on_event("startup")
def startup_event():
    database.init_db()
    database.ensure_task_order_column()
    print("Application startup event finished.")


def get_next_order(db: Session) -> int:
    max_order = db.query(func.max(models.TaskDB.order)).scalar()
    if not max_order:
        return 1
    return int(max_order) + 1


# ... (你的 CRUD 路由定义) ...
@app.get("/")
async def read_root():
    return {"message": "Welcome to the Task Manager API!"}

# Create Task
@app.post("/tasks/", response_model=models.Task, status_code=status.HTTP_201_CREATED)
def create_task(
    task: models.TaskCreate,
    db: Session = Depends(database.get_db)
):
    try:
        # 使用 model_dump() 获取 Pydantic 模型的数据，用于创建 SQLAlchemy 模型实例
        payload = task.model_dump()
        payload["order"] = get_next_order(db)
        db_task = models.TaskDB(**payload)
        db.add(db_task)
        db.commit()
        db.refresh(db_task)
        return db_task
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.errors())
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")

# Read Tasks (with filtering)
@app.get("/tasks/", response_model=List[models.Task])
def read_tasks(
    status_filter: Optional[models.TaskStatus] = Query(None, alias="status"),
    start_date: Optional[datetime] = Query(None, alias="start_date"),
    end_date: Optional[datetime] = Query(None, alias="end_date"),
    db: Session = Depends(database.get_db)
):
    query = db.query(models.TaskDB)

    if status_filter:
        query = query.filter(models.TaskDB.status == status_filter.value)
    if start_date:
        query = query.filter(models.TaskDB.due_date >= start_date)
    if end_date:
        query = query.filter(models.TaskDB.due_date <= end_date)

    tasks = query.order_by(models.TaskDB.order.asc(), models.TaskDB.id.asc()).all()
    return tasks

# Read Single Task
@app.get("/tasks/{task_id}", response_model=models.Task)
def read_task(task_id: int, db: Session = Depends(database.get_db)):
    db_task = db.query(models.TaskDB).filter(models.TaskDB.id == task_id).first()
    if db_task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return db_task

# Update Task
@app.put("/tasks/{task_id}", response_model=models.Task)
def update_task(
    task_id: int,
    task_update: models.TaskUpdate,
    db: Session = Depends(database.get_db)
):
    db_task = db.query(models.TaskDB).filter(models.TaskDB.id == task_id).first()
    if db_task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    try:
        update_data = task_update.model_dump(exclude_unset=True) # exclude_unset=True is crucial here
        update_data.pop("order", None)

        for key, value in update_data.items():
            setattr(db_task, key, value)

        db.commit()
        db.refresh(db_task)
        return db_task
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.errors())
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")

# Delete Task
@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(database.get_db)):
    db_task = db.query(models.TaskDB).filter(models.TaskDB.id == task_id).first()
    if db_task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    removed_order = db_task.order
    db.delete(db_task)
    db.query(models.TaskDB).filter(models.TaskDB.order > removed_order).update(
        {models.TaskDB.order: models.TaskDB.order - 1}, synchronize_session=False
    )
    db.commit()
    return


@app.post("/tasks/{task_id}/move_up/", response_model=models.Task)
def move_task_up(task_id: int, db: Session = Depends(database.get_db)):
    current_task = db.query(models.TaskDB).filter(models.TaskDB.id == task_id).first()
    if current_task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    previous_task = (
        db.query(models.TaskDB)
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
    current_task = db.query(models.TaskDB).filter(models.TaskDB.id == task_id).first()
    if current_task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    next_task = (
        db.query(models.TaskDB)
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
