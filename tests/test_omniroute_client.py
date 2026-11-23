"""
Tests para omniroute_client.py

Para ejecutar:
    pytest tests/test_omniroute_client.py -v
    
Para ejecutar con omniroute real (skip mocks):
    OMNIROUTE_REAL_TEST=1 pytest tests/test_omniroute_client.py -v
"""

import os
import json
import pytest
import requests
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
from home.provider_outcomes import NotDispatched, OutcomeUnknown


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


@pytest.mark.parametrize("api_key", ["", "key with spaces", "key\\value", "key'quote"])
def test_client_rejects_invalid_explicit_api_key(api_key):
    with pytest.raises(ValueError, match="api_key_invalid"):
        OmnirouteClient(endpoint="http://test:20128/v1", api_key=api_key)


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


@pytest.mark.parametrize("endpoint", [
    "not-a-url",
    "ftp://gateway/v1",
    "http://user:secret@gateway/v1",
    "http://gateway/v1#fragment",
    "http://gateway/v1?api_key=secret",
    "http://[::1",
    "http://gateway:invalid-port/v1",
])
def test_client_rejects_invalid_gateway_endpoint(endpoint):
    with patch.dict(os.environ, {"OMNIROUTE_ENDPOINT": endpoint}, clear=True):
        with pytest.raises(OmnirouteError, match="endpoint_invalid"):
            OmnirouteClient().endpoint


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
    mock_post.return_value.iter_content.return_value = [json.dumps(mock_response).encode()]
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
    mock_post.return_value.iter_content.return_value = [json.dumps(mock_response).encode()]
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
    mock_post.return_value.iter_content.return_value = [json.dumps(mock_response).encode()]
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
    
    with pytest.raises(OutcomeUnknown, match="failed_401"):
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


@pytest.mark.parametrize("kwargs, error", [
    ({"messages": []}, "messages_invalid"),
    ({"messages": [{"role": "user"}, "invalid"]}, "messages_invalid"),
    ({"messages": [{"role": "user"}], "model": ""}, "model_invalid"),
    ({"messages": [{"role": "user"}], "temperature": "warm"}, "temperature_invalid"),
    ({"messages": [{"role": "user"}], "max_tokens": 0}, "max_tokens_invalid"),
])
def test_chat_completion_rejects_invalid_request_before_dispatch(client, kwargs, error):
    with patch("home.omniroute_client.requests.Session.post") as mock_post:
        with pytest.raises(ValueError, match=error):
            client.chat_completion(**kwargs)
    mock_post.assert_not_called()


def test_chat_completion_stream_rejects_invalid_request_before_dispatch(client):
    with patch("home.omniroute_client.requests.Session.post") as mock_post:
        with pytest.raises(ValueError, match="max_tokens_invalid"):
            list(client.chat_completion_stream(
                [{"role": "user"}], max_tokens=-1
            ))
    mock_post.assert_not_called()


# Tests de Streaming

@patch('home.omniroute_client.requests.Session.post')
def test_chat_completion_stream(mock_post, client):
    """Test: chat_completion_stream retorna iterator."""
    # Simular SSE stream
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.status_code = 200
    mock_response.iter_content.return_value = map(lambda line: line + b'\n', [
        b'data: {"id":"resp-1","model":"example/model","choices":[{"delta":{"content":"Hola"}}]}',
        b'data: {"id":"resp-1","model":"example/model","choices":[{"delta":{"content":" mundo"}}]}',
        b'data: {"id":"resp-1","model":"example/model","choices":[{"delta":{},"finish_reason":"stop"}]}\n'
        b'data: {"id":"resp-1","model":"example/model","choices":[],"usage":{"prompt_tokens":2,"completion_tokens":1,"total_tokens":3}}',
        b'data: [DONE]'
    ])
    
    mock_post.return_value = mock_response
    
    chunks = list(client.chat_completion_stream(
        messages=[{"role": "user", "content": "Test"}]
    ))
    
    assert [chunk.content for chunk in chunks if chunk.event == "delta" and chunk.content] == ["Hola", " mundo"]
    assert chunks[-1] == OmnirouteStreamEvent("done")
    assert mock_post.call_args.kwargs["json"]["stream_options"] == {"include_usage": True}


