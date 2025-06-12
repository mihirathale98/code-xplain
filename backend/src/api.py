from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import os
from code_agent import CodeAgent

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
    llm_provider='openai',
    api_key=os.getenv('OPENAI_API_KEY'),
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
        agent.load_repo_data(request.repo_url)
        return {"status": "success", "message": f"Repository {request.repo_url} loaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze")
async def analyze_code(request: QueryRequest):
    """Analyze code based on the query"""
    if not agent.current_repo_url:
        raise HTTPException(status_code=400, detail="No repository loaded. Please load a repository first.")
    
    try:
        result = agent.run(request.query)
        return {"response": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/{session_id}")
async def chat(session_id: str, message: ChatMessage):
    """Handle chat messages with session history"""
    if not agent.current_repo_url:
        raise HTTPException(status_code=400, detail="No repository loaded. Please load a repository first.")
    
    if session_id not in chat_sessions:
        chat_sessions[session_id] = ChatSession(messages=[])
    
    # Add user message to history
    chat_sessions[session_id].messages.append(message)
    
    # Prepare context from chat history
    context = "\n".join([f"{msg.role}: {msg.content}" for msg in chat_sessions[session_id].messages])
    
    try:
        # Get response from agent
        response = agent.run(context)
        
        # Add assistant response to history
        chat_sessions[session_id].messages.append(
            ChatMessage(role="assistant", content=response)
        )
        
        return {
            "response": response,
            "history": chat_sessions[session_id].messages
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chat/{session_id}/history")
async def get_chat_history(session_id: str):
    """Get chat history for a session"""
    if session_id not in chat_sessions:
        return {"messages": []}
    return {"messages": chat_sessions[session_id].messages}

@app.delete("/chat/{session_id}")
async def reset_chat(session_id: str):
    """Reset chat history for a session"""
    if session_id in chat_sessions:
        del chat_sessions[session_id]
    return {"status": "success"}

@app.get("/repo-status")
async def get_repo_status():
    """Get current repository status"""
    return {
        "loaded": agent.current_repo_url is not None,
        "repo_url": agent.current_repo_url
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 