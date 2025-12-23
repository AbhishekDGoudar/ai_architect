import os
import sys
import contextlib
import io
import time

# Robust Import for Cookiecutter
try:
    from cookiecutter.main import cookiecutter
    HAS_COOKIECUTTER = True
except ImportError:
    HAS_COOKIECUTTER = False

def run_diagram_code(code_str: str, filename="architecture_diagram"):
    """
    Safely executes Python code to generate a diagram.
    """
    try:
        # Clean markdown code blocks if present
        clean_code = code_str.replace("```python", "").replace("```", "").strip()
        
        # 1. Pre-load common Diagram classes into globals
        # This acts as a fallback if the LLM forgets imports or writes bad ones.
        exec_globals = {}
        common_imports = """
from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import EC2, ECS, EKS, Lambda
from diagrams.aws.database import RDS, DynamoDB, ElastiCache, Redshift
from diagrams.aws.network import ELB, Route53, VPC, APIGateway
from diagrams.aws.storage import S3, EBS
from diagrams.aws.integration import SQS, SNS
from diagrams.onprem.compute import Server
from diagrams.onprem.database import PostgreSQL, MongoDB, Redis, Cassandra
from diagrams.onprem.queue import Kafka
from diagrams.programming.language import Python, Go, Java, Nodejs
from diagrams.programming.framework import React, Angular, Vue
"""
        # Execute imports first to populate globals
        exec(common_imports, exec_globals)
        
        # 2. Execute the LLM's code
        output_buffer = io.StringIO()
        with contextlib.redirect_stdout(output_buffer), contextlib.redirect_stderr(output_buffer):
             exec(clean_code, exec_globals)
        
        # 3. Check for output file
        # Priority 1: Exact match requested by logic
        if os.path.exists(f"{filename}.png"):
            return f"{filename}.png"
        
        # Priority 2: Check for specific filenames mandated in agents.py
        standard_names = ["system_context.png", "container_diagram.png", "data_flow.png"]
        for name in standard_names:
             if os.path.exists(name):
                 # Verify it was modified recently (last 2 seconds)
                 if time.time() - os.path.getmtime(name) < 2.0:
                     return name
        
        # Priority 3: Fallback to most recently created PNG
        files = [f for f in os.listdir('.') if f.endswith('.png')]
        if files:
            files.sort(key=os.path.getmtime, reverse=True)
            return files[0]
            
        return None
    except Exception as e:
        return f"Diagram Error: {str(e)}"

def generate_scaffold(structure, output_dir="./output_project") -> list[str]:
    """
    Generates the physical files and folders from the ScaffoldingSpec.
    """
    logs = []
    
    # 1. Handle Cookiecutter Template (if provided)
    if structure.cookiecutter_url and "http" in structure.cookiecutter_url:
        if HAS_COOKIECUTTER:
            try:
                cookiecutter(structure.cookiecutter_url, output_dir=output_dir, no_input=True)
                logs.append(f"✅ Hydrated template from {structure.cookiecutter_url}")
            except Exception as e:
                logs.append(f"⚠️ Cookiecutter failed: {e}")
        else:
            logs.append("⚠️ Cookiecutter URL provided but 'cookiecutter' library not installed.")

    # 2. Manual File Generation
    base_path = os.path.join(output_dir, "generated_app") 
    
    if not structure.starter_files:
        logs.append("ℹ️ No starter files defined in spec.")
        return logs

    for file_spec in structure.starter_files:
        try:
            full_path = os.path.join(base_path, file_spec.filename)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(file_spec.content)
                
            logs.append(f"📄 Created {file_spec.filename}")
            
        except Exception as e:
            logs.append(f"❌ Failed to write {file_spec.filename}: {e}")
            
    logs.append(f"✅ Scaffolding complete in {base_path}")
    return logs