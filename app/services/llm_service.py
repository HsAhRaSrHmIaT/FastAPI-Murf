"""Large Language Model service using Google Gemini"""
import google.generativeai as genai
from typing import List, Optional
from app.core.config import settings
from app.core.logging import get_logger
from app.models.schemas import LLMRequest, LLMResponse, ChatMessage

logger = get_logger(__name__)


class LLMService:
    """Large Language Model service using Google Gemini"""
    
    def __init__(self):
        self.api_key = settings.google_api_key
        
        if not self.api_key:
            logger.warning("Google API key not found")
            self._model = None
        else:
            genai.configure(api_key=self.api_key)
            self._model = genai.GenerativeModel(settings.default_llm_model)
            logger.info(f"LLM service initialized with {settings.default_llm_model}")
    
    def is_available(self) -> bool:
        """Check if LLM service is available"""
        return self._model is not None
    
    async def generate_response(self, prompt: str, temperature: float = 0.7) -> str:
        """
        Generate response from prompt
        
        Args:
            prompt: Input prompt for the model
            temperature: Generation temperature (0.0 to 2.0)
            
        Returns:
            Generated response text
            
        Raises:
            Exception: If generation fails or service unavailable
        """
        if not self.is_available():
            raise Exception("Google Gemini API key not configured")
        
        try:
            logger.info(f"Generating LLM response for prompt: '{prompt[:100]}...'")
            
            # Add system prompt for better responses
            system_prompt = (
                "You are a helpful assistant. You need to respond formally and straightforwardly. "
                "Provide informative and concise answers to user questions. "
                "If a question is not clear or appropriate, politely ask for clarification.\n\n"
                f"User: {prompt}"
            )
            
            response = self._model.generate_content(system_prompt)
            
            if not response or not response.text:
                logger.error("Empty response generated from LLM")
                raise Exception("Empty response generated from LLM")
            
            response_text = response.text.strip()
            logger.info(f"LLM response generated: '{response_text[:100]}...'")
            
            return response_text
            
        except Exception as e:
            logger.error(f"LLM service error: {str(e)}")
            raise Exception(f"Language model failed: {str(e)}")
    
    async def generate_chat_response(self, chat_history: List[ChatMessage]) -> str:
        """
        Generate response based on chat history
        
        Args:
            chat_history: List of previous chat messages
            
        Returns:
            Generated response text
            
        Raises:
            Exception: If generation fails or service unavailable
        """
        if not self.is_available():
            raise Exception("Google Gemini API key not configured")
        
        try:
            # Build conversation context
            messages = []
            for message in chat_history:
                messages.append(f"{message.role.title()}: {message.content}")
            
            conversation_text = "\n".join(messages)
            
            system_prompt = (
                "You are a helpful assistant. You need to respond formally and straightforwardly. "
                "Provide informative and concise answers based on the conversation context. "
                "If a question is not clear or appropriate, politely ask for clarification.\n\n"
                "Conversation history:\n"
                f"{conversation_text}"
            )
            
            logger.info(f"Generating chat response for {len(chat_history)} messages")
            
            response = self._model.generate_content(system_prompt)
            
            if not response or not response.text:
                logger.error("Empty response generated from LLM")
                raise Exception("Empty response generated from LLM")
            
            response_text = response.text.strip()
            logger.info(f"Chat response generated: '{response_text[:100]}...'")
            
            return response_text
            
        except Exception as e:
            logger.error(f"LLM chat service error: {str(e)}")
            raise Exception(f"Chat response generation failed: {str(e)}")


# Global LLM service instance
llm_service = LLMService()
