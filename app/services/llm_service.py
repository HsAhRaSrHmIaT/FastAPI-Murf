"""Language Model service using Google Gemini AI with streaming support"""
import google.generativeai as genai
from typing import AsyncGenerator, List, Dict, Any
from app.core.config import settings
from app.core.logging import get_logger
import asyncio
import time

logger = get_logger(__name__)

class LLMService:
    """Language Model service using Google Gemini AI"""
    
    def __init__(self):
        self.model = None
        self.conversation_history: Dict[str, List[Dict[str, str]]] = {}
        
        if not settings.google_api_key:
            logger.warning("Google API key not found")
            return
            
        try:
            genai.configure(api_key=settings.google_api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
            logger.info("LLM service initialized with Google Gemini 2.5 Flash")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {e}")
            self.model = None
    
    def is_available(self) -> bool:
        """Check if LLM service is available"""
        return self.model is not None
    
    def get_conversation_history(self, session_id: str) -> List[Dict[str, str]]:
        """Get conversation history for a session"""
        return self.conversation_history.get(session_id, [])
    
    def add_to_conversation(self, session_id: str, role: str, content: str):
        """Add message to conversation history"""
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []
        
        self.conversation_history[session_id].append({
            "role": role,
            "content": content,
            "timestamp": time.time()
        })
        
        # Keep only last 20 messages to prevent context overflow
        if len(self.conversation_history[session_id]) > 20:
            self.conversation_history[session_id] = self.conversation_history[session_id][-20:]
    
    def clear_conversation(self, session_id: str):
        """Clear conversation history for a session"""
        if session_id in self.conversation_history:
            del self.conversation_history[session_id]
            logger.info(f"Cleared conversation history for session: {session_id}")
    
    def _format_conversation_context(self, session_id: str) -> str:
        """Format conversation history as context"""
        history = self.get_conversation_history(session_id)
        if not history:
            return ""
        
        context_parts = []
        for msg in history[-10:]:  # Use last 10 messages for context
            role_label = "User" if msg["role"] == "user" else "Assistant"
            context_parts.append(f"{role_label}: {msg['content']}")
        
        return "\n".join(context_parts)
    
    async def generate_streaming_response(self, 
                                        text: str, 
                                        session_id: str = "default") -> AsyncGenerator[str, None]:
        """Generate streaming response from LLM"""
        if not self.is_available():
            yield "I'm sorry, but the AI service is currently unavailable. Please try again later."
            return
        
        try:
            # Add user message to conversation history
            self.add_to_conversation(session_id, "user", text)
            
            # Build prompt with conversation context
            context = self._format_conversation_context(session_id)
            
            # Create system prompt
            system_prompt = """You are a helpful AI assistant having a natural conversation through voice. 
Keep your responses conversational, concise, and engaging. Respond as if you're speaking to the person directly.
Avoid overly formal language and keep responses under 300 words unless specifically asked for more detail."""
            
            # Build the full prompt
            if context:
                full_prompt = f"{system_prompt}\n\nConversation history:\n{context}\n\nUser: {text}\n\nAssistant:"
            else:
                full_prompt = f"{system_prompt}\n\nUser: {text}\n\nAssistant:"
            
            logger.info(f"Generating streaming response for session {session_id}: '{text[:50]}...'")
            
            # Generate streaming response
            response = self.model.generate_content(
                full_prompt,
                stream=True,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=2000,
                    top_p=0.9
                )
            )
            
            accumulated_response = ""
            chunk_count = 0
            
            for chunk in response:
                if chunk.text:
                    chunk_count += 1
                    accumulated_response += chunk.text
                    logger.debug(f"Streaming chunk {chunk_count}: '{chunk.text[:30]}...'")
                    yield chunk.text
                    
                    # Small delay to make streaming visible
                    await asyncio.sleep(0.05)
            
            # Add assistant response to conversation history
            if accumulated_response:
                self.add_to_conversation(session_id, "assistant", accumulated_response)
                logger.info(f"Completed streaming response for session {session_id}. "
                          f"Total chunks: {chunk_count}, Length: {len(accumulated_response)}")
            else:
                logger.warning(f"Empty response generated for session {session_id}")
                yield "I'm sorry, I couldn't generate a response. Please try again."
                
        except Exception as e:
            logger.error(f"LLM service error for session {session_id}: {str(e)}")
            yield f"I encountered an error while processing your request: {str(e)}"
    
    async def generate_response(self, text: str, session_id: str = "default") -> str:
        """Generate non-streaming response (legacy support)"""
        accumulated_response = ""
        async for chunk in self.generate_streaming_response(text, session_id):
            accumulated_response += chunk
        return accumulated_response

# Global LLM service instance
llm_service = LLMService()
