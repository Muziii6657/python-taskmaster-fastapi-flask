# -*- coding: utf-8 -*-

import json
import re
from typing import Any, Optional

import httpx

import models
from config import AI_ENABLED, AI_REQUEST_TIMEOUT, LLM_API_KEY, LLM_BASE_URL, LLM_MODEL


class AIServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _build_history_context(experiences: list[models.TaskExperience]) -> str:
    if not experiences:
        return "No historical experience is available. Generate the plan from general knowledge."

    lines = []
    for index, item in enumerate(experiences, start=1):
        lines.append(
            (
                f"{index}. Title: {item.title}\n"
                f"   Description: {item.description or 'None'}\n"
                f"   Experience: {item.execution_notes or 'None'}\n"
                f"   Actual Hours: {item.actual_hours if item.actual_hours is not None else 'Unknown'}"
            )
        )
    return "\n".join(lines)


def _extract_json_from_text(raw_text: str) -> dict:
    text = (raw_text or "").strip()
    if not text:
        raise AIServiceError("The model returned an empty response.", status_code=502)

    fenced_match = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", text, flags=re.IGNORECASE)
    if fenced_match:
        text = fenced_match.group(1).strip()
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1]

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AIServiceError("The model response is not valid JSON.", status_code=502) from exc

    if not isinstance(parsed, dict):
        raise AIServiceError("The model JSON structure is invalid.", status_code=502)
    return parsed


def _build_messages(
    request: models.TaskBreakdownRequest,
    experiences: list[models.TaskExperience],
) -> list[dict[str, str]]:
    history_context = _build_history_context(experiences)
    system_prompt = (
        "You are a task breakdown assistant for Chinese college students. "
        "Break complex goals into 3 to 7 specific, practical subtasks. "
        "Do not assume a company team or enterprise workflow. "
        "Return JSON only and do not output Markdown."
    )
    user_prompt = f"""
Please break the following goal into a structured task tree and return a JSON object only.

Expected JSON shape:
{{
  "root_task_title": "Main task title in Chinese",
  "summary": "1-2 Chinese sentences",
  "warnings": ["Risk 1", "Risk 2"],
  "suggestions": [
    {{
      "title": "Subtask title",
      "description": "Subtask description",
      "estimated_hours": 3,
      "priority": "high",
      "dependencies": [1]
    }}
  ]
}}

Rules:
1. `priority` must be one of `low`, `medium`, or `high`.
2. `dependencies` uses 1-based indexes of earlier subtasks. Use [] if there is no dependency.
3. Subtasks must be suitable for one person to complete.
4. Use the historical experience to adjust priority, time estimate, and warnings.
5. If there is not enough history, still return a complete result.
6. Write task titles, summary, descriptions, and warnings in Chinese.

Goal: {request.goal}
Extra Context: {request.description or "None"}

Historical Experience:
{history_context}
""".strip()

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _build_client() -> Any:
    if not AI_ENABLED:
        raise AIServiceError("AI is disabled. Please enable AI_ENABLED first.", status_code=503)
    if not LLM_API_KEY:
        raise AIServiceError("LLM_API_KEY is missing.", status_code=503)
    try:
        from openai import OpenAI
    except ModuleNotFoundError:
        return None
    return OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL, timeout=AI_REQUEST_TIMEOUT)


def _validate_provider_settings() -> None:
    model_name = (LLM_MODEL or "").strip().lower()
    base_url = (LLM_BASE_URL or "").strip().lower()

    if model_name.startswith("deepseek") and "deepseek.com" not in base_url:
        raise AIServiceError(
            "DeepSeek model is selected, but LLM_BASE_URL is not a DeepSeek endpoint. "
            "Please set LLM_BASE_URL to https://api.deepseek.com/v1.",
            status_code=503,
        )


def _request_chat_completion(messages: list[dict[str, str]]) -> str:
    _validate_provider_settings()
    client = _build_client()

    if client is not None:
        try:
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                temperature=0.3,
            )
            return response.choices[0].message.content
        except Exception as exc:
            raise AIServiceError(f"Model request failed: {exc}", status_code=502) from exc

    try:
        response = httpx.post(
            f"{LLM_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {LLM_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": LLM_MODEL,
                "messages": messages,
                "temperature": 0.3,
            },
            timeout=AI_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        return payload["choices"][0]["message"]["content"]
    except httpx.HTTPError as exc:
        raise AIServiceError(f"Compatible chat API request failed: {exc}", status_code=502) from exc
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise AIServiceError("Compatible chat API returned an invalid response.", status_code=502) from exc


def generate_task_breakdown(
    request: models.TaskBreakdownRequest,
    experiences: Optional[list[models.TaskExperience]] = None,
) -> models.TaskBreakdownResponse:
    messages = _build_messages(request, experiences or [])

    try:
        raw_content = _request_chat_completion(messages)
    except AIServiceError:
        raise
    except Exception as exc:
        raise AIServiceError("The model did not return usable content.", status_code=502) from exc

    parsed = _extract_json_from_text(raw_content)
    warnings = parsed.get("warnings") or []
    if not experiences:
        warnings = ["No reusable historical experience was found. This plan is generated from general knowledge.", *warnings]
        parsed["warnings"] = warnings

    try:
        return models.TaskBreakdownResponse.model_validate(parsed)
    except Exception as exc:
        raise AIServiceError("The model returned JSON, but its fields do not match the schema.", status_code=502) from exc
