import os
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from openai import AsyncOpenAI
from openai.types.shared.reasoning import Reasoning
from agents import FileSearchTool, WebSearchTool, Agent, ModelSettings, Runner, RunConfig

# Import configuration and prompt
from config import API_KEY, KB_VECTOR_STORE_ID, PRIMARY_AGENT_MODEL
from prompts import SYSTEM_DIRECTIVE

# Initialize the async client
ai_client = AsyncOpenAI(api_key=API_KEY)

# ==========================================
# 1. TOOL DEFINITIONS
# ==========================================
# Tool for querying the uploaded ANC JSON guidelines
anc_knowledge_tool = FileSearchTool(
    vector_store_ids=[KB_VECTOR_STORE_ID]
)

# Tool for fallback web searches, optimized for speed
authoritative_web_tool = WebSearchTool(
    search_context_size="medium",
    user_location={"type": "approximate"}
)


# ==========================================
# 2. DATA MODELS
# ==========================================
class QueryPayload(BaseModel):
    """Defines the expected input structure from the UI tier."""
    current_prompt: str
    chat_history: Optional[List[Dict[str, Any]]] = None


# ==========================================
# 3. AGENT FACTORY
# ==========================================
def create_anc_agent() -> Agent:
    """Constructs the conversational agent with tools and strict directives."""
    return Agent(
        name="Antenatal Care Information Agent",
        instructions=SYSTEM_DIRECTIVE,
        model=PRIMARY_AGENT_MODEL,
        tools=[anc_knowledge_tool, authoritative_web_tool],
        model_settings=ModelSettings(
            store=True,
            reasoning=Reasoning(
                effort="low",
                summary="auto"
            )
        )
    )


# ==========================================
# 4. EXECUTION WORKFLOW
# ==========================================
async def execute_agent_run(payload: QueryPayload) -> dict:
    """Processes the conversation history and runs the agent."""
    
    formatted_history = []
    
    # Helper to ensure text format consistency
    def format_text(content_field) -> str:
        if isinstance(content_field, str):
            return content_field
        if isinstance(content_field, (list, tuple)):
            return " ".join(str(part) for part in content_field)
        return str(content_field)

    # Reconstruct the conversation context for the agent
    if payload.chat_history:
        for message in payload.chat_history:
            role = message.get("role")
            content = message.get("content")
            
            if role in {"user", "assistant"} and content:
                content_type = "output_text" if role == "assistant" else "input_text"
                formatted_history.append({
                    "role": role,
                    "content": [{"type": content_type, "text": format_text(content)}]
                })
    else:
        # If no history, just pass the current prompt
        formatted_history.append({
            "role": "user",
            "content": [{"type": "input_text", "text": payload.current_prompt}]
        })

    # Initialize agent and execute
    anc_agent = create_anc_agent()
    
    try:
        execution_result = await Runner.run(
            anc_agent,
            input=formatted_history,
            run_config=RunConfig(trace_metadata={"__trace_source__": "anc-agent-module"})
        )
        
        # Extract and return the final string response
        return {"response": execution_result.final_output_as(str)}
        
    except Exception as e:
        return {"response": f"An internal system error occurred: {str(e)}"}