"""
HealthLake Agent API - REST API for React frontend.

This module provides a clean REST API for the React chatbot to interact
with the HealthLake agent.
"""

import os
import uuid
import logging
from typing import Dict, List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import json
import asyncio

from agent import get_agent_instance
from models.session import SessionContext, UserRole
from models.agent_response import AgentResponse
from services.interaction_logger import InteractionLogger

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="HealthLake Agent API",
    description="AI agent API for AWS HealthLake FHIR data",
    version="2.0.0"
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
agent = None
sessions: Dict[str, List[Dict]] = {}
interaction_logger = None


# ============================================================================
# Request/Response Models
# ============================================================================

class ChatRequest(BaseModel):
    """Chat request from frontend"""
    message: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    user_role: Optional[str] = "service_rep"
    active_member_id: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "What conditions does this patient have?",
                "session_id": "user-123",
                "user_id": "rep-456",
                "user_role": "service_rep",
                "active_member_id": "patient-789"
            }
        }


class ChatResponse(BaseModel):
    """Chat response to frontend"""
    response: str
    session_id: str
    timestamp: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "response": "Based on the FHIR data, this patient has...",
                "session_id": "user-123",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class SessionInfo(BaseModel):
    """Session information"""
    session_id: str
    message_count: int
    user_id: Optional[str] = None
    user_role: Optional[str] = None


class HealthCheck(BaseModel):
    """Health check response"""
    status: str
    agent_ready: bool
    timestamp: str


# ============================================================================
# Startup/Shutdown
# ============================================================================

@app.on_event("startup")
def startup_event():
    """Initialize agent on startup"""
    global agent, interaction_logger
    
    logger.info("🚀 Starting HealthLake Agent API...")
    
    try:
        # Initialize agent
        agent = get_agent_instance()
        logger.info("✅ Agent initialized")
        
        # Initialize interaction logger
        interaction_logger = InteractionLogger()
        logger.info("✅ Interaction logger initialized")
        
        logger.info("✅ API ready for requests")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize: {str(e)}", exc_info=True)
        raise


@app.on_event("shutdown")
def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🛑 Shutting down...")
    logger.info("✅ Cleanup complete")


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/health", response_model=HealthCheck)
async def health_check():
    """
    Health check endpoint
    
    Returns API status and readiness
    """
    return HealthCheck(
        status="healthy",
        agent_ready=agent is not None,
        timestamp=datetime.utcnow().isoformat()
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint for React frontend
    
    Send a message to the agent and get a response.
    The agent maintains conversation context per session.
    
    Args:
        request: ChatRequest with message and context
    
    Returns:
        ChatResponse with agent's response
    """
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    # Generate session ID if not provided
    session_id = request.session_id or str(uuid.uuid4())
    
    # Initialize session if new
    if session_id not in sessions:
        sessions[session_id] = []
    
    try:
        # Create session context
        context = SessionContext(
            user_id=request.user_id or "anonymous",
            user_role=UserRole(request.user_role or "service_rep"),
            active_member_id=request.active_member_id,
            session_id=session_id
        )
        
        # Add user message to history
        sessions[session_id].append({
            "role": "user",
            "content": request.message,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Log interaction start
        if interaction_logger:
            interaction_logger.log_interaction_start(
                session_id=session_id,
                user_id=context.user_id,
                query=request.message,
                context=context.to_dict()
            )
        
        # Get response from agent
        from agent import process_query
        result = process_query(
            query=request.message,
            session_id=session_id,
            context=context
        )
        
        response_text = result['text']
        
        # Add agent response to history
        sessions[session_id].append({
            "role": "assistant",
            "content": response_text,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Log interaction completion
        if interaction_logger:
            interaction_logger.log_interaction_complete(
                session_id=session_id,
                response=response_text,
                metadata=result.get('metadata', {})
            )
        
        return ChatResponse(
            response=response_text,
            session_id=session_id,
            timestamp=datetime.utcnow().isoformat()
        )
    
    except Exception as e:
        logger.error(f"Error processing chat: {str(e)}", exc_info=True)
        
        # Log error
        if interaction_logger:
            interaction_logger.log_interaction_error(
                session_id=session_id,
                error=str(e)
            )
        
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions", response_model=List[SessionInfo])
async def list_sessions():
    """
    List all active chat sessions
    
    Returns list of session IDs and their message counts
    """
    return [
        SessionInfo(
            session_id=session_id,
            message_count=len(messages)
        )
        for session_id, messages in sessions.items()
    ]


@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """
    Get conversation history for a session
    
    Args:
        session_id: Session identifier
    
    Returns:
        Conversation history with all messages
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "messages": sessions[session_id],
        "message_count": len(sessions[session_id])
    }


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a chat session
    
    Args:
        session_id: Session identifier
    
    Returns:
        Success message
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    del sessions[session_id]
    return {"message": "Session deleted", "session_id": session_id}


