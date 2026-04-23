# -*- coding: utf-8 -*-

import os


DEFAULT_DATABASE_URL = "mysql+pymysql://root:password@localhost:3306/task_db?charset=utf8mb4"

DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()
# ??????????? DeepSeek ???????????????????????????????? OpenAI ???????
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
AI_REQUEST_TIMEOUT = float(os.getenv("AI_REQUEST_TIMEOUT", "30"))
AI_ENABLED = os.getenv("AI_ENABLED", "1").strip().lower() not in {"0", "false", "no"}
