"""Session management service for chat conversations"""
from typing import Dict, List, Optional
# from app.core.logging import get_logger
from app.models.schemas import ChatMessage, ChatHistory
import time

# logger = get_logger(__name__)


class SessionService:
    """Service for managing chat sessions and conversation history"""
    
    def __init__(self):
        self._sessions: Dict[str, List[Dict[str, str]]] = {}
        # logger.info("Session service initialized")
    
    def create_session(self, session_id: str) -> None:
        """Create a new chat session"""
        if session_id not in self._sessions:
            self._sessions[session_id] = []
            # logger.info(f"Created new session: {session_id}")
    
    def add_message(self, session_id: str, role: str, content: str) -> None:
        """
        Add a message to the session
        
        Args:
            session_id: Session identifier
            role: Message role (user/assistant)
            content: Message content
        """
        if session_id not in self._sessions:
            self.create_session(session_id)
        
        message = {
            "role": role,
            "content": content,
            "timestamp": time.time()
        }
        
        self._sessions[session_id].append(message)
        # logger.info(f"Added {role} message to session {session_id}")
    
    def get_chat_history(self, session_id: str) -> ChatHistory:
        """
        Get chat history for a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            ChatHistory object with messages
        """
        if session_id not in self._sessions:
            # logger.info(f"Session {session_id} not found, returning empty history")
            return ChatHistory(session_id=session_id, messages=[])
        
        messages = [
            ChatMessage(
                role=msg["role"],
                content=msg["content"],
                timestamp=msg.get("timestamp")
            )
            for msg in self._sessions[session_id]
        ]
        
        return ChatHistory(session_id=session_id, messages=messages)
    
    def get_messages_for_llm(self, session_id: str) -> List[ChatMessage]:
        """
        Get messages formatted for LLM processing
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of ChatMessage objects
        """
        history = self.get_chat_history(session_id)
        return history.messages
    
    def clear_session(self, session_id: str) -> bool:
        """
        Clear all messages from a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if session was cleared, False if session didn't exist
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            # logger.info(f"Cleared session: {session_id}")
            return True
        else:
            # logger.warning(f"Attempted to clear non-existent session: {session_id}")
            return False
    
    def get_session_count(self) -> int:
        """Get the number of active sessions"""
        return len(self._sessions)
    
    def session_exists(self, session_id: str) -> bool:
        """Check if a session exists"""
        return session_id in self._sessions


# Global session service instance
session_service = SessionService()
