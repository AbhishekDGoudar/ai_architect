from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic
from langchain_ollama import ChatOllama

def get_llm(provider: str, api_key: str, model_type: str = "smart"):
    """
    Initializes LLM with a session-specific API Key.
    """
    
    models = {
        "openai": {"fast": "gpt-4o-mini", "smart": "gpt-4.1-mini"},
        "gemini": {"smart": "gemini-2.5-flash", "fast": "gemini-2.5-flash-lite"},
        "claude": {"smart": "claude-3-5-sonnet-20240620", "fast": "claude-3-haiku-20240307"},
        "ollama": {"smart": "qwen3:8b", "fast": "phi4-mini:latest"}
    }

    selected_model = models[provider][model_type]
    temperature = 0

    if provider == "openai":
        return ChatOpenAI(
            model=selected_model, 
            temperature=temperature,
            api_key=api_key
        )
    
    elif provider == "gemini":
        return ChatGoogleGenerativeAI(
            model=selected_model, 
            temperature=temperature,
            convert_system_message_to_human=True,
            google_api_key=api_key
        )
    
    elif provider == "claude":
        return ChatAnthropic(
            model=selected_model, 
            temperature=temperature,
            api_key=api_key
        )
    
    elif provider == "ollama":
        # Ollama typically runs locally without a key, but we accept the arg for consistency
        return ChatOllama(model=selected_model, temperature=temperature, format="json")
    
    raise ValueError(f"Unknown provider: {provider}")