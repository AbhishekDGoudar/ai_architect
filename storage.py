import os
import json
import time
from typing import List, Dict, Any, Optional

# Include our schemas for reconstruction
try:
    from schemas import (
        HighLevelDesign, LowLevelDesign, JudgeVerdict, 
        ProjectStructure, ArchitectureDiagrams, DiagramValidationResult
    )
except ImportError:
    # Fallback if schemas aren't found (though they should be)
    HighLevelDesign = None
    LowLevelDesign = None
    JudgeVerdict = None
    ProjectStructure = None
    ArchitectureDiagrams = None
    DiagramValidationResult = None

SNAPSHOT_DIR = "snapshots"

def _to_dict(obj: Any) -> Dict:
    """Helper to convert Pydantic models to dicts for JSON saving."""
    if obj is None: return None
    if hasattr(obj, "model_dump"): return obj.model_dump()
    if hasattr(obj, "dict") and callable(obj.dict): return obj.dict()
    return obj

def get_file_path(project_name: str) -> str:
    if not os.path.exists(SNAPSHOT_DIR): os.makedirs(SNAPSHOT_DIR)
    safe_name = "".join([c for c in project_name if c.isalnum() or c in (' ', '-', '_')]).strip() or "untitled_project"
    return os.path.join(SNAPSHOT_DIR, f"{safe_name}.json")

def save_snapshot(project_name: str, state: Dict):
    """Saves the current state to a JSON file."""
    filepath = get_file_path(project_name)
    
    # Serialize all Pydantic objects to dicts
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
        # Metrics and Logs are usually primitives
        "metrics": state.get("metrics", {}),
        "total_tokens": state.get("total_tokens", 0),
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
    """Returns a list of available snapshot filenames sorted by date."""
    if not os.path.exists(SNAPSHOT_DIR): return []
    try:
        files = [f for f in os.listdir(SNAPSHOT_DIR) if f.endswith(".json")]
        files.sort(key=lambda x: os.path.getmtime(os.path.join(SNAPSHOT_DIR, x)), reverse=True)
        return files
    except OSError: return []

def load_snapshot(filename: str) -> Dict:
    """Loads a snapshot and reconstructs Pydantic objects."""
    filepath = os.path.join(SNAPSHOT_DIR, filename)
    if not os.path.exists(filepath): 
        raise FileNotFoundError(f"Snapshot {filename} not found.")
    
    with open(filepath, "r", encoding="utf-8") as f: 
        data = json.load(f)
        
    # Reconstruct Pydantic objects if they exist in the data
    # This prevents 'AttributeError' in the UI when accessing .dot notation
    if HighLevelDesign and data.get("hld"):
        try: data["hld"] = HighLevelDesign(**data["hld"])
        except Exception as e: print(f"Failed to reconstruct HLD: {e}")

    if LowLevelDesign and data.get("lld"):
        try: data["lld"] = LowLevelDesign(**data["lld"])
        except Exception as e: print(f"Failed to reconstruct LLD: {e}")

    if JudgeVerdict and data.get("verdict"):
        try: data["verdict"] = JudgeVerdict(**data["verdict"])
        except Exception as e: print(f"Failed to reconstruct Verdict: {e}")

    if ProjectStructure and data.get("scaffold"):
        try: data["scaffold"] = ProjectStructure(**data["scaffold"])
        except Exception as e: print(f"Failed to reconstruct Scaffold: {e}")

    if ArchitectureDiagrams and data.get("diagram_code"):
        try: data["diagram_code"] = ArchitectureDiagrams(**data["diagram_code"])
        except Exception as e: print(f"Failed to reconstruct Diagrams: {e}")

    if DiagramValidationResult and data.get("diagram_validation"):
        try: data["diagram_validation"] = DiagramValidationResult(**data["diagram_validation"])
        except Exception as e: print(f"Failed to reconstruct Validation: {e}")

    return data

def delete_snapshot(filename: str) -> bool:
    filepath = os.path.join(SNAPSHOT_DIR, filename)
    try:
        if os.path.exists(filepath): 
            os.remove(filepath)
            return True
        return False
    except OSError: return False