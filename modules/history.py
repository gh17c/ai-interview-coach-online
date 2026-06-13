"""
面试记录持久化
==============
所有面试记录以 JSON 格式存储在 data/sessions/ 目录。
"""

import json
import os
import uuid
from datetime import datetime

SESSIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sessions")


def _ensure_dir():
    """确保存储目录存在"""
    os.makedirs(SESSIONS_DIR, exist_ok=True)


def save_session(session_data: dict) -> str:
    """
    保存一场面试的完整记录。
    返回: session_id (str)
    """
    _ensure_dir()
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:6]
    record = {
        "session_id": session_id,
        "created_at": datetime.now().isoformat(),
        "scenario": session_data.get("scenario", ""),
        "mode": session_data.get("mode", ""),
        "profile": session_data.get("profile", {}),
        "messages": session_data.get("messages", []),
        "report": session_data.get("report"),
    }
    filepath = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    return session_id


def load_session(session_id: str) -> dict | None:
    """加载指定会话，不存在返回 None"""
    filepath = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def list_sessions() -> list[dict]:
    """列出所有历史会话摘要（按时间倒序）"""
    _ensure_dir()
    sessions = []
    for filename in os.listdir(SESSIONS_DIR):
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(SESSIONS_DIR, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            sessions.append({
                "session_id": data.get("session_id", filename.replace(".json", "")),
                "created_at": data.get("created_at", ""),
                "scenario": data.get("scenario", ""),
                "mode": data.get("mode", ""),
                "score": data.get("report", {}).get("overall_score") if data.get("report") else None,
            })
        except (json.JSONDecodeError, KeyError):
            continue
    sessions.sort(key=lambda x: x["created_at"], reverse=True)
    return sessions


def delete_session(session_id: str) -> bool:
    """删除指定会话，成功返回 True"""
    filepath = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    if os.path.exists(filepath):
        os.remove(filepath)
        return True
    return False
