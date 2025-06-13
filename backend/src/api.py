from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import os
import logging
import traceback
from code_agent import CodeAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Code Analysis API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the code agent
agent = CodeAgent(
    llm_provider='gemini',
    api_key=os.getenv('GOOGLE_API_KEY'),
    github_token=os.getenv('GITHUB_TOKEN')
)

class QueryRequest(BaseModel):
    query: str

class LoadRepoRequest(BaseModel):
    repo_url: str

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatSession(BaseModel):
    messages: List[ChatMessage]

# Store chat sessions
chat_sessions: Dict[str, ChatSession] = {}

@app.post("/load-repo")
async def load_repository(request: LoadRepoRequest):
    """Load a repository for analysis"""
    try:
        logger.info(f"Loading repository: {request.repo_url}")
        agent.load_repo_data(request.repo_url)
        return {"status": "success", "message": f"Repository {request.repo_url} loaded successfully"}
    except Exception as e:
        error_msg = f"Error loading repository: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/analyze")
async def analyze_code(request: QueryRequest):
    """Analyze code based on the query"""
    if not agent.current_repo_url:
        error_msg = "No repository loaded. Please load a repository first."
        logger.error(error_msg)
        raise HTTPException(status_code=400, detail=error_msg)
    
    try:
        logger.info(f"Analyzing code with query: {request.query}")
        result = agent.run(request.query)
        return {"response": result}
    except Exception as e:
        error_msg = f"Error analyzing code: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/chat/{session_id}")
async def chat(session_id: str, message: ChatMessage):
    """Handle chat messages with session history and intent identification"""
    try:
        logger.info(f"Processing chat message for session {session_id}: {message.content[:100]}...")
        
        if session_id not in chat_sessions:
            chat_sessions[session_id] = ChatSession(messages=[])
        
        # Add user message to history
        chat_sessions[session_id].messages.append(message)
        
        # Convert chat messages to dict format for the agent
        chat_history = [
            {"role": msg.role, "content": msg.content} 
            for msg in chat_sessions[session_id].messages
        ]
        
        # Get response from agent with chat history for intent identification
        logger.info("Getting response from agent with intent identification...")
        response = agent.run(message.content, chat_history=chat_history)
        
        # Add assistant response to history
        chat_sessions[session_id].messages.append(
            ChatMessage(role="assistant", content=response)
        )
        
        logger.info("Successfully processed chat message")
        return {
            "response": response,
            "history": [{"role": msg.role, "content": msg.content} for msg in chat_sessions[session_id].messages]
        }
    except Exception as e:
        error_msg = f"Error in chat: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/chat/{session_id}/history")
async def get_chat_history(session_id: str):
    """Get chat history for a session"""
    try:
        logger.info(f"Getting chat history for session {session_id}")
        if session_id not in chat_sessions:
            return {"messages": []}
        return {"messages": [{"role": msg.role, "content": msg.content} for msg in chat_sessions[session_id].messages]}
    except Exception as e:
        error_msg = f"Error getting chat history: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@app.delete("/chat/{session_id}")
async def reset_chat(session_id: str):
    """Reset chat session"""
    try:
        logger.info(f"Resetting chat session {session_id}")
        if session_id in chat_sessions:
            del chat_sessions[session_id]
        return {"status": "success", "message": "Chat session reset successfully"}
    except Exception as e:
        error_msg = f"Error resetting chat session: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/repo-status")
async def get_repo_status():
    """Get current repository status"""
    try:
        logger.info("Getting repository status")
        return {
            "loaded": bool(agent.current_repo_url),
            "repo_url": agent.current_repo_url
        }
    except Exception as e:
        error_msg = f"Error getting repository status: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 