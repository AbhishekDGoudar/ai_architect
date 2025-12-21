import streamlit as st
import time
import json
from dotenv import load_dotenv

# Import our custom modules
from graph import app_graph
from storage import save_snapshot, list_snapshots, load_snapshot, delete_snapshot
from schemas import HighLevelDesign, LowLevelDesign, JudgeVerdict

# Load environment variables (optional, for default keys)
load_dotenv()

# --- Page Configuration ---
st.set_page_config(
    page_title="AI Architect Studio",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Session State Initialization ---
if "api_key" not in st.session_state:
    st.session_state["api_key"] = ""
if "current_result" not in st.session_state:
    st.session_state["current_result"] = None

# --- Helper: Cost Estimator ---
def calculate_estimate(prompt_text, provider):
    """
    Rough calculation of token usage based on system architecture.
    """
    # 1. Input Tokens (User Prompt) - English avg ~4 chars/token
    input_tokens = len(prompt_text) / 4 
    
    # 2. System Overhead (Prompts + Pydantic Schemas injected by LangChain)
    # Manager: ~800, Lead: ~1000, Judge: ~500 (Context includes HLD/LLD history)
    system_overhead = 2500 
    
    # 3. Output Prediction (Architecture docs are verbose)
    estimated_output = 2000 
    
    total_est = input_tokens + system_overhead + estimated_output
    
    # 4. Pricing (Approximate per 1M tokens as of late 2024/2025)
    rates = {
        "openai": 10.00,  # Blended GPT-4o rate
        "gemini": 3.50,   # Gemini 1.5 Pro
        "claude": 9.00,   # Sonnet 3.5
        "ollama": 0.00    # Free
    }
    cost = (total_est / 1_000_000) * rates.get(provider, 0)
    
    return int(total_est), cost

# ==============================================================================
# SIDEBAR
# ==============================================================================
with st.sidebar:
    st.title("⚙️ Configuration")
    
    # --- 1. Vendor Selection ---
    st.subheader("AI Provider")
    provider = st.selectbox(
        "Select Model Backend",
        ("openai", "gemini", "claude", "ollama"),
        index=1,
        help="Gemini is recommended for cost/performance balance."
    )
    
    # --- 2. API Key Management ---
    if provider != "ollama":
        api_key_input = st.text_input(
            f"{provider.title()} API Key",
            type="password",
            value=st.session_state["api_key"],
            help="This key is used for this session only and not stored permanently."
        )
        st.session_state["api_key"] = api_key_input
    else:
        st.info("Using Local Ollama (No Key Required)")
        st.session_state["api_key"] = "local"

    st.divider()

    # --- 3. Snapshot Manager ---
    st.subheader("📂 Snapshot Manager")
    snapshots = list_snapshots()
    
    selected_file = st.selectbox(
        "Saved Architectures:", 
        options=["(New Run)"] + snapshots,
        index=0
    )
    
    if selected_file != "(New Run)":
        col_load, col_del = st.columns(2)
        
        # Load Button
        if col_load.button("📂 Load"):
            try:
                data = load_snapshot(selected_file)
                # Rehydrate Pydantic models from JSON
                st.session_state["current_result"] = {
                    "hld": HighLevelDesign(**data['hld']),
                    "lld": LowLevelDesign(**data['lld']),
                    "verdict": JudgeVerdict(**data['verdict']),
                    "metrics": data.get("metrics", {}),
                    "logs": data.get("logs", [])
                }
                st.toast(f"Loaded '{selected_file}'", icon="✅")
                time.sleep(0.5)
                st.rerun()
            except Exception as e:
                st.error(f"Corrupt file: {e}")

        # Delete Button
        if col_del.button("🗑️ Delete"):
            success = delete_snapshot(selected_file)
            if success:
                st.toast(f"Deleted {selected_file}", icon="🗑️")
                time.sleep(1.0)
                st.rerun()
            else:
                st.error("Could not delete file.")

# ==============================================================================
# MAIN APPLICATION
# ==============================================================================
st.title("🤖 AI Systems Architect")
st.markdown("Automated generation of **High Level (HLD)** and **Low Level (LLD)** designs with **Self-Correction**.")

# ------------------------------------------------------------------------------
# CASE A: INPUT FORM (No Result Loaded)
# ------------------------------------------------------------------------------
if st.session_state["current_result"] is None:
    
    st.info("👋 Welcome! Describe the system you want to build below.")
    
    user_prompt = st.text_area(
        "System Requirements:", 
        height=200, 
        placeholder="Example: Build a scalable ride-sharing backend like Uber for 50k daily users. Must use SQL.",
        value="Build a scalable URL shortener like Bitly."
    )

    # --- Pre-Run Estimator ---
    if user_prompt:
        est_tokens, est_cost = calculate_estimate(user_prompt, provider)
        with st.expander("📊 Cost & Token Estimate", expanded=False):
            c1, c2 = st.columns(2)
            c1.metric("Est. Tokens", f"~{est_tokens}")
            c2.metric("Est. Cost", f"${est_cost:.4f}")
            st.caption("Includes estimated system prompts and schema definitions.")

    run_btn = st.button("🚀 Generate Architecture", type="primary", use_container_width=True)

    if run_btn:
        # Validation
        if not st.session_state["api_key"]:
            st.error(f"❌ Please enter an API Key for {provider.title()} in the sidebar.")
            st.stop()

        # Execution
        with st.status(f"Running Architect Pipeline on {provider.title()}...", expanded=True) as status:
            
            inputs = {
                "user_request": user_prompt, 
                "provider": provider,
                "api_key": st.session_state["api_key"],
                "retry_count": 0,
                # Metrics initialization
                "total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0,
                "logs": []
            }
            
            try:
                # --- CALLING THE LANGGRAPH ---
                final_state = app_graph.invoke(inputs)
                
                status.update(label="✅ Architecture Generated!", state="complete", expanded=False)
                
                # Save to Session
                st.session_state["current_result"] = {
                    "hld": final_state['hld'],
                    "lld": final_state['lld'],
                    "verdict": final_state['verdict'],
                    "metrics": {
                        "total": final_state['total_tokens'],
                        "prompt": final_state['prompt_tokens'],
                        "completion": final_state['completion_tokens']
                    },
                    "logs": final_state['logs']
                }
                st.rerun()

            except Exception as e:
                st.error(f"Execution Failed: {str(e)}")
                st.error("Please check your API Key and connection.")

# ------------------------------------------------------------------------------
# CASE B: RESULTS DISPLAY (Result Loaded)
# ------------------------------------------------------------------------------
else:
    res = st.session_state["current_result"]
    hld = res['hld']
    lld = res['lld']
    verdict = res['verdict']
    metrics = res['metrics']
    logs = res['logs']

    # --- Toolbar ---
    col_back, col_save, col_spacer = st.columns([1, 1, 4])
    
    if col_back.button("⬅️ Start New Run"):
        st.session_state["current_result"] = None
        st.rerun()
        
    if col_save.button("💾 Save Snapshot"):
        filename = save_snapshot("Run", {
            "user_request": "Snapshot", 
            "hld": hld, "lld": lld, "verdict": verdict,
            "metrics": metrics, "logs": logs
        })
        st.toast(f"Saved to {filename}", icon="✅")

    st.divider()

    # --- Metrics Section ---
    with st.expander("📈 Usage & Logs", expanded=False):
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Tokens", metrics.get("total", 0))
        m2.metric("Input Tokens", metrics.get("prompt", 0))
        m3.metric("Output Tokens", metrics.get("completion", 0))
        
        st.markdown("### Execution Trace")
        for log in logs:
            st.text(f"[{log['time']}] {log['role']}: {log['message']}")

    # --- Architecture View ---
    tab_hld, tab_lld = st.tabs(["🏛️ High Level Design (Manager)", "💻 Low Level Design (Team Lead)"])

    with tab_hld:
        st.subheader("System Overview")
        st.info(hld.system_overview)
        
        c1, c2 = st.columns([2, 1])
        with c1:
            st.markdown("### 📦 Components")
            for comp in hld.components:
                with st.container(border=True):
                    st.markdown(f"**{comp.name}**")
                    st.caption(f"Stack: `{comp.tech_stack}`")
                    st.write(comp.purpose)
        
        with c2:
            st.markdown("### 🧠 Decisions (ADR)")
            for dec in hld.decisions:
                st.success(f"**{dec.title}**: {dec.decision}\n\n_{dec.reasoning}_")

    with tab_lld:
        # Quality Score Header
        score_color = "green" if verdict.is_valid else "red"
        st.markdown(f"### Quality Audit Score: :{score_color}[{verdict.score}/10]")
        if not verdict.is_valid:
            st.warning(f"⚠️ **Judge Feedback:** {verdict.critique}")
        
        col_db, col_api = st.columns(2)
        
        with col_db:
            st.markdown("#### 🗄️ Database Schema")
            for table in lld.database_schema:
                with st.expander(f"Table: {table.table_name}", expanded=True):
                    st.code("\n".join(table.columns), language="sql")
        
        with col_api:
            st.markdown("#### 🔌 API Specifications")
            for api in lld.api_specs:
                with st.expander(f"{api.method} {api.path}", expanded=False):
                    st.write(api.description)