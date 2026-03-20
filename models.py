# models.py

# ... (Pydantic 模型部分保持不变) ...
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from datetime import datetime
from enum import Enum

# --- Pydantic Models ---
class TaskStatus(str, Enum):
    TODO = "todo"
    DOING = "doing"
    DONE = "done"

class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, description="The title of the task")
    description: Optional[str] = Field(None, description="A detailed description of the task")
    status: TaskStatus = TaskStatus.TODO
    due_date: Optional[datetime] = Field(None, description="The deadline for the task")

    @field_validator('title')
    def title_must_not_be_empty(cls, value):
        if not value or value.strip() == "":
            raise ValueError("Title cannot be empty")
        return value

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, description="The title of the task")
    description: Optional[str] = Field(None, description="A detailed description of the task")
    status: Optional[TaskStatus] = Field(None, description="The status of the task")
    due_date: Optional[datetime] = Field(None, description="The deadline for the task")
    order: Optional[int] = Field(None, ge=1, description="The task display order")

    @field_validator('title', mode='after')
    def title_must_not_be_empty_on_update(cls, value):
        if value is not None and (not value or value.strip() == ""):
            raise ValueError("Title cannot be empty")
        return value

class Task(TaskBase):
    id: int
    order: int

    class Config:
        orm_mode = True # For SQLAlchemy models

# --- SQLAlchemy Models ---
from sqlalchemy import Column, Integer, String, DateTime # 导入MySQL/SQLAlchemy需要的类型
from database import Base # !!! 关键：从 database.py 导入 Base !!!

class TaskDB(Base):
    __tablename__ = "tasks" # 表名

    id = Column(Integer, primary_key=True, index=True) # MySQL 的 Integer 类型
    title = Column(String(255), index=True) # String 类型，可以指定长度，MySQL 推荐
    description = Column(String(255), nullable=True) # nullable=True 表示数据库列允许 NULL
    status = Column(String(50), default=TaskStatus.TODO.value) # 存储状态的字符串
    due_date = Column(DateTime, nullable=True) # DateTime 类型
    order = Column(Integer, nullable=False, default=0, index=True)

    def __repr__(self):
        return f"<Task(id={self.id}, title='{self.title}', order={self.order}, status='{self.status}')>"
