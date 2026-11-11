"""
omniroute Client - Python interface for communication with omniroute gateway.

This module provides a unified interface for all AI model calls,
delegating routing, fallback and credential management to omniroute.

Basic usage:
    from home.omniroute_client import omniroute_client
    
    response = omniroute_client.chat_completion(
        messages=[{"role": "user", "content": "Hello"}],
        model="nous-ai/solar-mini-4"
    )
"""

import os
import logging
import requests
from typing import Dict, List, Optional, Iterator, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class OmnirouteUsage:
    """Token usage information from a response."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'OmnirouteUsage':
        """Build from response dictionary."""
        return cls(
            prompt_tokens=data.get('prompt_tokens', 0),
            completion_tokens=data.get('completion_tokens', 0),
            total_tokens=data.get('total_tokens', 0)
        )


@dataclass
class OmnirouteResponse:
    """Complete response from omniroute."""
    id: str
    model: str
    content: str
    finish_reason: str
    usage: OmnirouteUsage
    created: datetime
    raw: Dict  # Complete response for debugging
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'OmnirouteResponse':
        """Build from response dictionary."""
        choice = data['choices'][0]
        message = choice['message']
        
        return cls(
            id=data.get('id', 'unknown'),
            model=data.get('model', 'unknown'),
            content=message.get('content', ''),
            finish_reason=choice.get('finish_reason', 'unknown'),
            usage=OmnirouteUsage.from_dict(data.get('usage', {})),
            created=datetime.fromtimestamp(data.get('created', 0)),
            raw=data
        )


class OmnirouteClient:
    """
    Client for interacting with omniroute gateway.
    
    Handles:
    - Authentication with API key
    - OpenAI-compatible request formatting
    - Response parsing
    - SSE streaming
    - Error handling and retries
    - Audit logging
    """
    
    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 60
    ):
        """
        Initialize omniroute client.
        
        Args:
            endpoint: omniroute base URL (default: from env OMNIROUTE_ENDPOINT)
            api_key: API key (default: from env OMNIROUTE_API_KEY)
            timeout: Timeout in seconds for requests
        """
        self.endpoint = (
            endpoint or 
            os.getenv('OMNIROUTE_ENDPOINT', 'http://localhost:20128/v1')
        ).rstrip('/')
        
        self.api_key = api_key or os.getenv('OMNIROUTE_API_KEY')
        
        if not self.api_key:
            raise ValueError(
                "OMNIROUTE_API_KEY not configured. "
                "Set in .env or pass as argument."
            )
        
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        })
        
        logger.info(f"OmnirouteClient inicializado: {self.endpoint}")
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "nous-ai/solar-mini-4",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        reasoning: Optional[bool] = None,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> OmnirouteResponse:
        """
        Send chat completion request to omniroute.
        
        Args:
            messages: List of messages [{"role": "user", "content": "..."}]
            model: Model ID (e.g., "nous-ai/solar-mini-4", "ollama/qwen3.5:4b")
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate
            stream: If True, returns iterator (use chat_completion_stream)
            reasoning: If False, disables reasoning (for memory agent)
            tools: List of available tools for function calling
            **kwargs: Additional parameters for the model
        
        Returns:
            OmnirouteResponse with content and metadata
        
        Raises:
            requests.HTTPError: If omniroute returns HTTP error
            ValueError: If response has invalid format
        """
        if stream:
            raise ValueError(
                "For streaming, use chat_completion_stream() instead"
            )
        
        payload = {
            'model': model,
            'messages': messages,
            'temperature': temperature,
            **kwargs
        }
        
        if max_tokens is not None:
            payload['max_tokens'] = max_tokens
        
        if reasoning is not None:
            payload['reasoning'] = reasoning
        
        if tools is not None:
            payload['tools'] = tools
        
        logger.debug(
            f"Enviando chat completion: model={model}, "
            f"msgs={len(messages)}, max_tokens={max_tokens}"
        )
        
        try:
            response = self.session.post(
                f"{self.endpoint}/chat/completions",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            result = OmnirouteResponse.from_dict(data)
            
            logger.info(
                f"Chat completion exitoso: model={result.model}, "
                f"tokens={result.usage.total_tokens}, "
                f"finish={result.finish_reason}"
            )
            
            return result
        
        except requests.HTTPError as e:
            logger.error(f"omniroute HTTP error: {e.response.status_code}")
            logger.error(f"Response: {e.response.text}")
            raise
        
        except Exception as e:
            logger.error(f"Error en chat completion: {e}")
            raise
    
    def chat_completion_stream(
        self,
        messages: List[Dict[str, str]],
        model: str = "nous-ai/solar-mini-4",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Iterator[str]:
        """
        Send chat completion with SSE streaming.
        
        Returns iterator that yields each text chunk as it arrives.
        
        Args:
            messages: List of messages
            model: Model ID
            temperature: Temperature
            max_tokens: Maximum tokens
            **kwargs: Additional parameters
        
        Yields:
            str: Each generated text chunk
        
        Example:
            for chunk in client.chat_completion_stream(messages):
                print(chunk, end='', flush=True)
        """
        payload = {
            'model': model,
            'messages': messages,
            'temperature': temperature,
            'stream': True,
            **kwargs
        }
        
        if max_tokens is not None:
            payload['max_tokens'] = max_tokens
        
        logger.debug(f"Iniciando streaming: model={model}, msgs={len(messages)}")
        
        try:
            response = self.session.post(
                f"{self.endpoint}/chat/completions",
                json=payload,
                stream=True,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if not line:
                    continue
                
                line = line.decode('utf-8')
                
                # SSE format: "data: {...}"
                if line.startswith('data: '):
                    data_str = line[6:]  # Remove "data: " prefix
                    
                    if data_str == '[DONE]':
                        logger.debug("Streaming completed")
                        break
                    
                    try:
                        data = json.loads(data_str)
                        choices = data.get('choices', [])
                        
                        if choices:
                            delta = choices[0].get('delta', {})
                            content = delta.get('content', '')
                            
                            if content:
                                yield content
                    
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in stream: {data_str}")
                        continue
        
        except requests.HTTPError as e:
            logger.error(f"omniroute streaming error: {e.response.status_code}")
            raise
        
        except Exception as e:
            logger.error(f"Error en streaming: {e}")
            raise
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check omniroute status.
        
        Returns:
            Dict with status and provider metadata
        
        Example:
            health = client.health_check()
            print(f"Status: {health['status']}")
            print(f"Providers: {health['providers']}")
        """
        try:
            # Remove /v1 suffix for health endpoint
            base_endpoint = self.endpoint.replace('/v1', '')
            
            response = self.session.get(
                f"{base_endpoint}/health",
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Health check OK: {data.get('status')}")
            
            return data
        
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get omniroute usage statistics.
        
        Returns:
            Dict with total requests, tokens, distribution by provider, etc.
        
        Note:
            Endpoint may not be available in all omniroute installations.
        """
        try:
            # Remove /v1 suffix
            base_endpoint = self.endpoint.replace('/v1', '')
            
            response = self.session.get(
                f"{base_endpoint}/usage",
                timeout=10
            )
            
            if response.status_code == 404:
                logger.warning("Endpoint /usage not available in omniroute")
                return {}
            
            response.raise_for_status()
            return response.json()
        
        except Exception as e:
            logger.error(f"Error getting usage stats: {e}")
            return {}


# Global singleton for use across application
omniroute_client = OmnirouteClient()


# Helpers for common use cases

def chat_with_external_model(
    messages: List[Dict[str, str]],
    **kwargs
) -> OmnirouteResponse:
    """
    Send chat to external model (Nous Portal primary).
    
    Uses fallback chain configured in omniroute.
    """
    return omniroute_client.chat_completion(
        messages=messages,
        model="nous-ai/solar-mini-4",
        **kwargs
    )


def chat_with_local_model(
    messages: List[Dict[str, str]],
    **kwargs
) -> OmnirouteResponse:
    """
    Send chat to local model (Ollama).
    
    For guests or when cloud unavailable.
    """
    return omniroute_client.chat_completion(
        messages=messages,
        model="ollama/qwen3.5:4b",
        **kwargs
    )


def memory_agent_search(
    query: str,
    conversation_context: Optional[List[Dict[str, str]]] = None
) -> OmnirouteResponse:
    """
    Invoke memory agent with reasoning disabled.
    
    Args:
        query: Current user query
        conversation_context: Optional conversation context
    
    Returns:
        Memory agent response with relevant memory IDs
    """
    messages = conversation_context or []
    messages.append({"role": "user", "content": query})
    
    return omniroute_client.chat_completion(
        messages=messages,
        model="nous-ai/solar-mini-4",
        reasoning=False,  # Critical: disable reasoning for memory agent
        temperature=0.3,  # More deterministic for search
        max_tokens=500
    )


# Import json for streaming
import json
