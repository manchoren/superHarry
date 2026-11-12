"""Defensive OpenAI-compatible client for the local omniroute gateway."""
import json, logging, os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional
import requests
from home.provider_outcomes import NotDispatched, OutcomeUnknown

logger = logging.getLogger(__name__)
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_SSE_LINE_BYTES = 256 * 1024
MAX_SSE_EVENTS = 4096

class OmnirouteError(RuntimeError):
    """Gateway failure without credentials or response-body leakage."""

class OmnirouteUsageError(OmnirouteError):
    """Gateway did not return trustworthy usage."""

@dataclass(frozen=True)
class OmnirouteUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OmnirouteUsage":
        if not isinstance(data, dict): raise OmnirouteUsageError("gateway_usage_invalid")
        values = tuple(data.get(k) for k in ("prompt_tokens", "completion_tokens", "total_tokens"))
        if any(type(v) is not int or v < 0 for v in values) or values[2] != values[0] + values[1]:
            raise OmnirouteUsageError("gateway_usage_invalid")
        return cls(*values)

@dataclass(frozen=True)
class OmnirouteResponse:
    id: str; model: str; content: str; finish_reason: str; usage: OmnirouteUsage; created: datetime; raw: Dict[str, Any]
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OmnirouteResponse":
        if not isinstance(data, dict) or data.get("object") != "chat.completion": raise OmnirouteError("gateway_response_invalid")
        if not isinstance(data.get("id"), str) or not isinstance(data.get("model"), str): raise OmnirouteError("gateway_response_invalid")
        choices = data.get("choices")
        if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict): raise OmnirouteError("gateway_response_invalid")
        choice, message = choices[0], choices[0].get("message")
        if (choice.get("index") != 0 or not isinstance(message, dict) or message.get("role") != "assistant"
                or not isinstance(message.get("content"), str) or not isinstance(choice.get("finish_reason"), str)):
            raise OmnirouteError("gateway_response_invalid")
        created = data.get("created")
        if type(created) is not int or created < 0: raise OmnirouteError("gateway_response_invalid")
        return cls(data["id"], data["model"], message["content"], choice["finish_reason"],
                   OmnirouteUsage.from_dict(data.get("usage")), datetime.fromtimestamp(created, tz=timezone.utc), data)

@dataclass(frozen=True)
class OmnirouteStreamEvent:
    event: str; content: str = ""; finish_reason: Optional[str] = None; usage: Optional[OmnirouteUsage] = None

