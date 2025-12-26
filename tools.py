import os
import io
import contextlib
import time
import shutil
import tempfile
import sys
import asyncio
from pyppeteer import launch
import asyncio
from playwright.async_api import async_playwright

try:
    from cookiecutter.main import cookiecutter
    HAS_COOKIECUTTER = True
except ImportError:
    HAS_COOKIECUTTER = False


def hld_to_mermaid(hld) -> dict:
    """
    Deterministically converts HLD Pydantic object to Mermaid.js strings.
    No LLM involved.
    """
    
    # 1. System Context (Simple)
    # Assumes a central system with external interfaces
    system_context = "graph TD\n"
    system_context += "    User((User))\n"
    system_context += "    System[System Boundary]\n"
    system_context += "    User -->|Uses| System\n"
    
    if hld.architecture_overview.external_interfaces:
        for ext in hld.architecture_overview.external_interfaces:
            # Sanitize name
            safe_ext = ext.replace(" ", "_").replace("-", "_")
            system_context += f"    {safe_ext}[{ext}]\n"
            system_context += f"    System -->|Integrates| {safe_ext}\n"

    # 2. Container Diagram (Components & Database)
    container = "graph TD\n"
    
    # Create nodes for Core Components
    for comp in hld.core_components:
        safe_name = comp.name.replace(" ", "_")
        container += f"    {safe_name}[{comp.name}]\n"
        
        # Add dependencies
        for dep in comp.component_dependencies:
            safe_dep = dep.replace(" ", "_")
            container += f"    {safe_name} --> {safe_dep}\n"
            
    # Add Storage
    for store in hld.data_architecture.storage_choices:
        safe_store = store.technology.replace(" ", "_")
        safe_comp = store.component.replace(" ", "_")
        container += f"    {safe_store}[({store.technology})]\n"
        container += f"    {safe_comp} -->|Reads/Writes| {safe_store}\n"

    # 3. Data Flow (Sequence Diagram)
    data_flow = "sequenceDiagram\n    autonumber\n"
    
    # Naive generation based on event flows or user stories
    # (Since we don't have a strict sequence step list in HLD, we visualize the Event Flows)
    for flow in hld.architecture_overview.event_flows:
        # Assuming flow.components_involved is ordered list: A, B, C
        comps = flow.components_involved
        if len(comps) >= 2:
            for i in range(len(comps) - 1):
                data_flow += f"    {comps[i]}->>{comps[i+1]}: {flow.description}\n"

    return {
        "system_context": system_context,
        "container_diagram": container,
        "data_flow": data_flow
    }



async def run_diagram(mermaid_code):
    """This function checks Mermaid code syntax using a headless browser."""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            await page.set_content(f'''
                <html>
                    <head>
                        <script type="module">
                            import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
                            mermaid.initialize({{startOnLoad: true}});
                            window.onload = () => {{
                                mermaid.render('graphDiv', `{mermaid_code}`, (svgCode) => {{
                                    document.body.innerHTML = svgCode;
                                }});
                            }};
                        </script>
                    </head>
                    <body>
                        <div id="graphDiv"></div>
                    </body>
                </html>
            ''')

            # Wait for the diagram to load or timeout after 5 seconds
            await page.wait_for_selector('#graphDiv', timeout=5000)
            await browser.close()
            return "Mermaid code is valid!"
    except Exception as e:
        return f"Syntax error in Mermaid code: {str(e)}"

# generate_scaffold function remains unchanged
def generate_scaffold(structure, output_dir="./output_project") -> list[str]:
    logs = []
    if structure.cookiecutter_url and "http" in structure.cookiecutter_url and HAS_COOKIECUTTER:
        try:
            cookiecutter(structure.cookiecutter_url, output_dir=output_dir, no_input=True)
            logs.append(f"✅ Hydrated template from {structure.cookiecutter_url}")
        except Exception as e: logs.append(f"⚠️ Cookiecutter failed: {e}")

    base_path = os.path.join(output_dir, "generated_app") 
    for file_spec in structure.starter_files:
        try:
            full_path = os.path.join(base_path, file_spec.filename)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f: f.write(file_spec.content)
            logs.append(f"📄 Created {file_spec.filename}")
        except Exception as e: logs.append(f"❌ Failed to write {file_spec.filename}: {e}")
            
    logs.append(f"✅ Scaffolding complete in {base_path}")
    return logs