@app.post("/sessions/{session_id}/clear")
async def clear_session(session_id: str):
    """
    Clear conversation history for a session (keeps session alive)
    
    Args:
        session_id: Session identifier
    
    Returns:
        Success message
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    sessions[session_id] = []
    return {"message": "Session cleared", "session_id": session_id}


@app.post("/chat/agentcore")
async def chat_agentcore(request: ChatRequest):
    """
    Chat endpoint that uses AgentCore deployed agent
    
    This endpoint calls the deployed AgentCore agent instead of the local agent.
    Useful for testing the production deployment.
    
    Args:
        request: ChatRequest with message and context
    
    Returns:
        ChatResponse with agent's response
    """
    import subprocess
    
    # Generate session ID if not provided
    session_id = request.session_id or str(uuid.uuid4())
    agent_name = getattr(request, 'agent_name', 'healthlake_agent')
    
    try:
        # Build AgentCore CLI command
        payload = {
            'prompt': request.message,
            'session_id': session_id,
            'context': {
                'user_id': request.user_id or 'web-user',
                'user_role': request.user_role or 'admin',
                'active_member_id': request.active_member_id
            }
        }
        
        # Set AWS environment
        env = os.environ.copy()
        env['AWS_PROFILE'] = env.get('AWS_PROFILE', 'himssdemo')
        env['AWS_REGION'] = env.get('AWS_REGION', 'us-west-2')
        
        # Call AgentCore CLI
        cmd = [
            'agentcore', 'invoke',
            json.dumps(payload),
            '--agent', agent_name
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=60
        )
        
        if result.returncode == 0:
            # Parse the response
            try:
                response_data = json.loads(result.stdout)
                response_text = response_data.get('result', result.stdout)
            except json.JSONDecodeError:
                response_text = result.stdout
            
            return ChatResponse(
                response=response_text,
                session_id=session_id,
                timestamp=datetime.utcnow().isoformat()
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"AgentCore error: {result.stderr or result.stdout}"
            )
            
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="AgentCore request timed out")
    except Exception as e:
        logger.error(f"Error calling AgentCore: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Streaming chat endpoint that shows the agent's thinking process
    
    Streams events as Server-Sent Events (SSE):
    - thinking: Agent's reasoning steps
    - tool_use: When agent uses a tool
    - tool_result: Results from tool execution
    - content: Final response chunks
    - done: Completion signal
    
    Args:
        request: ChatRequest with message and context
    
    Returns:
        StreamingResponse with SSE events
    """
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    # Generate session ID if not provided
    session_id = request.session_id or str(uuid.uuid4())
    
    # Initialize session if new
    if session_id not in sessions:
        sessions[session_id] = []
    
    async def event_generator():
        try:
            # Create session context
            context = SessionContext(
                user_id=request.user_id or "anonymous",
                user_role=UserRole(request.user_role or "service_rep"),
                active_member_id=request.active_member_id,
                session_id=session_id
            )
            
            # Add user message to history
            sessions[session_id].append({
                "role": "user",
                "content": request.message,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Log interaction start
            if interaction_logger:
                interaction_logger.log_interaction_start(
                    session_id=session_id,
                    user_id=context.user_id,
                    query=request.message,
                    context=context.to_dict()
                )
            
            # Send session info
            yield f"data: {json.dumps({'type': 'session', 'session_id': session_id})}\n\n"
            
            # Get streaming response from agent
            from agent import stream_query
            full_response = ""
            
            # Stream events directly without wrapping in another async context
            try:
                async for event in stream_query(request.message, session_id, context):
                    event_type = event.get('type')
                    
                    if event_type == 'thinking':
                        # Agent is thinking/reasoning
                        yield f"data: {json.dumps({'type': 'thinking', 'content': event.get('content', '')})}\n\n"
                    
                    elif event_type == 'tool_use':
                        # Agent is using a tool
                        yield f"data: {json.dumps({'type': 'tool_use', 'tool': event.get('tool', ''), 'input': event.get('input', {})})}\n\n"
                    
                    elif event_type == 'tool_result':
                        # Tool execution result
                        yield f"data: {json.dumps({'type': 'tool_result', 'tool': event.get('tool', ''), 'result': event.get('result', '')})}\n\n"
                    
                    elif event_type == 'content':
                        # Response content chunk
                        content = event.get('content', '')
                        full_response += content
                        yield f"data: {json.dumps({'type': 'content', 'content': content})}\n\n"
                    
                    elif event_type == 'error':
                        # Error occurred
                        yield f"data: {json.dumps({'type': 'error', 'error': event.get('error', 'Unknown error')})}\n\n"
                        if interaction_logger:
                            interaction_logger.log_interaction_error(session_id=session_id, error=event.get('error', ''))
                        return
                    
                    # Small delay to prevent overwhelming the client
                    await asyncio.sleep(0.01)
            
            except Exception as stream_error:
                logger.error(f"Error during streaming: {str(stream_error)}", exc_info=True)
                yield f"data: {json.dumps({'type': 'error', 'error': str(stream_error)})}\n\n"
                if interaction_logger:
                    interaction_logger.log_interaction_error(session_id=session_id, error=str(stream_error))
                return
            
            # Add agent response to history
            sessions[session_id].append({
                "role": "assistant",
                "content": full_response,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Log interaction completion
            if interaction_logger:
                interaction_logger.log_interaction_complete(
                    session_id=session_id,
                    response=full_response,
                    metadata={}
                )
            
            # Send completion signal
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        
        except Exception as e:
            logger.error(f"Error in streaming chat: {str(e)}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
            if interaction_logger:
                interaction_logger.log_interaction_error(session_id=session_id, error=str(e))
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/")
async def root():
    """
    API information endpoint
    """
    return {
        "name": "HealthLake Agent API",
        "version": "2.0.0",
        "description": "AI agent API for AWS HealthLake FHIR data",
        "endpoints": {
            "health": "GET /health - Health check",
            "chat": "POST /chat - Send message to agent",
            "sessions": "GET /sessions - List active sessions",
            "session_detail": "GET /sessions/{session_id} - Get session history",
            "delete_session": "DELETE /sessions/{session_id} - Delete session",
            "clear_session": "POST /sessions/{session_id}/clear - Clear session history"
        },
        "docs": "/docs - Interactive API documentation"
    }


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    
    logger.info(f"🚀 Starting HealthLake Agent API on {host}:{port}")
    logger.info(f"📚 API docs: http://{host}:{port}/docs")
    
    uvicorn.run(
        "api:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
