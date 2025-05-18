import os
import json
from typing import List, Dict, Iterator
from groq import Groq
from flask import current_app

class AIService:
    """Service for handling AI interactions using Groq API."""
    
    @staticmethod
    def _get_client() -> Groq:
        """Get Groq client instance."""
        api_key = current_app.config.get('GROQ_API_KEY')
        if not api_key:
            raise ValueError("GROQ_API_KEY not configured")
        return Groq(api_key=api_key)
    
    @staticmethod
    def _prepare_messages(messages: List[Dict], custom_instruction: str = None) -> List[Dict]:
        """Prepare messages for the AI API call."""
        prepared_messages = []
        
        # Add system message with custom instruction if provided
        if custom_instruction:
            prepared_messages.append({
                "role": "system",
                "content": custom_instruction
            })
        else:
            # Default system message
            prepared_messages.append({
                "role": "system",
                "content": "You are ScubaAI, a helpful and knowledgeable assistant. Provide accurate, helpful, and engaging responses to user queries."
            })
        
        # Add conversation messages
        prepared_messages.extend(messages)
        
        return prepared_messages
    
    @staticmethod
    def get_response(messages: List[Dict], custom_instruction: str = None) -> str:
        """Get a single response from the AI."""
        try:
            client = AIService._get_client()
            model = current_app.config.get('GROQ_MODEL', 'llama3-8b-8192')
            
            prepared_messages = AIService._prepare_messages(messages, custom_instruction)
            
            response = client.chat.completions.create(
                model=model,
                messages=prepared_messages,
                temperature=0.7,
                max_tokens=4096,
                top_p=1,
                stream=False
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            current_app.logger.error(f"AI Service error: {str(e)}")
            raise Exception(f"Failed to get AI response: {str(e)}")
    
    @staticmethod
    def stream_response(messages: List[Dict], custom_instruction: str = None) -> Iterator[str]:
        """Get a streaming response from the AI."""
        try:
            client = AIService._get_client()
            model = current_app.config.get('GROQ_MODEL', 'llama3-8b-8192')
            
            prepared_messages = AIService._prepare_messages(messages, custom_instruction)
            
            response = client.chat.completions.create(
                model=model,
                messages=prepared_messages,
                temperature=0.7,
                max_tokens=4096,
                top_p=1,
                stream=True
            )
            
            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            current_app.logger.error(f"AI Service streaming error: {str(e)}")
            raise Exception(f"Failed to stream AI response: {str(e)}")
    
    @staticmethod
    def get_available_models() -> List[Dict]:
        """Get list of available models from Groq."""
        try:
            client = AIService._get_client()
            models = client.models.list()
            
            available_models = []
            for model in models.data:
                available_models.append({
                    'id': model.id,
                    'name': model.id,
                    'description': f"Model: {model.id}"
                })
            
            return available_models
            
        except Exception as e:
            current_app.logger.error(f"Error fetching models: {str(e)}")
            return []
    
    @staticmethod
    def validate_api_key(api_key: str) -> bool:
        """Validate a Groq API key."""
        try:
            client = Groq(api_key=api_key)
            # Try to list models as a way to validate the key
            client.models.list()
            return True
        except Exception as e:
            current_app.logger.error(f"API key validation failed: {str(e)}")
            return False
    
    @staticmethod
    def get_usage_stats() -> Dict:
        """Get usage statistics (if available from Groq API)."""
        try:
            # Note: This depends on Groq API providing usage endpoints
            # For now, return a placeholder
            return {
                'requests_made': 0,
                'tokens_used': 0,
                'last_request': None
            }
        except Exception as e:
            current_app.logger.error(f"Error fetching usage stats: {str(e)}")
            return {}
    
    @staticmethod
    def generate_conversation_title(messages: List[Dict]) -> str:
        """Generate a title for a conversation based on the first few messages."""
        try:
            if not messages:
                return "New Conversation"
            
            # Get the first user message
            first_user_message = None
            for msg in messages:
                if msg.get('role') == 'user':
                    first_user_message = msg.get('content', '')
                    break
            
            if not first_user_message:
                return "New Conversation"
            
            # If the message is short enough, use it as title
            if len(first_user_message) <= 50:
                return first_user_message
            
            # Otherwise, try to generate a title using AI
            client = AIService._get_client()
            
            title_messages = [
                {
                    "role": "system",
                    "content": "Generate a short, descriptive title (max 50 characters) for a conversation that starts with the following message. Return only the title, nothing else."
                },
                {
                    "role": "user",
                    "content": first_user_message[:200]  # Limit input to first 200 chars
                }
            ]
            
            response = client.chat.completions.create(
                model=current_app.config.get('GROQ_MODEL', 'llama3-8b-8192'),
                messages=title_messages,
                temperature=0.5,
                max_tokens=50,
                stream=False
            )
            
            title = response.choices[0].message.content.strip()
            
            # Ensure title is not too long
            if len(title) > 50:
                title = title[:47] + "..."
            
            return title
            
        except Exception as e:
            current_app.logger.error(f"Error generating conversation title: {str(e)}")
            # Fallback to truncated first message
            if first_user_message:
                return first_user_message[:47] + "..." if len(first_user_message) > 50 else first_user_message
            return "New Conversation"
