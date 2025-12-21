import os
import json
import time
from typing import List, Dict

SNAPSHOT_DIR = "snapshots"

def save_snapshot(project_name: str, state: Dict):
    """Saves the final state to a JSON file."""
    if not os.path.exists(SNAPSHOT_DIR):
        os.makedirs(SNAPSHOT_DIR)
    
    # Create a unique filename
    timestamp = int(time.time())
    safe_name = "".join([c for c in project_name if c.isalnum() or c in (' ', '-', '_')]).strip()
    filename = f"{SNAPSHOT_DIR}/{safe_name}_{timestamp}.json"
    
    # We only save Serializable data (exclude objects if they aren't dicts)
    # The Pydantic models (HLD/LLD) need to be converted to dicts first
    data_to_save = {
        "user_request": state["user_request"],
        "hld": state["hld"].dict(),
        "lld": state["lld"].dict(),
        "verdict": state["verdict"].dict(),
        "metrics": {
            "total_tokens": state["total_tokens"],
            "cost": state.get("final_cost", 0.0)
        },
        "logs": state.get("logs", []), # Save the execution logs too
        "timestamp": timestamp
    }
    
    with open(filename, "w") as f:
        json.dump(data_to_save, f, indent=2)
    
    return filename

def list_snapshots() -> List[str]:
    """Returns a list of available snapshot filenames."""
    if not os.path.exists(SNAPSHOT_DIR):
        return []
    files = [f for f in os.listdir(SNAPSHOT_DIR) if f.endswith(".json")]
    # Sort by newest first
    files.sort(key=lambda x: os.path.getmtime(os.path.join(SNAPSHOT_DIR, x)), reverse=True)
    return files

def load_snapshot(filename: str) -> Dict:
    """Loads a snapshot JSON."""
    filepath = os.path.join(SNAPSHOT_DIR, filename)
    with open(filepath, "r") as f:
        return json.load(f)