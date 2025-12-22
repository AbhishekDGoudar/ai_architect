import os
import json
import time
from typing import List, Dict, Any

SNAPSHOT_DIR = "snapshots"

def _to_dict(obj: Any) -> Dict:
    """Helper to safely convert Pydantic models or Dicts to JSON-serializable dicts."""
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict") and callable(obj.dict):
        return obj.dict()
    return obj

def get_file_path(project_name: str) -> str:
    """Generates the standardized file path for a project."""
    if not os.path.exists(SNAPSHOT_DIR):
        os.makedirs(SNAPSHOT_DIR)
    
    # Sanitize: Allow only alphanumerics, spaces, dashes, underscores
    safe_name = "".join([c for c in project_name if c.isalnum() or c in (' ', '-', '_')]).strip()
    if not safe_name:
        safe_name = "untitled_project"
    
    return os.path.join(SNAPSHOT_DIR, f"{safe_name}.json")

def check_snapshot_exists(project_name: str) -> bool:
    """Checks if a project file already exists."""
    filepath = get_file_path(project_name)
    return os.path.exists(filepath)

def save_snapshot(project_name: str, state: Dict):
    """Saves the state to a JSON file named after the project."""
    filepath = get_file_path(project_name)
    
    data_to_save = {
        "project_name": project_name, # Store the real name
        "user_request": state.get("user_request", ""),
        "hld": _to_dict(state.get("hld")),
        "lld": _to_dict(state.get("lld")),
        "verdict": _to_dict(state.get("verdict")),
        "metrics": state.get("metrics", {}),
        "logs": state.get("logs", []),
        "timestamp": int(time.time())
    }
    
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, indent=2)
        return os.path.basename(filepath)
    except Exception as e:
        print(f"Error saving snapshot: {e}")
        return None

def list_snapshots() -> List[str]:
    """Returns a list of available snapshot filenames sorted by newest."""
    if not os.path.exists(SNAPSHOT_DIR):
        return []
        
    try:
        files = [f for f in os.listdir(SNAPSHOT_DIR) if f.endswith(".json")]
        files.sort(key=lambda x: os.path.getmtime(os.path.join(SNAPSHOT_DIR, x)), reverse=True)
        return files
    except OSError:
        return []

def load_snapshot(filename: str) -> Dict:
    """Loads a snapshot JSON."""
    filepath = os.path.join(SNAPSHOT_DIR, filename)
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Snapshot {filename} not found.")
        
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def delete_snapshot(filename: str) -> bool:
    """Deletes a snapshot file."""
    filepath = os.path.join(SNAPSHOT_DIR, filename)
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False
    except OSError as e:
        print(f"Error deleting snapshot: {e}")
        return False