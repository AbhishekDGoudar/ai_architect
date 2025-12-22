import streamlit as st
import time
import json
import zlib
import zipfile
import io
import streamlit.components.v1 as components
from dotenv import load_dotenv

# Import custom modules
from graph import app_graph
from storage import save_snapshot, list_snapshots, load_snapshot, delete_snapshot, check_snapshot_exists
from knowledge import knowledge
from tools import generate_scaffold

# Load environment variables
load_dotenv()

# --- Page Configuration ---
st.set_page_config(
    page_title="AI Architect Studio",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Session State Initialization ---
if "api_key" not in st.session_state:
    st.session_state["api_key"] = ""
if "current_result" not in st.session_state:
    st.session_state["current_result"] = None
if "project_name" not in st.session_state:
    st.session_state["project_name"] = ""

# ==============================================================================
# 🛠️ HELPER FUNCTIONS
# ==============================================================================

def create_zip(scaffold):
    """Creates a downloadable ZIP file from the scaffold object."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for folder in scaffold.folder_structure:
            zip_file.writestr(f"{folder}/.gitkeep", "")
        for file in scaffold.files:
            zip_file.writestr(file.filename, file.content)
    buffer.seek(0)
    return buffer

def base64_encode_plantuml(input_bytes):
    """Custom Base64 encoding for PlantUML."""
    _b64_str = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_"
    res = ""
    i = 0
    while i < len(input_bytes):
        b1 = input_bytes[i]
        b2 = input_bytes[i+1] if i+1 < len(input_bytes) else 0
        b3 = input_bytes[i+2] if i+2 < len(input_bytes) else 0
        c1 = b1 >> 2
        c2 = ((b1 & 0x3) << 4) | (b2 >> 4)
        c3 = ((b2 & 0xF) << 2) | (b3 >> 6)
        c4 = b3 & 0x3F
        res += _b64_str[c1] + _b64_str[c2]
        if i+1 < len(input_bytes): res += _b64_str[c3]
        if i+2 < len(input_bytes): res += _b64_str[c4]
        i += 3
    return res

def render_plantuml(code: str, caption: str):
    """Encodes and renders PlantUML via official server."""
    try:
        if "@startuml" not in code:
            code = f"@startuml\n{code}\n@enduml"
        zlibbed = zlib.compress(code.encode('utf-8'))
        compressed = zlibbed[2:-4] 
        encoded = base64_encode_plantuml(compressed)
        url = f"http://www.plantuml.com/plantuml/svg/{encoded}"
        st.image(url, caption=caption, use_container_width=True)
    except Exception as e:
        st.error(f"PlantUML Error: {e}")
        st.code(code, language="text")

def render_mermaid(code: str, height=400):
    """Renders Mermaid.js via HTML injection."""
    clean_code = code.replace("```mermaid", "").replace("```", "").strip()
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <body>
        <script type="module">
            import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
            mermaid.initialize({{ startOnLoad: true, theme: 'neutral', securityLevel: 'loose' }});
        </script>
        <div class="mermaid">
            {clean_code}
        </div>
    </body>
    </html>
    """
    components.html(html_code, height=height, scrolling=True)

def render_diagram(code: str, caption: str = "Diagram"):
    """Hybrid Renderer: Detects format (PlantUML vs Mermaid)."""
    if not code: return
    if "@startuml" in code or "package " in code or "node " in code:
        render_plantuml(code, caption)
    elif any(x in code for x in ["graph TD", "sequenceDiagram", "classDiagram", "C4Context"]):
        render_mermaid(code)
    else:
        # Fallback to text if ambiguous
        st.code(code, language="text")

# ==============================================================================
# SIDEBAR
# ==============================================================================
with st.sidebar:
    st.header("Configuration")
    
    # 1. Context Uploader (New)
    st.subheader("Project Context")
    uploaded_files = st.file_uploader(
        "Upload PRDs, Legacy Code, or Docs:", 
        type=["pdf", "txt", "md"], 
        accept_multiple_files=True
    )
    
    if uploaded_files:
        st.warning("Files are available for this session only and will not be permanently stored.")
        if st.button("Process & Ingest Files"):
            with st.spinner("Analyzing uploaded context..."):
                results = []
                for f in uploaded_files:
                    msg = knowledge.ingest_upload(f)
                    results.append(msg)
                for res in results:
                    if "Ingested" in res: st.success(res)
                    else: st.error(res)
    else:
        st.caption("Uploads are transient and cleared on restart.")

    st.divider()

    # 2. Knowledge Sources
    st.subheader("Knowledge Sources")
    use_web = st.checkbox("Web Search (Freshness)", value=True)
    use_kb = st.checkbox("Internal/Uploaded Knowledge", value=True)
    
    st.divider()

    # 3. AI Provider
    st.subheader("AI Provider")
    provider = st.selectbox("Select Model Backend", ("openai", "gemini", "claude", "ollama"), index=1)
    
    if provider != "ollama":
        st.session_state["api_key"] = st.text_input(f"{provider.title()} API Key", type="password", value=st.session_state["api_key"])
    else:
        st.info("Using Local Ollama")
        st.session_state["api_key"] = "local"

    st.divider()
    
    # 4. Snapshots
    st.subheader("Snapshot Manager")
    snapshots = list_snapshots()
    selected_file = st.selectbox("Saved Runs:", ["(New Run)"] + snapshots)
    
    if selected_file != "(New Run)":
        if st.button("Load Snapshot"):
            try:
                data = load_snapshot(selected_file)
                st.session_state["current_result"] = data
                st.session_state["project_name"] = data.get("project_name", selected_file.replace(".json", ""))
                st.rerun()
            except Exception as e:
                st.error(f"Corrupt file: {e}")

# ==============================================================================
# MAIN APPLICATION
# ==============================================================================
st.title("AI Systems Architect")
st.markdown("Automated generation of **Enterprise-Grade** design documents covering **22 architectural points**.")

# ------------------------------------------------------------------------------
# CASE A: INPUT FORM (No Result Loaded)
# ------------------------------------------------------------------------------
if st.session_state["current_result"] is None:
    
    st.info("Upload specific requirements (PRD/PDF) in the sidebar to ground the architecture.")
    
    project_name = st.text_input(
        "Project Name", 
        value=st.session_state.get("project_name", ""),
        placeholder="e.g., Enterprise URL Shortener"
    )
    st.session_state["project_name"] = project_name
    
    user_prompt = st.text_area(
        "System Requirements:", 
        height=200, 
        placeholder="Example: Build a scalable ride-sharing backend like Uber for 50k daily users.",
        value="Build a scalable generic backend."
    )

    if st.button("Generate Architecture", type="primary"):
        if not st.session_state["api_key"]:
            st.error(f"Please enter an API Key for {provider}.")
            st.stop()
        if not project_name.strip():
            st.error("Please provide a Project Name.")
            st.stop()

        with st.status(f"Running Architect Pipeline on {provider}...", expanded=True) as status:
            inputs = {
                "user_request": user_prompt, 
                "provider": provider,
                "api_key": st.session_state["api_key"],
                "retry_count": 0,
                "total_tokens": 0,
                "logs": []
            }
            try:
                final_state = app_graph.invoke(inputs)
                status.update(label="Architecture Generated!", state="complete", expanded=False)
                
                # Store Full State (Unified Dictionary)
                st.session_state["current_result"] = {
                    "hld": final_state.get('hld'),
                    "lld": final_state.get('lld'),
                    "verdict": final_state.get('verdict'),
                    "scaffold": final_state.get('scaffold'),
                    "diagram_path": final_state.get('diagram_path'),
                    "metrics": final_state.get('metrics', {}),
                    "logs": final_state.get('logs', []),
                    "project_name": project_name
                }
                st.rerun()

            except Exception as e:
                st.error(f"Execution Failed: {str(e)}")

# ------------------------------------------------------------------------------
# CASE B: RESULTS DISPLAY (Result Loaded)
# ------------------------------------------------------------------------------
else:
    res = st.session_state["current_result"]
    hld = res.get('hld', {})
    lld = res.get('lld', {})
    verdict = res.get('verdict', {})
    scaffold = res.get('scaffold', {})
    metrics = res.get('metrics', {})
    diagram_path = res.get('diagram_path')

    # --- Toolbar ---
    col_back, col_save, col_spacer = st.columns([1, 1, 4])
    if col_back.button("Start New Run"):
        st.session_state["current_result"] = None
        st.rerun()
        
    if col_save.button("Save Project"):
        p_name = st.session_state.get("project_name", "Untitled")
        save_data = st.session_state["current_result"]
        filename = save_snapshot(p_name, save_data)
        st.success(f"Saved project to {filename}")

    st.divider()
    
    # --- Quality Metrics ---
    st.subheader(f"Project: {st.session_state.get('project_name', 'Untitled')}")
    m_col1, m_col2, m_col3 = st.columns(3)
    with m_col1:
        sec_score = metrics.get('security_score', 0)
        st.metric("Security Score", f"{sec_score:.2f}/1.0")
    with m_col2:
        issues = metrics.get('red_team_issues', [])
        st.metric("Red Team Issues", len(issues))
    with m_col3:
        st.metric("Iterations", res.get('retry_count', 0))

    if issues:
        with st.expander("Review Security Issues"):
            for issue in issues:
                st.error(f"Issue: {issue}")

    # --- TABS: HLD / LLD / CODE ---
    tab_hld, tab_lld, tab_code = st.tabs(["High Level Design (HLD)", "Low Level Design (LLD)", "Code & Scaffold"])

    # ==========================================
    # HLD VISUALIZATION
    # ==========================================
    with tab_hld:
        # 1. Generated Python Diagram (Primary)
        if diagram_path:
            st.image(diagram_path, caption="Architecture Diagram (Generated)", use_container_width=True)

        # 2. Business Context
        if isinstance(hld, dict) and "business_context" in hld:
            business_context = hld["business_context"]
            st.header("1. Business Context")
            st.markdown(f"**Problem:** {business_context.get('problem_statement', 'No problem statement available')}")
            
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Goals & Metrics**")
                for item in business_context.get('business_goals', []):
                    st.success(f"- {item}")
            with c2:
                st.markdown("**Constraints**")
                for item in business_context.get('assumptions_constraints', []):
                    st.warning(f"- {item}")
        else:
            st.error("Invalid or missing 'business_context' in HLD.")
            
        # 3. Architecture Overview & Legacy Diagrams
        if isinstance(hld, dict) and "architecture_overview" in hld:
            st.header("2. Architecture Overview")
            st.markdown(f"**Style:** `{hld['architecture_overview'].get('style', 'Unknown')}`")
            st.markdown(f"**Context:** {hld['architecture_overview'].get('system_context_diagram_desc', 'No context available')}")

            # Legacy Diagrams Support (If present in HLD)
            if "diagrams" in hld:
                st.divider()
                st.subheader("Structural Diagrams")
                t_ctx, t_cont = st.tabs(["System Context", "Containers"])
                with t_ctx: render_diagram(hld["diagrams"].get('system_context', ""), "System Context")
                with t_cont: render_diagram(hld["diagrams"].get('container_diagram', ""), "Container Diagram")

        # 4. Core Components
        if isinstance(hld, dict) and "core_components" in hld:
            st.header("3. Core Components")
            cols = st.columns(3)
            for idx, comp in enumerate(hld["core_components"]):
                with cols[idx % 3]:
                    with st.container(border=True):
                        st.subheader(comp.get('name', 'Unnamed Component'))
                        st.write(comp.get('responsibility', 'No description'))
                        st.caption(f"Protocols: {', '.join(comp.get('communication_protocols', []))}")

        # 5. Data & NFRs
        c1, c2 = st.columns(2)
        with c1:
            if isinstance(hld, dict) and "data_architecture" in hld:
                st.container(border=True)
                st.header("Data Architecture")
                st.markdown(f"**Consistency:** `{hld['data_architecture'].get('consistency_model', 'Unknown')}`")
                st.json(hld['data_architecture'].get('storage_choices', {}))
        with c2:
            if isinstance(hld, dict) and "security_compliance" in hld:
                st.container(border=True)
                st.header("Security & Compliance")
                st.markdown(f"**Auth:** {hld['security_compliance'].get('authentication_strategy', 'Not defined')}")
                st.markdown(f"**Encryption:** {hld['security_compliance'].get('encryption_at_rest', 'Not specified')}")
            
    # ==========================================
    # LLD VISUALIZATION
    # ==========================================
    with tab_lld:
        # Verdict Display
        if verdict:
            if verdict.get('is_valid', False):
                st.success(f"Verdict: Approved ({verdict.get('score', 0)}/10)")
            else:
                st.error(f"Verdict: Rejected - {verdict.get('critique', 'No critique provided')}")
            
        st.divider()

        # Detailed Components
        if isinstance(lld, dict) and "detailed_components" in lld:
            st.subheader("12. Component Internal Design")
            for dcomp in lld["detailed_components"]:
                with st.expander(f"Component: {dcomp.get('component_name', 'Unnamed Component')}", expanded=False):
                    st.markdown("**Class Structure:**")
                    st.code(dcomp.get('class_structure_desc', 'No description available'), language="text")

        # API Spec
        if isinstance(lld, dict) and "api_design" in lld:
            st.subheader("13. API Specification")
            for api in lld["api_design"]:
                with st.container(border=True):
                    st.markdown(f"**{api.get('method', 'GET')}** {api.get('endpoint', '/path')}")
                    st.text(f"Req: {api.get('request_schema', 'N/A')}")
                    st.text(f"Res: {api.get('response_schema', 'N/A')}")

        # Implementation
        st.divider()
        st.subheader("Implementation Strategy")
        
        t1, t2, t3 = st.tabs(["Logic", "Security Flow", "Ops"])
        with t1:
            st.markdown(f"**Core Algorithms:**\n{lld.get('business_logic', {}).get('core_algorithms', 'No core algorithms defined')}")
        with t2:
            render_diagram(lld.get('security_implementation', {}).get('auth_flow_diagram_desc', ""), "Auth Flow")
        with t3:
            st.markdown(f"**Runbooks:** {lld.get('operational_readiness', {}).get('runbook_summary', 'No runbooks defined')}")

    # ==========================================
    # CODE & SCAFFOLD
    # ==========================================
    with tab_code:
        if scaffold:
            st.header(f"Project Scaffolding: {scaffold.get('project_name', 'Untitled Project')}")
            
            # Download
            zip_buffer = create_zip(scaffold)
            st.download_button(
                label="Download Project (.zip)",
                data=zip_buffer,
                file_name=f"{scaffold.get('project_name', 'Untitled')}.zip",
                mime="application/zip",
                type="primary"
            )
            
            st.divider()
            
            c_struc, c_prev = st.columns([1, 2])
            
            with c_struc:
                st.subheader("Folder Structure")
                for folder in scaffold.get('folder_structure', []):
                    st.text(f"📁 {folder}")
                for file in scaffold.get('files', []):
                    st.text(f"📄 {file.filename}")
                    
                st.subheader("Setup Commands")
                for cmd in scaffold.get('setup_commands', []):
                    st.code(cmd, language="bash")
            
            with c_prev:
                st.subheader("File Preview")
                files_to_show = [f.filename for f in scaffold.get('files', [])]
                selected_file_name = st.selectbox("Select file to view:", files_to_show)
                
                selected_file = next((f for f in scaffold.get('files', []) if f.filename == selected_file_name), None)
                if selected_file:
                    st.code(selected_file.content, language=selected_file.language)
        else:
            st.info("No scaffolding generated yet. Run the pipeline first.")
