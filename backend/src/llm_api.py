import os
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

class LLMApi:
    def __init__(self, provider: str, api_key: Optional[str] = None, base_url: Optional[str] = None, project: Optional[str] = None, location: Optional[str] = None):
        self.provider = provider.lower()
        self.api_key = api_key or os.getenv(f'{self.provider.upper()}_API_KEY')
        self.base_url = base_url
        self.project = project or os.getenv('GOOGLE_CLOUD_PROJECT')
        self.location = location or os.getenv('GOOGLE_CLOUD_LOCATION')
        if self.provider == 'openai' or self.provider == 'together':
            try:
                from openai import OpenAI
                self.OpenAI = OpenAI
            except ImportError:
                raise ImportError("Please install openai: pip install openai")
        elif self.provider == 'anthropic':
            try:
                from anthropic import Anthropic
                self.Anthropic = Anthropic
            except ImportError:
                raise ImportError("Please install anthropic: pip install anthropic")
        elif self.provider == 'gemini':
            try:
                import google.generativeai as genai
                self.genai = genai
            except ImportError:
                raise ImportError("Please install google-generativeai: pip install google-generativeai")
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def chat(self, messages: List[dict], model: Optional[str] = None, **kwargs):
        """
        messages: List of dicts, e.g. [{"role": "user", "content": "Hello!"}]
        model: Model name (optional, depends on provider)
        kwargs: Additional provider-specific arguments
        """
        if self.provider == 'openai':
            # OpenAI official SDK >=1.84.0
            client = self.OpenAI(api_key=self.api_key, base_url=self.base_url) if self.base_url else self.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model=model or 'gpt-4o-mini',
                messages=messages,
                **kwargs
            )
            return response.choices[0].message.content
        elif self.provider == 'together':
            # Together AI via OpenAI SDK
            client = self.OpenAI(api_key=self.api_key, base_url=self.base_url or 'https://api.together.xyz/v1')
            response = client.chat.completions.create(
                model=model or 'togethercomputer/llama-2-70b-chat',
                messages=messages,
                **kwargs
            )
            return response.choices[0].message.content
        elif self.provider == 'anthropic':
            # Anthropic SDK >=0.52.2
            client = self.Anthropic(api_key=self.api_key)
            # Anthropic expects messages as a list of {role, content}
            response = client.messages.create(
                model=model or 'claude-3-5-sonnet-latest',
                max_tokens=kwargs.get('max_tokens', 32000),
                messages=messages,
                **{k: v for k, v in kwargs.items() if k != 'max_tokens'}
            )
            # Anthropic returns a list of content blocks; join them if needed
            if hasattr(response, 'content'):
                if isinstance(response.content, list):
                    return ''.join([c.text for c in response.content if hasattr(c, 'text')])
                return response.content
            return response
        elif self.provider == 'gemini':
            try:
                # Configure Gemini
                if self.api_key:
                    self.genai.configure(api_key=self.api_key)
                elif self.project and self.location:
                    self.genai.configure(project=self.project, location=self.location)
                
                # Initialize the model
                model_name = model or 'gemini-2.5-pro-preview-06-05'
                logger.info(f"Using Gemini model: {model_name}")
                
                # Create a chat session
                chat = self.genai.GenerativeModel(model_name=model_name)
                
                # Convert messages to Gemini format
                chat_history = []
                for msg in messages:
                    if msg['role'] == 'user':
                        chat_history.append({"role": "user", "parts": [msg['content']]})
                    elif msg['role'] == 'assistant':
                        chat_history.append({"role": "model", "parts": [msg['content']]})
                    elif msg['role'] == 'system':
                        # Add system message as context to the last user message
                        if chat_history and chat_history[-1]['role'] == 'user':
                            chat_history[-1]['parts'][0] = f"{msg['content']}\n\n{chat_history[-1]['parts'][0]}"
                
                # Generate response
                logger.info("Generating response from Gemini...")
                response = chat.generate_content(
                    chat_history,
                    generation_config=kwargs.get('generation_config', {
                        'temperature': 0.7,
                        'top_p': 0.95,
                        'top_k': 40,
                        'max_output_tokens': 32000,
                    })
                )
                
                # Extract and return the response text
                if hasattr(response, 'text'):
                    logger.info("Successfully generated response")
                    return response.text
                else:
                    error_msg = f"Unexpected response format from Gemini: {response}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                    
            except Exception as e:
                error_msg = f"Error in Gemini chat: {str(e)}"
                logger.error(error_msg)
                raise
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def _anthropic_format(self, messages: List[dict]) -> str:
        """Convert OpenAI-style messages to Anthropic prompt format."""
        prompt = ""
        for msg in messages:
            if msg['role'] == 'user':
                prompt += f"\n\nHuman: {msg['content']}"
            elif msg['role'] == 'assistant':
                prompt += f"\n\nAssistant: {msg['content']}"
        prompt += "\n\nAssistant:"
        return prompt

# Example usage:
# OpenAI (GPT-4.1):
# llm = LLMApi(provider='openai', api_key='sk-...')
# response = llm.chat([
#     {"role": "user", "content": "Hello!"}
# ])
# print(response)
#
# Together AI:
# llm = LLMApi(provider='together', api_key='together-...', base_url='https://api.together.xyz/v1')
# response = llm.chat([
#     {"role": "user", "content": "Hello!"}
# ])
# print(response)
#
# Anthropic (Claude 3.5):
# llm = LLMApi(provider='anthropic', api_key='...')
# response = llm.chat([
#     {"role": "user", "content": "Hello!"}
# ])
# print(response)
#
# Gemini (Google GenAI):
# llm = LLMApi(provider='gemini', api_key='...')
# response = llm.chat([
#     {"role": "user", "content": "Hello!"}
# ])
# print(response) 