class OmnirouteClient:
    def __init__(self, endpoint: Optional[str] = None, api_key: Optional[str] = None, timeout: int = 60):
        self._endpoint = endpoint.rstrip("/") if endpoint else None
        self._api_key = api_key
        if type(timeout) is not int or timeout <= 0: raise ValueError("timeout_invalid")
        self.timeout, self._session = timeout, None
    @property
    def endpoint(self):
        return (self._endpoint or os.getenv("OMNIROUTE_ENDPOINT", "http://localhost:20128/v1")).rstrip("/")

    @property
    def api_key(self):
        return self._api_key if self._api_key is not None else os.getenv("OMNIROUTE_API_KEY")

    def _session_for_request(self):
        key = self.api_key
        if not key: raise NotDispatched("omniroute_credentials_missing")
        self._session = requests.Session()
        self._session.headers.update({"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        return self._session
    @staticmethod
    def _raise_http(response, operation):
        if 200 <= response.status_code < 300: return
        if response.status_code in (401, 403, 404, 409, 422, 429): raise NotDispatched(f"omniroute_{operation}_rejected_{response.status_code}")
        raise OmnirouteError(f"omniroute_{operation}_failed_{response.status_code}")
    def _post(self, payload, stream=False):
        session = self._session_for_request()
        try:
            response = session.post(f"{self.endpoint}/chat/completions", json=payload, stream=stream, timeout=self.timeout)
            try:
                self._raise_http(response, "chat")
            except Exception:
                response.close()
                raise
            return response
        except requests.Timeout as exc: raise OutcomeUnknown("omniroute_timeout") from exc
        except requests.RequestException as exc: raise OutcomeUnknown("omniroute_transport_failure") from exc
    def chat_completion(self, messages: List[Dict[str, str]], model="nous-ai/solar-mini-4", temperature=0.7, max_tokens=None, stream=False, reasoning=None, tools=None, **kwargs):
        if stream: raise ValueError("use chat_completion_stream for streaming")
        payload = {"model": model, "messages": messages, "temperature": temperature, **kwargs}
        if max_tokens is not None: payload["max_tokens"] = max_tokens
        if reasoning is not None: payload["reasoning"] = reasoning
        if tools is not None: payload["tools"] = tools
        response = self._post(payload)
        try:
            length = response.headers.get("Content-Length", 0)
            if isinstance(length, str) and length.isdigit() and int(length) > MAX_RESPONSE_BYTES: raise OmnirouteError("gateway_response_too_large")
            return OmnirouteResponse.from_dict(response.json())
        except (ValueError, json.JSONDecodeError) as exc: raise OmnirouteError("gateway_response_invalid") from exc
        finally: response.close(); self.close()
    def chat_completion_stream(self, messages: List[Dict[str, str]], model="nous-ai/solar-mini-4", temperature=0.7, max_tokens=None, **kwargs) -> Iterator[OmnirouteStreamEvent]:
        payload = {"model": model, "messages": messages, "temperature": temperature, "stream": True, **kwargs}
        if max_tokens is not None: payload["max_tokens"] = max_tokens
        response = self._post(payload, stream=True)
        try:
            event_count = 0
            for raw_line in response.iter_lines():
                if not raw_line: continue
                if len(raw_line) > MAX_SSE_LINE_BYTES: raise OmnirouteError("gateway_sse_line_too_large")
                event_count += 1
                if event_count > MAX_SSE_EVENTS: raise OmnirouteError("gateway_sse_too_many_events")
                try:
                    line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
                except UnicodeDecodeError as exc:
                    raise OmnirouteError("gateway_sse_malformed") from exc
                if not line.startswith("data:"): continue
                value = line[5:].strip()
                if value == "[DONE]": yield OmnirouteStreamEvent("done"); return
                try: data = json.loads(value)
                except (TypeError, json.JSONDecodeError) as exc: raise OmnirouteError("gateway_sse_malformed") from exc
                choices = data.get("choices") if isinstance(data, dict) else None
                if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict): raise OmnirouteError("gateway_sse_schema_invalid")
                choice, delta = choices[0], choices[0].get("delta", {})
                if (not isinstance(delta, dict) or not isinstance(delta.get("content", ""), str)
                        or (choice.get("finish_reason") is not None and not isinstance(choice.get("finish_reason"), str))):
                    raise OmnirouteError("gateway_sse_schema_invalid")
                usage = OmnirouteUsage.from_dict(data["usage"]) if "usage" in data else None
                yield OmnirouteStreamEvent("delta", delta.get("content", ""), choice.get("finish_reason"), usage)
        except (requests.Timeout, requests.RequestException) as exc: raise OutcomeUnknown("omniroute_stream_failure") from exc
        finally: response.close(); self.close()
    def _get(self, path, missing_ok=False):
        session = self._session_for_request()
        try:
            response = session.get(f"{self.endpoint.removesuffix('/v1')}/{path}", timeout=self.timeout)
            if missing_ok and response.status_code == 404: return {}
            self._raise_http(response, path); data = response.json()
            if not isinstance(data, dict): raise OmnirouteError("gateway_response_invalid")
            return data
        except requests.RequestException as exc: raise OutcomeUnknown(f"omniroute_{path}_failure") from exc
        finally:
            if "response" in locals(): response.close()
            self.close()
    def health_check(self): return self._get("health")
    def get_usage_stats(self): return self._get("usage", True)
    def close(self):
        if self._session is not None: self._session.close(); self._session = None

omniroute_client = OmnirouteClient()
def chat_with_external_model(messages, **kwargs): return omniroute_client.chat_completion(messages=messages, model="nous-ai/solar-mini-4", **kwargs)
def chat_with_local_model(messages, **kwargs): return omniroute_client.chat_completion(messages=messages, model="ollama/qwen3.5:4b", **kwargs)
def memory_agent_search(query, conversation_context=None):
    messages = list(conversation_context or []); messages.append({"role": "user", "content": query})
    return omniroute_client.chat_completion(messages=messages, model="nous-ai/solar-mini-4", reasoning=False, temperature=0.3, max_tokens=500)
