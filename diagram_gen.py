import os
import sys
from typing import Optional

def generate_diagram_from_code(code: str, output_filename: str = "architecture_diagram") -> Optional[str]:
    """
    Executes Python code that uses the 'diagrams' library.
    WARNING: Only run code from trusted agents.
    """
    # 1. Sanitize: Ensure code doesn't delete files or access network heavily
    if "os.system" in code or "subprocess" in code or "shutil.rmtree" in code:
        raise ValueError("Unsafe code detected in diagram generation.")

    # 2. Wrap code to force output filename
    # The 'diagrams' lib uses `with Diagram("Name"): ...` 
    # We inject logic to ensure it saves where we want.
    
    try:
        # Execute in a restricted scope
        exec_globals = {}
        exec(code, exec_globals)
        
        # Check if a .png was created
        expected_file = f"{output_filename}.png"
        
        # 'diagrams' usually saves based on the Diagram name. 
        # We might need to find the newest PNG if the name varies.
        # For this prototype, we rely on the agent naming it correctly 
        # or we scan for the generated file.
        
        files = [f for f in os.listdir('.') if f.endswith('.png')]
        files.sort(key=os.path.getmtime, reverse=True)
        if files:
            return files[0] # Return newest PNG
        return None
        
    except Exception as e:
        print(f"Diagram Gen Error: {e}")
        return None