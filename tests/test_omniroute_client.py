"""
Tests para omniroute_client.py

Para ejecutar:
    pytest tests/test_omniroute_client.py -v
    
Para ejecutar con omniroute real (skip mocks):
    OMNIROUTE_REAL_TEST=1 pytest tests/test_omniroute_client.py -v
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from home.omniroute_client import (
    OmnirouteClient,
    OmnirouteResponse,
    OmnirouteUsage,
    OmnirouteError,
    OmnirouteStreamEvent,
    omniroute_client,
    chat_with_external_model,
    chat_with_local_model,
    memory_agent_search
)


# Fixtures

@pytest.fixture
def mock_response():
    """Response exitosa simulada de omniroute."""
    return {
        "id": "chatcmpl-test123",
        "object": "chat.completion",
        "created": 1699999999,
        "model": "nous-ai/solar-mini-4",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "Buenos Aires es la capital de Argentina."
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 15,
            "completion_tokens": 10,
            "total_tokens": 25
        }
    }


@pytest.fixture
def mock_health_response():
    """Health check response simulada."""
    return {
        "status": "ok",
        "version": "1.0.0",
        "providers": {
            "nous-portal": "connected",
            "ollama": "connected"
        }
    }


@pytest.fixture
def client():
    """Cliente omniroute de prueba."""
    return OmnirouteClient(
        endpoint="http://localhost:20128/v1",
        api_key="test-api-key-12345"
    )


# Tests de Construcción

def test_client_initialization():
    """Test: Cliente se inicializa correctamente."""
    client = OmnirouteClient(
        endpoint="http://test:20128/v1",
        api_key="test-key"
    )
    
    assert client.endpoint == "http://test:20128/v1"
    assert client.api_key == "test-key"
    assert client.timeout == 60


def test_client_requires_api_key():
    """Test: Cliente requiere API key."""
    with patch.dict(os.environ, {}, clear=True):
        client = OmnirouteClient(endpoint="http://test:20128")
        with pytest.raises(Exception, match="credentials_missing"):
            client.health_check()


def test_client_uses_env_vars():
    """Test: Cliente lee de variables de entorno."""
    with patch.dict(os.environ, {
        'OMNIROUTE_ENDPOINT': 'http://env-endpoint:8080/v1',
        'OMNIROUTE_API_KEY': 'env-key-123'
    }):
        client = OmnirouteClient()
        assert client.endpoint == "http://env-endpoint:8080/v1"
        assert client.api_key == "env-key-123"


# Tests de Parsing

def test_omniroute_usage_from_dict():
    """Test: OmnirouteUsage se construye desde dict."""
    data = {
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "total_tokens": 150
    }
    
    usage = OmnirouteUsage.from_dict(data)
    
    assert usage.prompt_tokens == 100
    assert usage.completion_tokens == 50
    assert usage.total_tokens == 150


def test_omniroute_response_from_dict(mock_response):
    """Test: OmnirouteResponse se construye desde dict."""
    response = OmnirouteResponse.from_dict(mock_response)
    
    assert response.id == "chatcmpl-test123"
    assert response.model == "nous-ai/solar-mini-4"
    assert "Buenos Aires" in response.content
    assert response.finish_reason == "stop"
    assert response.usage.total_tokens == 25


# Tests de Chat Completion

@patch('home.omniroute_client.requests.Session.post')
def test_chat_completion_success(mock_post, client, mock_response):
    """Test: chat_completion envía request correctamente."""
    mock_post.return_value.json.return_value = mock_response
    mock_post.return_value.raise_for_status = Mock()
    mock_post.return_value.status_code = 200
    
    messages = [
        {"role": "user", "content": "¿Cuál es la capital de Argentina?"}
    ]
    
    response = client.chat_completion(
        messages=messages,
        model="nous-ai/solar-mini-4",
        max_tokens=50
    )
    
    # Verificar que se llamó con parámetros correctos
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args[1]
    
    assert call_kwargs['json']['model'] == "nous-ai/solar-mini-4"
    assert call_kwargs['json']['messages'] == messages
    assert call_kwargs['json']['max_tokens'] == 50
    assert call_kwargs['timeout'] == 60
    
    # Verificar respuesta parseada
    assert "Buenos Aires" in response.content
    assert response.usage.total_tokens == 25


@patch('home.omniroute_client.requests.Session.post')
def test_chat_completion_with_reasoning_disabled(mock_post, client, mock_response):
    """Test: chat_completion puede deshabilitar reasoning."""
    mock_post.return_value.json.return_value = mock_response
    mock_post.return_value.raise_for_status = Mock()
    mock_post.return_value.status_code = 200
    
    messages = [{"role": "user", "content": "Test"}]
    
    client.chat_completion(
        messages=messages,
        reasoning=False
    )
    
    call_kwargs = mock_post.call_args[1]
    assert call_kwargs['json']['reasoning'] is False


@patch('home.omniroute_client.requests.Session.post')
def test_chat_completion_with_tools(mock_post, client, mock_response):
    """Test: chat_completion puede incluir tools."""
    mock_post.return_value.json.return_value = mock_response
    mock_post.return_value.raise_for_status = Mock()
    mock_post.return_value.status_code = 200
    
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get weather",
                "parameters": {"type": "object", "properties": {}}
            }
        }
    ]
    
    client.chat_completion(
        messages=[{"role": "user", "content": "Weather?"}],
        tools=tools
    )
    
    call_kwargs = mock_post.call_args[1]
    assert call_kwargs['json']['tools'] == tools


@patch('home.omniroute_client.requests.Session.post')
def test_chat_completion_http_error(mock_post, client):
    """Test: chat_completion maneja errores HTTP."""
    import requests
    
    mock_response = Mock()
    mock_response.status_code = 401
    mock_response.ok = False
    mock_response.text = "Unauthorized"
    mock_response.raise_for_status.side_effect = requests.HTTPError(response=mock_response)
    
    mock_post.return_value = mock_response
    
    with pytest.raises(Exception, match="rejected_401"):
        client.chat_completion(
            messages=[{"role": "user", "content": "Test"}]
        )


def test_chat_completion_stream_raises_error(client):
    """Test: chat_completion rechaza stream=True."""
    with pytest.raises(ValueError, match="streaming"):
        client.chat_completion(
            messages=[{"role": "user", "content": "Test"}],
            stream=True
        )


# Tests de Streaming

@patch('home.omniroute_client.requests.Session.post')
def test_chat_completion_stream(mock_post, client):
    """Test: chat_completion_stream retorna iterator."""
    # Simular SSE stream
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.status_code = 200
    mock_response.iter_lines.return_value = [
        b'data: {"choices":[{"delta":{"content":"Hola"}}]}',
        b'data: {"choices":[{"delta":{"content":" mundo"}}]}',
        b'data: [DONE]'
    ]
    
    mock_post.return_value = mock_response
    
    chunks = list(client.chat_completion_stream(
        messages=[{"role": "user", "content": "Test"}]
    ))
    
    assert [chunk.content for chunk in chunks if chunk.event == "delta"] == ["Hola", " mundo"]
    assert chunks[-1] == OmnirouteStreamEvent("done")


# Tests de Health Check

@patch('home.omniroute_client.requests.Session.get')
def test_health_check_success(mock_get, client, mock_health_response):
    """Test: health_check retorna status."""
    mock_get.return_value.json.return_value = mock_health_response
    mock_get.return_value.raise_for_status = Mock()
    mock_get.return_value.status_code = 200
    
    health = client.health_check()
    
    assert health['status'] == 'ok'
    assert 'providers' in health
    assert health['providers']['nous-portal'] == 'connected'


@patch('home.omniroute_client.requests.Session.get')
def test_health_check_failure(mock_get, client):
    """Test: health_check propaga excepciones."""
    import requests
    mock_get.side_effect = requests.ConnectionError("Connection refused")
    
    with pytest.raises(Exception, match="health_failure"):
        client.health_check()


# Tests de Usage Stats

@patch('home.omniroute_client.requests.Session.get')
def test_get_usage_stats_success(mock_get, client):
    """Test: get_usage_stats retorna datos."""
    mock_stats = {
        "total_requests": 1234,
        "total_tokens": 567890,
        "by_provider": {
            "nous-portal": {"requests": 1000, "tokens": 500000}
        }
    }
    
    mock_get.return_value.json.return_value = mock_stats
    mock_get.return_value.raise_for_status = Mock()
    mock_get.return_value.status_code = 200
    
    stats = client.get_usage_stats()
    
    assert stats['total_requests'] == 1234
    assert stats['total_tokens'] == 567890


@patch('home.omniroute_client.requests.Session.get')
def test_get_usage_stats_not_available(mock_get, client):
    """Test: get_usage_stats maneja endpoint no disponible."""
    mock_get.return_value.status_code = 404
    
    stats = client.get_usage_stats()
    
    assert stats == {}


# Tests de Helpers

@patch('home.omniroute_client.omniroute_client.chat_completion')
def test_chat_with_external_model(mock_completion):
    """Test: chat_with_external_model usa modelo correcto."""
    mock_completion.return_value = Mock()
    
    messages = [{"role": "user", "content": "Test"}]
    chat_with_external_model(messages, temperature=0.5)
    
    mock_completion.assert_called_once()
    call_kwargs = mock_completion.call_args[1]
    
    assert call_kwargs['model'] == "nous-ai/solar-mini-4"
    assert call_kwargs['temperature'] == 0.5


@patch('home.omniroute_client.omniroute_client.chat_completion')
def test_chat_with_local_model(mock_completion):
    """Test: chat_with_local_model usa Ollama."""
    mock_completion.return_value = Mock()
    
    messages = [{"role": "user", "content": "Test"}]
    chat_with_local_model(messages)
    
    mock_completion.assert_called_once()
    call_kwargs = mock_completion.call_args[1]
    
    assert call_kwargs['model'] == "ollama/qwen3.5:4b"


@patch('home.omniroute_client.omniroute_client.chat_completion')
def test_memory_agent_search(mock_completion):
    """Test: memory_agent_search configura correctamente."""
    mock_completion.return_value = Mock()
    
    memory_agent_search(
        query="Buscar recuerdos sobre Python",
        conversation_context=[{"role": "system", "content": "Context"}]
    )
    
    mock_completion.assert_called_once()
    call_kwargs = mock_completion.call_args[1]
    
    # Verificar parámetros críticos
    assert call_kwargs['model'] == "nous-ai/solar-mini-4"
    assert call_kwargs['reasoning'] is False  # Crítico para memory agent
    assert call_kwargs['temperature'] == 0.3
    assert call_kwargs['max_tokens'] == 500
    
    # Verificar mensajes
    messages = call_kwargs['messages']
    assert len(messages) == 2  # Context + query
    assert messages[-1]['content'] == "Buscar recuerdos sobre Python"


def test_memory_agent_does_not_mutate_caller_context(client):
    original = [{"role": "system", "content": "Context"}]
    with patch.object(omniroute_client, "chat_completion", return_value=Mock()) as completion:
        memory_agent_search("query", original)
    assert original == [{"role": "system", "content": "Context"}]


def test_missing_usage_is_rejected(mock_response):
    del mock_response["usage"]
    with pytest.raises(OmnirouteError, match="usage_invalid"):
        OmnirouteResponse.from_dict(mock_response)


def test_usage_total_must_match_components():
    with pytest.raises(OmnirouteError, match="usage_invalid"):
        OmnirouteUsage.from_dict({"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 99})


def test_sse_malformed_json_is_rejected(client):
    response = Mock(); response.status_code = 200; response.iter_lines.return_value = [b"data: {broken"]
    with patch("home.omniroute_client.requests.Session.post", return_value=response):
        with pytest.raises(OmnirouteError, match="sse_malformed"):
            list(client.chat_completion_stream([{"role": "user", "content": "Test"}]))


def test_client_resolves_environment_configuration_at_request_time():
    with patch.dict(os.environ, {}, clear=True):
        client = OmnirouteClient()
        assert client.api_key is None
        with pytest.raises(Exception, match="credentials_missing"):
            client.health_check()
    with patch.dict(os.environ, {"OMNIROUTE_API_KEY": "synthetic-key", "OMNIROUTE_ENDPOINT": "http://gateway/v1"}, clear=True):
        assert client.api_key == "synthetic-key"
        assert client.endpoint == "http://gateway/v1"


@patch("home.omniroute_client.requests.Session.get")
def test_health_check_uses_configured_timeout(mock_get, client):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"status": "ok"}
    client.timeout = 7
    client.health_check()
    assert mock_get.call_args.kwargs["timeout"] == 7


@patch("home.omniroute_client.requests.Session.post")
def test_http_rejection_closes_response_without_leaking_body(mock_post, client):
    response = Mock(status_code=401, text="secret response body")
    mock_post.return_value = response
    with pytest.raises(Exception, match="rejected_401") as error:
        client.chat_completion([{"role": "user", "content": "Test"}])
    response.close.assert_called_once_with()
    assert "secret response body" not in str(error.value)


# Tests de Integración (requieren omniroute real)

@pytest.mark.skipif(
    not os.getenv('OMNIROUTE_REAL_TEST'),
    reason="Requiere OMNIROUTE_REAL_TEST=1 y omniroute corriendo"
)
def test_real_omniroute_health():
    """Test de integración: health check real."""
    client = OmnirouteClient()
    health = client.health_check()
    
    assert health['status'] in ['ok', 'healthy', 'up']
    assert 'providers' in health or 'status' in health


@pytest.mark.skipif(
    not os.getenv('OMNIROUTE_REAL_TEST'),
    reason="Requiere OMNIROUTE_REAL_TEST=1 y omniroute corriendo"
)
def test_real_omniroute_chat():
    """Test de integración: chat completion real."""
    client = OmnirouteClient()
    
    response = client.chat_completion(
        messages=[
            {"role": "user", "content": "Di 'ok' y nada más"}
        ],
        model="nous-ai/solar-mini-4",
        max_tokens=5,
        temperature=0.1
    )
    
    assert response.content
    assert response.usage.total_tokens > 0
    assert response.model


@pytest.mark.skipif(
    not os.getenv('OMNIROUTE_REAL_TEST'),
    reason="Requiere OMNIROUTE_REAL_TEST=1 y omniroute corriendo"
)
def test_real_omniroute_local_model():
    """Test de integración: modelo local real."""
    client = OmnirouteClient()
    
    response = client.chat_completion(
        messages=[{"role": "user", "content": "Hi"}],
        model="ollama/qwen3.5:4b",
        max_tokens=10
    )
    
    assert response.content
    assert 'ollama' in response.model.lower() or 'qwen' in response.model.lower()


if __name__ == "__main__":
    # Ejecutar tests con pytest
    pytest.main([__file__, "-v"])
