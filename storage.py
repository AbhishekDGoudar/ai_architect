import os
import json
import time
from typing import List, Dict, Any

SNAPSHOT_DIR = "snapshots"

def _to_dict(obj: Any) -> Dict:
    if obj is None: return None
    if hasattr(obj, "model_dump"): return obj.model_dump()
    if hasattr(obj, "dict") and callable(obj.dict): return obj.dict()
    return obj

def get_file_path(project_name: str) -> str:
    if not os.path.exists(SNAPSHOT_DIR): os.makedirs(SNAPSHOT_DIR)
    safe_name = "".join([c for c in project_name if c.isalnum() or c in (' ', '-', '_')]).strip() or "untitled_project"
    return os.path.join(SNAPSHOT_DIR, f"{safe_name}.json")

def save_snapshot(project_name: str, state: Dict):
    filepath = get_file_path(project_name)
    data_to_save = {
        "project_name": project_name,
        "user_request": state.get("user_request", ""),
        "hld": _to_dict(state.get("hld")),
        "lld": _to_dict(state.get("lld")),
        "verdict": _to_dict(state.get("verdict")),
        "scaffold": _to_dict(state.get("scaffold")),
        "diagram_code": _to_dict(state.get("diagram_code")),
        "diagram_path": state.get("diagram_path"),
        "diagram_validation": _to_dict(state.get("diagram_validation")),
        "metrics": state.get("metrics", {}),
        "logs": state.get("logs", []),
        "timestamp": int(time.time())
    }
    try:
        with open(filepath, "w", encoding="utf-8") as f: json.dump(data_to_save, f, indent=2)
        return os.path.basename(filepath)
    except Exception as e: print(f"Error saving: {e}"); return None

def list_snapshots() -> List[str]:
    if not os.path.exists(SNAPSHOT_DIR): return []
    try:
        files = [f for f in os.listdir(SNAPSHOT_DIR) if f.endswith(".json")]
        files.sort(key=lambda x: os.path.getmtime(os.path.join(SNAPSHOT_DIR, x)), reverse=True)
        return files
    except OSError: return []

def load_snapshot(filename: str) -> Dict:
    filepath = os.path.join(SNAPSHOT_DIR, filename)
    if not os.path.exists(filepath): raise FileNotFoundError(f"Snapshot {filename} not found.")
    with open(filepath, "r", encoding="utf-8") as f: return json.load(f)

def delete_snapshot(filename: str) -> bool:
    filepath = os.path.join(SNAPSHOT_DIR, filename)
    try:
        if os.path.exists(filepath): os.remove(filepath); return True
        return False
    except OSError: return False