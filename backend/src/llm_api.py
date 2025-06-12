import os
from typing import Optional, List

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
                from google import genai
                self.genai = genai
            except ImportError:
                raise ImportError("Please install google-genai: pip install google-genai")
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
                max_tokens=kwargs.get('max_tokens', 1024),
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
            # Google GenAI SDK >=1.19.0
            # Use environment variable GOOGLE_API_KEY or pass api_key
            if self.api_key:
                client = self.genai.Client(api_key=self.api_key)
            elif self.project and self.location:
                client = self.genai.Client(vertexai=True, project=self.project, location=self.location)
            else:
                client = self.genai.Client()
            # Gemini expects a single string or list of messages
            prompt = messages[-1]['content'] if messages else ''
            model_name = model or 'gemini-2.0-flash-001'
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                **kwargs
            )
            return getattr(response, 'text', str(response))
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