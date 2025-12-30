
import os
import requests
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
import pypdf
from io import BytesIO

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


def generate_scaffold(structure, output_dir) -> list[str]:
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

# Ensure knowledge base folder exists
def ensure_knowledge_base_folder():
    if not os.path.exists("knowledge_base"):
        os.makedirs("knowledge_base")

# Download book function
def download_book(book_name, book_url, folder="knowledge_base"):
    """
    Download a book from a URL and save it to the knowledge base folder.
    If the book already exists, it will be skipped.
    """
    ensure_knowledge_base_folder()

    # Path where the book will be saved
    book_filename = os.path.join(folder, f"{book_name}.pdf")

    # Check if the book already exists
    if os.path.exists(book_filename):
        print(f"'{book_name}' already exists, skipping download.")
        return
    
    try:
        # Get the content of the book
        response = requests.get(book_url)

        # Check if request was successful (status code 200)
        if response.status_code == 200:
            # Save the book content to the knowledge base folder
            with open(book_filename, "wb") as file:
                file.write(response.content)  # Write binary content (PDF)

            print(f"'{book_name}' downloaded and saved to {book_filename}")
        else:
            print(f"Failed to download '{book_name}', Status code: {response.status_code}")

    except Exception as e:
        print(f"Error downloading '{book_name}': {e}")

def convert_to_raw_url(github_url):
    """
    Converts a GitHub blob URL to a raw URL.
    """
    if 'github.com' in github_url:
        # Replace "blob" with "raw" in the URL to get the raw file
        raw_url = github_url.replace('github.com', 'raw.githubusercontent.com').replace('/blob/', '/')
        return raw_url
    return ""


books_map = {
        "Azure for Architect": "https://tanthiamhuat.wordpress.com/wp-content/uploads/2019/09/azure_for_architects.pdf",
        "AWS for Architect": "https://d1.awsstatic.com/whitepapers/aws-overview.pdf",
        "GCP for Architect": "https://www.citadelcloudmanagement.com/wp-content/uploads/2023/05/2a1631cf2dcc736f8330e7d54571ba13Google-Cloud-Platform-in-Action-PDFDrive-.pdf",
        "Design Patterns": "https://www.javier8a.com/itc/bd1/articulo.pdf",
        "Big Book on Data Engineering": "https://www.databricks.com/sites/default/files/2025-11/big-book-data-engineering.pdf",
        "Fundamentals of Software Architecture": "https://github.com/littlee/littlee.github.io/raw/master/OReilly.Fundamentals.of.Software.Architecture.2020.1.pdf",
        "Microservices Architecture": convert_to_raw_url("https://github.com/namhoangduc99/TargetOf2018/blob/master/Sam%20Newman-Building%20Microservices-O'Reilly%20Media%20(2015).pdf"),
        "Domain Driven Design": convert_to_raw_url("https://github.com/gmoral/Books/blob/master/Domain%20Driven%20Design%20Tackling%20Complexity%20in%20the%20Heart%20of%20Software%20-%20Eric%20Evans.pdf"),
        #"Clean Architecture": convert_to_raw_url("https://github.com/GunterMueller/Books-3/blob/master/Clean%20Architecture%20A%20Craftsman%20Guide%20to%20Software%20Structure%20and%20Design.pdf"),"
       }

# Function to download multiple books
def download_multiple_books(books_map = books_map, folder="knowledge_base"):
    for book_name, book_url in books_map.items():
        download_book(book_name, book_url, folder)


def extract_text_from_file(uploaded_file) -> str:
    """Extracts text from PDF or TXT bytes in memory."""
    try:
        # 1. Handle PDF
        if uploaded_file.type == "application/pdf":
            reader = pypdf.PdfReader(BytesIO(uploaded_file.getvalue()))
            text = []
            for page in reader.pages:
                text.append(page.extract_text())
            return "\n".join(text)
            
        # 2. Handle Text
        elif "text" in uploaded_file.type:
            return str(uploaded_file.read(), "utf-8")
            
        else:
            return "Unsupported file format. Please upload PDF or TXT."
            
    except Exception as e:
        return f"Error reading file: {str(e)}"