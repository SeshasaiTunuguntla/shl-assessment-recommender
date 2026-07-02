"""
FastAPI Application

Exposes /health and /chat endpoints for the SHL Assessment Recommender.
"""

import os
import time
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from ..agent.agent import AssessmentAgent
from ..retrieval import AssessmentRetriever

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="SHL Assessment Recommender",
    description="Conversational agent for SHL assessment recommendations",
    version="1.0.0"
)

# Global state for agent and retriever
retriever: AssessmentRetriever = None
agent: AssessmentAgent = None
startup_time: float = None


@app.on_event("startup")
async def startup_event():
    """Initialize retriever and agent on startup."""
    global retriever, agent, startup_time
    startup_time = time.time()
    
    print("Initializing SHL Assessment Recommender...")
    
    # Initialize retriever
    catalog_path = os.getenv("CATALOG_PATH", "data/catalog/shl_catalog.json")
    retriever = AssessmentRetriever(catalog_path=catalog_path)
    
    try:
        retriever.load_catalog()
        retriever.build_index()
        print(f"Loaded {len(retriever.assessments)} assessments")
    except FileNotFoundError:
        print("Warning: Catalog not found. Run scraper first!")
        # For testing, create empty catalog
        retriever.assessments = []
    
    # Initialize agent
    llm_provider = os.getenv("LLM_PROVIDER", "openai")
    llm_model = os.getenv("LLM_MODEL", "gpt-4-turbo-preview")
    
    agent = AssessmentAgent(
        retriever=retriever,
        llm_provider=llm_provider,
        model=llm_model
    )
    
    print("Agent initialized successfully!")


# Request/Response models
class Message(BaseModel):
    """Single conversation message."""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Chat endpoint request."""
    messages: List[Message] = Field(..., description="Conversation history")


class Recommendation(BaseModel):
    """Assessment recommendation."""
    name: str = Field(..., description="Assessment name")
    url: str = Field(..., description="Assessment URL from SHL catalog")
    test_type: str = Field(..., description="Test type code (P/K/A/S/O)")


class ChatResponse(BaseModel):
    """Chat endpoint response."""
    reply: str = Field(..., description="Agent's response text")
    recommendations: List[Recommendation] = Field(
        default=[],
        description="Assessment recommendations (empty when clarifying/refusing)"
    )
    end_of_conversation: bool = Field(
        default=False,
        description="Whether the agent considers the conversation complete"
    )


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns status 200 with {"status": "ok"} when service is ready.
    Allows up to 2 minutes for cold start on first call.
    """
    global startup_time
    
    # Check if still in startup phase
    if agent is None or retriever is None:
        elapsed = time.time() - (startup_time or time.time())
        if elapsed < 120:  # 2 minute grace period
            return {"status": "initializing", "elapsed": elapsed}
        else:
            raise HTTPException(status_code=503, detail="Service failed to initialize")
    
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Conversational chat endpoint.
    
    Takes full conversation history and returns agent's next response
    with optional recommendations.
    
    Stateless - all conversation context must be in the request.
    """
    global agent
    
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    # Validate request
    if not request.messages:
        raise HTTPException(status_code=400, detail="Messages cannot be empty")
    
    if len(request.messages) > 16:  # 8 turns = 16 messages
        raise HTTPException(status_code=400, detail="Conversation exceeds 8 turn limit")
    
    # Convert messages to dict format
    messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
    
    try:
        # Process conversation
        result = agent.chat(messages)
        
        # Validate recommendations are from catalog
        validated_recommendations = []
        for rec in result.get("recommendations", []):
            # Verify this assessment exists in catalog
            if any(a['name'] == rec['name'] for a in retriever.assessments):
                validated_recommendations.append(Recommendation(**rec))
        
        return ChatResponse(
            reply=result["reply"],
            recommendations=validated_recommendations,
            end_of_conversation=result.get("end_of_conversation", False)
        )
        
    except Exception as e:
        print(f"Error processing chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "SHL Assessment Recommender",
        "version": "1.0.0",
        "endpoints": {
            "/health": "GET - Health check",
            "/chat": "POST - Conversational interface",
            "/docs": "GET - API documentation"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("API_PORT", 8000))
    host = os.getenv("API_HOST", "0.0.0.0")
    
    uvicorn.run(app, host=host, port=port)
