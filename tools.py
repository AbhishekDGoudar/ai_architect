import os
import sys
from cookiecutter.main import cookiecutter

def run_diagram_code(code_str: str, filename="architecture_diagram"):
    """
    Safely executes Python code to generate a diagram.
    """
    try:
        # Patch code to import necessary modules dynamically
        patched_code = f"""
from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import *
from diagrams.aws.database import *
from diagrams.aws.network import *
from diagrams.gcp.compute import *
from diagrams.gcp.database import *
from diagrams.onprem.database import *
from diagrams.onprem.queue import *
from diagrams.programming.language import *
from diagrams.programming.framework import *

{code_str}
"""
        exec_globals = {}
        exec(patched_code, exec_globals)
        
        # Check for output file (diagrams lib typically outputs filename.png)
        # We assume the agent names the diagram consistent with 'filename' or we search for recent pngs
        if os.path.exists(f"{filename}.png"):
            return f"{filename}.png"
        
        # Fallback: search for any PNG created
        files = [f for f in os.listdir('.') if f.endswith('.png')]
        if files:
            files.sort(key=os.path.getmtime, reverse=True)
            return files[0]
            
        return None
    except Exception as e:
        print(f"Diagram Error: {e}")
        return None

def generate_scaffold(structure, output_dir="./output_project"):
    """
    Hybrid Scaffolder: Cookiecutter or Manual.
    """
    log = []
    
    # 1. Cookiecutter Strategy
    if hasattr(structure, 'cookiecutter_url') and structure.cookiecutter_url and "http" in structure.cookiecutter_url:
        try:
            cookiecutter(structure.cookiecutter_url, output_dir=output_dir, no_input=True)
            log.append(f"Hydrated template from {structure.cookiecutter_url}")
            return log
        except Exception as e:
            log.append(f"Template failed: {e}. Falling back to manual generation.")

    # 2. Manual Strategy
    base_path = os.path.join(output_dir, structure.project_name)
    
    for folder in structure.folder_structure:
        path = os.path.join(base_path, folder)
        os.makedirs(path, exist_ok=True)

    for file in structure.files:
        path = os.path.join(base_path, file.filename)
        # Ensure directory exists
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(file.content)
            
    log.append(f"Generated {len(structure.files)} custom files.")
    return log