@patch('home.omniroute_client.requests.Session.post')
def test_chat_completion_stream_accepts_final_usage_only_chunk(mock_post, client):
    response = Mock(status_code=200)
    response.iter_content.return_value = map(lambda line: line + b'\n', [
        b'data: {"id":"resp-1","model":"example/model","choices":[{"delta":{"content":"ok"}}]}',
        b'data: {"id":"resp-1","model":"example/model","choices":[{"delta":{},"finish_reason":"stop"}]}\n'
        b'data: {"id":"resp-1","model":"example/model","choices":[],"usage":{"prompt_tokens":2,"completion_tokens":1,"total_tokens":3}}',
        b'data: [DONE]',
    ])
    mock_post.return_value = response
    chunks = list(client.chat_completion_stream([{"role": "user", "content": "Test"}]))
    assert chunks[-2].usage == OmnirouteUsage(2, 1, 3)


@pytest.mark.parametrize("final_identity", [
    {"id": "different", "model": "example/model"},
    {"id": "resp-1", "model": "other/model"},
    {"model": "example/model"},
    {"id": "resp-1"},
    {"id": "", "model": "example/model"},
])
def test_stream_rejects_uncorrelated_usage(client, final_identity):
    import json

    first = {"id": "resp-1", "model": "example/model", "choices": [{"delta": {"content": "ok"}}]}
    final = {**final_identity, "choices": [], "usage": {"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3}}
    response = Mock(status_code=200)
    response.iter_content.return_value = map(lambda line: line + b'\n', [
        ("data: " + json.dumps(first)).encode(),
        ("data: " + json.dumps(final)).encode(),
        b"data: [DONE]",
    ])
    with patch("home.omniroute_client.requests.Session.post", return_value=response):
        with pytest.raises(OutcomeUnknown, match="stream_invalid"):
            list(client.chat_completion_stream([{"role": "user", "content": "Test"}]))
    response.close.assert_called_once_with()


@pytest.mark.parametrize('finish_reason', [None, 'length', 'tool_calls', 'content_filter'])
def test_stream_requires_normal_finish_even_with_usage_and_done(client, finish_reason):
    chunk = {"id": "resp-1", "model": "example/model", "choices": [
        {"delta": {"content": "partial"}, "finish_reason": finish_reason}
    ]}
    usage = {"id": "resp-1", "model": "example/model", "choices": [],
             "usage": {"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3}}
    response = Mock(status_code=200)
    response.iter_content.return_value = [
        ("data: " + json.dumps(chunk) + "\n" + "data: " + json.dumps(usage) + "\ndata: [DONE]\n").encode()
    ]
    with patch('home.omniroute_client.requests.Session.post', return_value=response):
        with pytest.raises(OutcomeUnknown, match='stream_invalid'):
            list(client.chat_completion_stream([{'role': 'user', 'content': 'Test'}]))
    response.close.assert_called_once_with()


@patch('home.omniroute_client.requests.Session.post')
def test_chat_completion_stream_rejects_oversized_total_stream(mock_post, client):
    response = Mock(status_code=200)
    response.iter_content.return_value = map(lambda line: line + b'\n', [b'data: {"id":"resp-1","model":"example/model","choices":[{"delta":{"content":"x"}}]}'] * 20)
    mock_post.return_value = response
    with patch('home.omniroute_client.MAX_RESPONSE_BYTES', 100):
        with pytest.raises(OutcomeUnknown, match="stream_invalid"):
            list(client.chat_completion_stream([{"role": "user", "content": "Test"}]))


# Tests de Health Check

@patch('home.omniroute_client.requests.Session.get')
def test_health_check_success(mock_get, client, mock_health_response):
    """Test: health_check retorna status."""
    mock_get.return_value.headers = {}
    mock_get.return_value.iter_content.return_value = [json.dumps(mock_health_response).encode()]
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
    
    mock_get.return_value.headers = {}
    mock_get.return_value.iter_content.return_value = [json.dumps(mock_stats).encode()]
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
    with pytest.raises(NotDispatched, match="admission_unavailable"):
        chat_with_external_model([{"role": "user", "content": "Test"}])
    mock_completion.assert_not_called()


@patch('home.omniroute_client.omniroute_client.chat_completion')
def test_chat_with_local_model(mock_completion):
    with pytest.raises(NotDispatched, match="locality_unverified"):
        chat_with_local_model([{"role": "user", "content": "Test"}])
    mock_completion.assert_not_called()


@patch('home.omniroute_client.omniroute_client.chat_completion')
def test_memory_agent_search(mock_completion):
    for user_key in (None, "user-1"):
        with pytest.raises(NotDispatched, match="memory_gateway_admission_unavailable"):
            memory_agent_search("query", [{"role": "system", "content": "Context"}], user_key=user_key)
    mock_completion.assert_not_called()


@patch('home.omniroute_client.omniroute_client.chat_completion')
def test_memory_agent_caller_metadata_cannot_open_unverified_nous_route(mock_completion):
    context = [{"role": "system", "content": "synthetic authorized-looking context"}]
    with pytest.raises(NotDispatched, match="memory_gateway_admission_unavailable"):
        memory_agent_search("synthetic query", context, user_key="user-1", operation_id="synthetic-operation")
    mock_completion.assert_not_called()
    with pytest.raises(TypeError, match="unexpected keyword argument"):
        memory_agent_search(
            "synthetic query",
            context,
            provider="nous",
            model="upstage/solar-mini4:free",
            endpoint="https://inference-api.nousresearch.com/v1",
            budget_reserved=True,
            disclosure_authorized=True,
        )
    mock_completion.assert_not_called()


def test_memory_agent_does_not_mutate_caller_context(client):
    original = [{"role": "system", "content": "Context"}]
    with patch.object(omniroute_client, "chat_completion", return_value=Mock()) as completion:
        with pytest.raises(NotDispatched):
            memory_agent_search("query", original)
    completion.assert_not_called()
    assert original == [{"role": "system", "content": "Context"}]


def test_missing_usage_is_rejected(mock_response):
    del mock_response["usage"]
    with pytest.raises(OmnirouteError, match="usage_invalid"):
        OmnirouteResponse.from_dict(mock_response)


def test_usage_total_must_match_components():
    with pytest.raises(OmnirouteError, match="usage_invalid"):
        OmnirouteUsage.from_dict({"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 99})


@pytest.mark.parametrize("payload", [{}, {"object": "chat.completion", "usage": None}])
def test_invalid_non_stream_response_has_unknown_outcome(client, payload):
    response = Mock(status_code=200, headers={})
    response.iter_content.return_value = [json.dumps(payload).encode()]
    with patch("home.omniroute_client.requests.Session.post", return_value=response):
        with pytest.raises(OutcomeUnknown, match="response_invalid"):
            client.chat_completion([{"role": "user", "content": "Test"}])
    response.close.assert_called_once_with()


@pytest.mark.parametrize("field,value", [("id", ""), ("model", "  "), ("created", 10**30)])
def test_non_stream_invalid_identity_or_timestamp_is_unknown(client, mock_response, field, value):
    mock_response[field] = value
    response = Mock(status_code=200, headers={})
    response.iter_content.return_value = [json.dumps(mock_response).encode()]
    with patch("home.omniroute_client.requests.Session.post", return_value=response):
        with pytest.raises(OutcomeUnknown, match="response_invalid"):
            client.chat_completion([{"role": "user", "content": "Test"}])
    response.close.assert_called_once_with()


@pytest.mark.parametrize("headers", [{}, {"Content-Length": "1"}])
def test_non_stream_response_enforces_actual_byte_limit(client, headers):
    response = Mock(status_code=200, headers=headers)
    response.iter_content.return_value = [b"12345", b"67890", b"excess"]
    with patch("home.omniroute_client.MAX_RESPONSE_BYTES", 10), \
            patch("home.omniroute_client.requests.Session.post", return_value=response) as post:
        with pytest.raises(OutcomeUnknown, match="response_invalid"):
            client.chat_completion([{"role": "user", "content": "Test"}])
    assert post.call_args.kwargs["stream"] is True
    response.close.assert_called_once_with()


def test_non_stream_read_failure_is_unknown_and_closes_response(client):
    response = Mock(status_code=200, headers={})
    response.iter_content.side_effect = requests.exceptions.ChunkedEncodingError("synthetic")
    with patch("home.omniroute_client.requests.Session.post", return_value=response):
        with pytest.raises(OutcomeUnknown, match="response_invalid"):
            client.chat_completion([{"role": "user", "content": "Test"}])
    response.close.assert_called_once_with()


@pytest.mark.parametrize("streaming", [False, True])
def test_deeply_nested_response_is_unknown_and_closed(client, streaming):
    response = Mock(status_code=200, headers={})
    nested = b"[" * 2000 + b"0" + b"]" * 2000
    response.iter_content.return_value = [b"data: " + nested + b"\n" if streaming else nested]
    with patch("home.omniroute_client.requests.Session.post", return_value=response):
        with pytest.raises(OutcomeUnknown):
            if streaming:
                list(client.chat_completion_stream([{"role": "user", "content": "Test"}]))
            else:
                client.chat_completion([{"role": "user", "content": "Test"}])
    response.close.assert_called_once_with()


def test_sse_excessively_long_integer_is_unknown_and_closed(client):
    import sys

    response = Mock(status_code=200)
    response.iter_content.return_value = [b'data: {"value":' + b'1' * 5000 + b'}\n']
    old_limit = sys.get_int_max_str_digits()
    try:
        sys.set_int_max_str_digits(4300)
        with patch("home.omniroute_client.requests.Session.post", return_value=response):
            with pytest.raises(OutcomeUnknown, match="stream_invalid"):
                list(client.chat_completion_stream([{"role": "user", "content": "Test"}]))
    finally:
        sys.set_int_max_str_digits(old_limit)
    response.close.assert_called_once_with()


def test_sse_os_error_during_read_is_unknown_and_closes_session(client):
    response = Mock(status_code=200)
    response.iter_content.side_effect = OSError("synthetic")
    with patch("home.omniroute_client.requests.Session.post", return_value=response):
        with patch.object(client, "close", wraps=client.close) as close:
            with pytest.raises(OutcomeUnknown, match="stream_failure"):
                list(client.chat_completion_stream([{"role": "user", "content": "Test"}]))
    response.close.assert_called_once_with()
    close.assert_called_once_with()


def test_stream_payload_cannot_be_disabled_by_kwargs(client):
    response = Mock(status_code=200)
    response.iter_content.return_value = [
        b'data: {"id":"r","model":"m","choices":[{"delta":{},"finish_reason":"stop"}]}\n'
        b'data: {"id":"r","model":"m","choices":[],'
        b'"usage":{"prompt_tokens":1,"completion_tokens":1,"total_tokens":2}}\n'
        b'data: [DONE]\n'
    ]
    with patch("home.omniroute_client.requests.Session.post", return_value=response) as post:
        list(client.chat_completion_stream([{"role": "user", "content": "Test"}], stream=False,
                                           stream_options={"include_usage": False}))
    assert post.call_args.kwargs["json"]["stream"] is True
    assert post.call_args.kwargs["json"]["stream_options"] == {"include_usage": True}


def test_sse_many_blank_lines_are_accepted_before_valid_result(client):
    response = Mock(status_code=200)
    response.iter_content.return_value = [
        b"\n" * 20000 + b'data: {"id":"r","model":"m","choices":[{"delta":{},"finish_reason":"stop"}]}\n'
        b'data: {"id":"r","model":"m","choices":[],'
        b'"usage":{"prompt_tokens":1,"completion_tokens":1,"total_tokens":2}}\n'
        b'data: [DONE]\n'
    ]
    with patch("home.omniroute_client.requests.Session.post", return_value=response):
        events = list(client.chat_completion_stream([{"role": "user", "content": "Test"}]))
    assert events[-1].event == "done"
    response.close.assert_called_once_with()


def test_sse_malformed_json_is_rejected(client):
    response = Mock(); response.status_code = 200; response.iter_content.return_value = map(lambda line: line + b'\n', [b"data: {broken"])
    with patch("home.omniroute_client.requests.Session.post", return_value=response):
        with pytest.raises(OutcomeUnknown, match="stream_invalid"):
            list(client.chat_completion_stream([{"role": "user", "content": "Test"}]))


@pytest.mark.parametrize("line_limit,total_limit", [(12, 100), (100, 12)])
def test_sse_enforces_bounds_before_newline(client, line_limit, total_limit):
    response = Mock(status_code=200)
    consumed = []
    def chunks():
        for chunk in (b"data:", b" 1234", b" 5678", b"should not be consumed"):
            consumed.append(chunk)
            yield chunk
    response.iter_content.return_value = chunks()
    with patch("home.omniroute_client.MAX_SSE_LINE_BYTES", line_limit), \
            patch("home.omniroute_client.MAX_RESPONSE_BYTES", total_limit), \
            patch("home.omniroute_client.requests.Session.post", return_value=response):
        with pytest.raises(OutcomeUnknown, match="stream_invalid"):
            list(client.chat_completion_stream([{"role": "user", "content": "Test"}]))
    assert len(consumed) == 3
    response.close.assert_called_once_with()


@pytest.mark.parametrize("delimiter", [b"\n", b"\r\n", b"\r"])
def test_sse_accepts_fragmented_lines_and_standard_delimiters(client, delimiter):
    response = Mock(status_code=200)
    payload = (b'data: {"id":"r","model":"m","choices":[{"delta":{},"finish_reason":"stop"}]}\n'
        b'data: {"id":"r","model":"m","choices":[],'
               b'"usage":{"prompt_tokens":1,"completion_tokens":1,"total_tokens":2}}'
               + delimiter + b'data: [DONE]' + delimiter)
    response.iter_content.return_value = [payload[:11], payload[11:37], payload[37:-1], payload[-1:]]
    with patch("home.omniroute_client.requests.Session.post", return_value=response):
        events = list(client.chat_completion_stream([{"role": "user", "content": "Test"}]))
    assert events[-2].usage == OmnirouteUsage(1, 1, 2)
    assert events[-1].event == "done"
    response.close.assert_called_once_with()


def test_sse_without_done_marker_is_rejected(client):
    response = Mock(); response.status_code = 200
    response.iter_content.return_value = map(lambda line: line + b'\n', [b'data: {"id":"resp-1","model":"example/model","choices":[{"delta":{"content":"partial"}}]}'])
    with patch("home.omniroute_client.requests.Session.post", return_value=response):
        with pytest.raises(OutcomeUnknown, match="stream_invalid"):
            list(client.chat_completion_stream([{"role": "user", "content": "Test"}]))


def test_sse_without_usage_is_rejected(client):
    response = Mock(); response.status_code = 200
    response.iter_content.return_value = map(lambda line: line + b'\n', [
        b'data: {"id":"resp-1","model":"example/model","choices":[{"delta":{"content":"partial"}}]}',
        b"data: [DONE]",
    ])
    with patch("home.omniroute_client.requests.Session.post", return_value=response):
        with pytest.raises(OutcomeUnknown, match="stream_invalid"):
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
    mock_get.return_value.headers = {}
    mock_get.return_value.iter_content.return_value = [b'{"status":"ok"}']
    client.timeout = 7
    client.health_check()
    assert mock_get.call_args.kwargs["timeout"] == 7


@pytest.mark.parametrize("body", [b"{bad secret", b"x" * (2 * 1024 * 1024 + 1)])
def test_health_check_rejects_invalid_or_oversized_body_without_leaking(client, body):
    response = Mock(status_code=200, headers={})
    response.iter_content.return_value = [body]
    with patch("home.omniroute_client.requests.Session.get", return_value=response) as get:
        with pytest.raises(OmnirouteError) as error:
            client.health_check()
    assert "secret" not in str(error.value)
    assert get.call_args.kwargs["stream"] is True
    response.close.assert_called_once_with()


@patch("home.omniroute_client.requests.Session.post")
def test_http_rejection_closes_response_without_leaking_body(mock_post, client):
    response = Mock(status_code=401, text="secret response body")
    mock_post.return_value = response
    with pytest.raises(OutcomeUnknown, match="failed_401") as error:
        client.chat_completion([{"role": "user", "content": "Test"}])
    response.close.assert_called_once_with()
    assert "secret response body" not in str(error.value)


@patch("home.omniroute_client.requests.Session.post")
def test_http_rejection_closes_session(mock_post, client):
    response = Mock(status_code=401, text="secret response body")
    mock_post.return_value = response
    with patch.object(client, "close", wraps=client.close) as close:
        with pytest.raises(OutcomeUnknown, match="failed_401"):
            client.chat_completion([{"role": "user", "content": "Test"}])
    close.assert_called_once_with()


@pytest.mark.parametrize("status", [401, 403, 404, 409, 422, 429, 500, 503])
def test_chat_http_error_does_not_prove_upstream_was_not_dispatched(client, status):
    response = Mock(status_code=status)
    with patch("home.omniroute_client.requests.Session.post", return_value=response):
        with pytest.raises(OutcomeUnknown, match=f"failed_{status}"):
            client.chat_completion([{"role": "user", "content": "Test"}])
    response.close.assert_called_once_with()


@patch("home.omniroute_client.requests.Session.post", side_effect=requests.ConnectionError("connection failed"))
def test_transport_failure_closes_session(mock_post, client):
    with patch.object(client, "close", wraps=client.close) as close:
        with pytest.raises(Exception, match="transport_failure"):
            client.chat_completion([{"role": "user", "content": "Test"}])
    close.assert_called_once_with()


@patch("home.omniroute_client.requests.Session.post", side_effect=requests.Timeout("request timed out"))
def test_timeout_closes_session(mock_post, client):
    with patch.object(client, "close", wraps=client.close) as close:
        with pytest.raises(Exception, match="omniroute_timeout"):
            client.chat_completion([{"role": "user", "content": "Test"}])
    close.assert_called_once_with()


@patch("home.omniroute_client.requests.Session.get")
def test_health_check_rejection_closes_response_and_session(mock_get, client):
    response = Mock(status_code=401, text="gateway secret body")
    mock_get.return_value = response
    with patch.object(client, "close", wraps=client.close) as close:
        with pytest.raises(Exception, match="rejected_401") as error:
            client.health_check()
    response.close.assert_called_once_with()
    close.assert_called_once_with()
    assert "gateway secret body" not in str(error.value)


@patch("home.omniroute_client.requests.Session.post")
def test_successful_stream_closes_response_and_session(mock_post, client):
    response = Mock(status_code=200)
    response.iter_content.return_value = map(lambda line: line + b'\n', [
        b'data: {"id":"resp-1","model":"example/model","choices": [{"delta": {"content": "ok"}}]}',
        b'data: {"id":"resp-1","model":"example/model","choices":[{"delta":{},"finish_reason":"stop"}]}\n'
        b'data: {"id":"resp-1","model":"example/model","choices":[],"usage":{"prompt_tokens":1,"completion_tokens":1,"total_tokens":2}}',
        b"data: [DONE]",
    ])
    mock_post.return_value = response
    with patch.object(client, "close", wraps=client.close) as close:
        list(client.chat_completion_stream([{"role": "user", "content": "Test"}]))
    response.close.assert_called_once_with()
    close.assert_called_once_with()


@patch("home.omniroute_client.requests.Session.get", side_effect=requests.ConnectionError("credential=secret"))
def test_health_check_transport_error_does_not_leak_request_message(mock_get, client):
    with pytest.raises(Exception, match="health_failure") as error:
        client.health_check()
    assert "credential=secret" not in str(error.value)


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


def test_gateway_post_disables_implicit_proxy_and_redirects(client):
    session = MagicMock()
    response = MagicMock(status_code=307)
    session.post.return_value = response
    with patch("home.omniroute_client.requests.Session", return_value=session):
        with pytest.raises(OutcomeUnknown, match="failed_307"):
            client.chat_completion([{"role": "user", "content": "synthetic"}])
    assert session.trust_env is False
    assert session.post.call_count == 1
    assert session.post.call_args.kwargs["allow_redirects"] is False
    response.close.assert_called_once_with()
    session.close.assert_called_once_with()


def test_gateway_get_disables_implicit_proxy_and_redirects(client):
    session = MagicMock()
    response = MagicMock(status_code=302)
    session.get.return_value = response
    with patch("home.omniroute_client.requests.Session", return_value=session):
        with pytest.raises(OmnirouteError, match="health_failed_302"):
            client.health_check()
    assert session.trust_env is False
    assert session.get.call_count == 1
    assert session.get.call_args.kwargs["allow_redirects"] is False
    response.close.assert_called_once_with()
    session.close.assert_called_once_with()


if __name__ == "__main__":
    # Ejecutar tests con pytest
    pytest.main([__file__, "-v"])
