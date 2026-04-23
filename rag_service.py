# -*- coding: utf-8 -*-

import re
from typing import Iterable

from sqlalchemy.orm import Session

import models


def _tokenize(text: str) -> set[str]:
    normalized = (text or "").lower().strip()
    if not normalized:
        return set()

    tokens = set(re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]{2,}", normalized))
    cjk_chunks = re.findall(r"[\u4e00-\u9fff]{2,}", normalized)
    for chunk in cjk_chunks:
        if len(chunk) <= 2:
            tokens.add(chunk)
            continue
        for index in range(len(chunk) - 1):
            tokens.add(chunk[index : index + 2])
    return {token for token in tokens if token}


def _build_candidate_text(task: models.TaskDB) -> str:
    parts = [
        task.title or "",
        task.description or "",
        task.execution_notes or "",
    ]
    return " ".join(part for part in parts if part)


def _score_task(query_tokens: set[str], task: models.TaskDB) -> float:
    candidate_text = _build_candidate_text(task).lower()
    candidate_tokens = _tokenize(candidate_text)
    if not candidate_tokens:
        return 0

    overlap = len(query_tokens & candidate_tokens)
    contains_bonus = sum(1 for token in query_tokens if token and token in candidate_text)
    hours_bonus = 0.5 if task.actual_hours is not None else 0
    note_bonus = 0.5 if task.execution_notes else 0
    return overlap * 2 + contains_bonus + hours_bonus + note_bonus


def save_task_experience(task: models.TaskDB) -> None:
    """
    当前 MVP 直接复用关系数据库中的已完成任务作为经验源。
    这个函数保留为统一入口，后续切换到真正向量库时不需要改主业务代码。
    """
    if not task:
        return


def search_similar_tasks(
    db: Session,
    task_text: str,
    limit: int = 3,
) -> list[models.TaskExperience]:
    query_tokens = _tokenize(task_text)
    if not query_tokens:
        return []

    candidates = (
        db.query(models.TaskDB)
        .filter(models.TaskDB.status == models.TaskStatus.DONE.value)
        .all()
    )

    scored_results: list[models.TaskExperience] = []
    for task in candidates:
        if not (task.execution_notes or task.actual_hours is not None or task.description):
            continue

        score = _score_task(query_tokens, task)
        if score <= 0:
            continue

        scored_results.append(
            models.TaskExperience(
                task_id=task.id,
                title=task.title,
                description=task.description,
                execution_notes=task.execution_notes,
                actual_hours=task.actual_hours,
                similarity_score=score,
            )
        )

    scored_results.sort(key=lambda item: item.similarity_score, reverse=True)
    return scored_results[:limit]

