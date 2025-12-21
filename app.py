import streamlit as st
from graph import app_graph

st.set_page_config(page_title="AI Architect", layout="wide")
st.title("AI Architect")

# --- Session State Management ---
if "api_key" not in st.session_state:
    st.session_state["api_key"] = ""

# --- Helper: Cost Estimator ---
def calculate_estimate(prompt_text, provider):
    """
    Rough calculation of token usage based on system architecture.
    """
    # 1. Input Tokens (User Prompt)
    input_tokens = len(prompt_text) / 4 
    
    # 2. System Overhead (Prompts + Pydantic Schemas injected by LangChain)
    # Manager: ~800, Lead: ~1000, Judge: ~500 (Context includes HLD/LLD history)
    system_overhead = 2300 
    
    # 3. Output Prediction (Architecture docs are verbose)
    estimated_output = 1500 
    
    total_est = input_tokens + system_overhead + estimated_output
    
    # 4. Pricing (Approximate per 1M tokens)
    rates = {
        "openai": 10.00,  # Blended GPT-4o rate
        "gemini": 3.50,   # Gemini 1.5 Pro
        "claude": 9.00,   # Sonnet 3.5
        "ollama": 0.00    # Free
    }
    cost = (total_est / 1_000_000) * rates.get(provider, 0)
    
    return int(total_est), cost

# --- Sidebar ---
with st.sidebar:
    st.header("1. Configuration")
    provider = st.selectbox("AI Provider", ("openai", "gemini", "claude", "ollama"), index=1)
    
    if provider != "ollama":
        api_key_input = st.text_input(
            f"{provider.title()} API Key", 
            type="password", 
            value=st.session_state["api_key"],
            help="Key is used for this session only."
        )
        st.session_state["api_key"] = api_key_input
    else:
        st.info("Using Local Ollama")
        st.session_state["api_key"] = "local"

    st.divider()
    
    st.header("2. Requirements")
    user_prompt = st.text_area("System Description:", height=150, 
        value="Build a localized DoorDash clone.")

    # --- PRE-RUN ESTIMATE ---
    if user_prompt:
        est_tokens, est_cost = calculate_estimate(user_prompt, provider)
        st.subheader("📊 Pre-Run Estimate")
        st.caption(f"Estimated Tokens: **~{est_tokens}**")
        st.caption(f"Estimated Cost: **${est_cost:.4f}**")
        
    run_btn = st.button("Generate Designs", type="primary")

# --- Execution ---
if run_btn:
    if not st.session_state["api_key"]:
        st.error("Please enter an API Key to proceed.")
        st.stop()

    with st.status(f"Running Architect Pipeline ({provider})...", expanded=True):
        
        inputs = {
            "user_request": user_prompt, 
            "provider": provider,
            "api_key": st.session_state["api_key"],
            "retry_count": 0,
            "total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0
        }
        
        try:
            # Run Graph
            final_state = app_graph.invoke(inputs)
            st.success("Pipeline Complete!")

            # --- POST-RUN ACTUALS ---
            t_total = final_state['total_tokens']
            t_in = final_state['prompt_tokens']
            t_out = final_state['completion_tokens']
            
            # Simple cost calculator for post-run
            rates = {"openai": 10.0, "gemini": 3.5, "claude": 9.0, "ollama": 0.0}
            actual_cost = (t_total / 1_000_000) * rates.get(provider, 0)

            st.markdown("### 📈 Final Usage Report")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Tokens", t_total, delta=f"{t_total - est_tokens} vs est")
            c2.metric("Input", t_in)
            c3.metric("Output", t_out)
            c4.metric("Actual Cost", f"${actual_cost:.4f}")

            st.divider()
            
            # --- Rendering Results ---
            hld = final_state['hld']
            lld = final_state['lld']
            verdict = final_state['verdict']

            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🏛️ High Level Design")
                st.info(hld.system_overview)
                for c in hld.components:
                    with st.expander(f"📦 {c.name}"):
                        st.write(f"**Stack:** {c.tech_stack}")
                        st.write(c.purpose)
                
                st.markdown("#### Key Decisions")
                for d in hld.decisions:
                    st.success(f"**{d.title}**: {d.decision}")

            with col2:
                st.subheader("💻 Low Level Design")
                
                # Quality Badge
                score_color = "green" if verdict.is_valid else "red"
                st.markdown(f":{score_color}[**QA Verified: {verdict.score}/10**]")
                if not verdict.is_valid:
                    st.warning(f"Issues remaining: {verdict.critique}")

                st.markdown("#### Database Schema")
                for t in lld.database_schema:
                    st.code(f"Table: {t.table_name}\n" + "\n".join(t.columns), language="sql")
                    
                st.markdown("#### API Specs")
                for api in lld.api_specs:
                    st.markdown(f"`{api.method} {api.path}`")

        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.caption("Check your API key and connection.")