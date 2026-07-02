# Quick fix to add at line 30 in agent.py
# Add this import at the top
from openai import OpenAI
import anthropic
import os

# Replace the __init__ LLM initialization section with:
def init_llm_client(self, llm_provider, model):
    self.llm_provider = llm_provider
    self.model = model
    
    if llm_provider == "openai":
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    elif llm_provider == "anthropic":
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    elif llm_provider == "groq":
        # Groq uses OpenAI-compatible API
        self.client = OpenAI(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1"
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {llm_provider}")
