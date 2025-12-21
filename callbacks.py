from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from typing import Any

class TokenMeter(BaseCallbackHandler):
    def __init__(self):
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Run when LLM ends running to capture usage stats."""
        try:
            # 1. Standard OpenAI/LangChain location
            if response.llm_output and "token_usage" in response.llm_output:
                usage = response.llm_output["token_usage"]
                self._update(usage)
            
            # 2. Google Gemini / Anthropic location (inside generations)
            elif response.generations:
                # Sum up usage across all generations (usually just one)
                for gen_list in response.generations:
                    for gen in gen_list:
                        # Anthropic/Gemini often attach usage_metadata here
                        if hasattr(gen, 'message') and hasattr(gen.message, 'usage_metadata'):
                            self._update(gen.message.usage_metadata)
                            
        except Exception as e:
            print(f"Warning: Could not parse token usage. {e}")

    def _update(self, usage: dict):
        # Normalize keys (some providers use 'input_tokens', others 'prompt_tokens')
        p = usage.get("prompt_tokens") or usage.get("input_tokens") or 0
        c = usage.get("completion_tokens") or usage.get("output_tokens") or 0
        t = usage.get("total_tokens") or (p + c)
        
        self.prompt_tokens += p
        self.completion_tokens += c
        self.total_tokens += t

class LogCollector(BaseCallbackHandler):
    """Captures agent actions for the UI log viewer."""
    def __init__(self):
        self.logs = [] # List of {"role": str, "message": str, "time": str}

    def log(self, role: str, message: str):
        timestamp = time.strftime("%H:%M:%S")
        self.logs.append({"role": role, "message": message, "time": timestamp})

    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any) -> None:
        """Runs when LLM starts generating."""
        # Clean up the prompt preview for display
        preview = prompts[0][:100].replace("\n", " ") + "..."
        self.log("System", f"Sending prompt to LLM: {preview}")

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Runs when LLM finishes."""
        self.log("System", "Received response from LLM.")