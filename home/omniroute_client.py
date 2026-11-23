"""Defensive OpenAI-compatible client for the local omniroute gateway."""
import json, logging, os, re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional
import requests
from home.provider_outcomes import NotDispatched, OutcomeUnknown
from home.provider_credentials import (
    CredentialConfigError,
    load_omniroute_endpoint,
    load_omniroute_key,
)

logger = logging.getLogger(__name__)
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_SSE_LINE_BYTES = 256 * 1024
MAX_SSE_EVENTS = 4096
_SSE_DELIMITER = re.compile(b"[\r\n]")

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
        if (not isinstance(data.get("id"), str) or not data["id"].strip()
                or not isinstance(data.get("model"), str) or not data["model"].strip()):
            raise OmnirouteError("gateway_response_invalid")
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


def _iter_bounded_sse_lines(response):
    """Read bounded bytes before buffering a complete SSE line."""
    pending = bytearray()
    total = 0
    skip_lf = False
    for chunk in response.iter_content(chunk_size=64 * 1024):
        if not isinstance(chunk, bytes):
            raise OmnirouteError("gateway_sse_malformed")
        total += len(chunk)
        if total > MAX_RESPONSE_BYTES:
            raise OmnirouteError("gateway_sse_too_large")
        offset = 0
        if skip_lf and chunk:
            skip_lf = False
            if chunk[0] == 10:
                offset = 1
        for match in _SSE_DELIMITER.finditer(chunk, offset):
            end = match.start()
            if end < offset:
                continue
            if end - offset > MAX_SSE_LINE_BYTES - len(pending):
                raise OmnirouteError("gateway_sse_line_too_large")
            pending.extend(chunk[offset:end])
            yield bytes(pending)
            pending.clear()
            offset = end + 1
            if chunk[end] == 13:
                if offset == len(chunk):
                    skip_lf = True
                elif chunk[offset] == 10:
                    offset += 1
        if len(chunk) - offset > MAX_SSE_LINE_BYTES - len(pending):
            raise OmnirouteError("gateway_sse_line_too_large")
        pending.extend(chunk[offset:])
    if pending:
        yield bytes(pending)


def _read_bounded_json(response):
    length = response.headers.get("Content-Length", "")
    if isinstance(length, str) and length.isdigit() and int(length) > MAX_RESPONSE_BYTES:
        raise OmnirouteError("gateway_response_too_large")
    body = bytearray()
    for chunk in response.iter_content(chunk_size=64 * 1024):
        if not isinstance(chunk, bytes):
            raise OmnirouteError("gateway_response_invalid")
        if len(chunk) > MAX_RESPONSE_BYTES - len(body):
            raise OmnirouteError("gateway_response_too_large")
        body.extend(chunk)
    try:
        return json.loads(body)
    except (ValueError, UnicodeDecodeError, RecursionError) as exc:
        raise OmnirouteError("gateway_response_invalid") from exc


class OmnirouteClient:
    def __init__(self, endpoint: Optional[str] = None, api_key: Optional[str] = None, timeout: int = 60):
        if endpoint is not None:
            try:
                endpoint = load_omniroute_endpoint({"OMNIROUTE_ENDPOINT": endpoint})
            except CredentialConfigError as exc:
                raise ValueError("endpoint_invalid") from exc
        self._endpoint = endpoint
        if api_key is not None:
            try:
                # Keep explicitly injected credentials under the same strict
                # validation as environment/systemd configuration.
                api_key = load_omniroute_key({"OMNIROUTE_API_KEY": api_key})
            except CredentialConfigError as exc:
                raise ValueError("api_key_invalid") from exc
        self._api_key = api_key
        if type(timeout) is not int or timeout <= 0: raise ValueError("timeout_invalid")
        self.timeout, self._session = timeout, None
    @property
    def endpoint(self):
        if self._endpoint is not None:
            return self._endpoint.rstrip("/")
        try:
            return load_omniroute_endpoint(os.environ)
        except CredentialConfigError as exc:
            raise OmnirouteError("omniroute_endpoint_invalid") from exc

    @property
    def api_key(self):
        if self._api_key is not None:
            return self._api_key
        try:
            return load_omniroute_key(os.environ)
        except CredentialConfigError as exc:
            raise OmnirouteError("omniroute_credentials_invalid") from exc

    def _session_for_request(self):
        key = self.api_key
        if not key: raise NotDispatched("omniroute_credentials_missing")
        self._session = requests.Session()
        # Do not route protected prompts or gateway credentials through a
        # proxy selected implicitly from the process environment.
        self._session.trust_env = False
        self._session.headers.update({"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        return self._session
    @staticmethod
    def _raise_http(response, operation):
        if 200 <= response.status_code < 300: return
        # A gateway error may be forwarded from an upstream provider after
        # dispatch. The status alone does not prove that no usage occurred.
        if operation == "chat":
            raise OutcomeUnknown(f"omniroute_chat_failed_{response.status_code}")
        if response.status_code in (401, 403, 404, 409, 422, 429): raise NotDispatched(f"omniroute_{operation}_rejected_{response.status_code}")
        raise OmnirouteError(f"omniroute_{operation}_failed_{response.status_code}")
    def _post(self, payload, stream=False):
        session = self._session_for_request()
        try:
            response = session.post(f"{self.endpoint}/chat/completions", json=payload, stream=stream,
                                    timeout=self.timeout, allow_redirects=False)
            try:
                self._raise_http(response, "chat")
            except Exception:
                response.close()
                raise
            return response
        except requests.Timeout as exc:
            self.close()
            raise OutcomeUnknown("omniroute_timeout") from exc
        except requests.RequestException as exc:
            self.close()
            raise OutcomeUnknown("omniroute_transport_failure") from exc
        except Exception:
            self.close()
            raise
    @staticmethod
    def _validate_chat_request(messages, model, temperature, max_tokens):
        if (not isinstance(messages, list) or not messages
                or any(not isinstance(message, dict) for message in messages)):
            raise ValueError("messages_invalid")
        if not isinstance(model, str) or not model.strip():
            raise ValueError("model_invalid")
        if isinstance(temperature, bool) or not isinstance(temperature, (int, float)):
            raise ValueError("temperature_invalid")
        if max_tokens is not None and (type(max_tokens) is not int or max_tokens <= 0):
            raise ValueError("max_tokens_invalid")
    def chat_completion(self, messages: List[Dict[str, str]], model="nous-ai/solar-mini-4", temperature=0.7, max_tokens=None, stream=False, reasoning=None, tools=None, **kwargs):
        if stream: raise ValueError("use chat_completion_stream for streaming")
        self._validate_chat_request(messages, model, temperature, max_tokens)
        payload = {"model": model, "messages": messages, "temperature": temperature, **kwargs}
        if max_tokens is not None: payload["max_tokens"] = max_tokens
        if reasoning is not None: payload["reasoning"] = reasoning
        if tools is not None: payload["tools"] = tools
        # Keep the response streamed even for the non-SSE API: Requests would
        # otherwise buffer an unbounded body before we can enforce our limit.
        response = self._post(payload, stream=True)
        try:
            length = response.headers.get("Content-Length", 0)
            if isinstance(length, str) and length.isdigit() and int(length) > MAX_RESPONSE_BYTES: raise OmnirouteError("gateway_response_too_large")
            body = bytearray()
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if not isinstance(chunk, bytes):
                    raise OmnirouteError("gateway_response_invalid")
                if len(chunk) > MAX_RESPONSE_BYTES - len(body):
                    raise OmnirouteError("gateway_response_too_large")
                body.extend(chunk)
            return OmnirouteResponse.from_dict(json.loads(body))
        except (ValueError, OverflowError, OSError, RecursionError, OmnirouteError, requests.RequestException) as exc:
            # The response was received after dispatch; parsing failure does
            # not establish whether the upstream request consumed tokens.
            raise OutcomeUnknown("omniroute_response_invalid") from exc
        finally: response.close(); self.close()
    def chat_completion_stream(self, messages: List[Dict[str, str]], model="nous-ai/solar-mini-4", temperature=0.7, max_tokens=None, **kwargs) -> Iterator[OmnirouteStreamEvent]:
        self._validate_chat_request(messages, model, temperature, max_tokens)
        payload = {"model": model, "messages": messages, "temperature": temperature, **kwargs,
                   "stream": True, "stream_options": {"include_usage": True}}
        if max_tokens is not None: payload["max_tokens"] = max_tokens
        response = self._post(payload, stream=True)
        try:
            event_count = 0
            completed = False
            usage_seen = False
            finish_seen = False
            response_id = None
            response_model = None
            for raw_line in _iter_bounded_sse_lines(response):
                if not raw_line: continue
                event_count += 1
                if event_count > MAX_SSE_EVENTS: raise OmnirouteError("gateway_sse_too_many_events")
                try:
                    line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
                except UnicodeDecodeError as exc:
                    raise OmnirouteError("gateway_sse_malformed") from exc
                if not line.startswith("data:"): continue
                value = line[5:].strip()
                if value == "[DONE]":
                    completed = True
                    if not usage_seen:
                        raise OmnirouteUsageError("gateway_usage_missing")
                    if not finish_seen:
                        raise OmnirouteError("gateway_finish_missing")
                    yield OmnirouteStreamEvent("done")
                    return
                try: data = json.loads(value)
                except (TypeError, ValueError, RecursionError) as exc: raise OmnirouteError("gateway_sse_malformed") from exc
                if not isinstance(data, dict):
                    raise OmnirouteError("gateway_sse_schema_invalid")
                event_id, event_model = data.get("id"), data.get("model")
                if (not isinstance(event_id, str) or not event_id.strip()
                        or not isinstance(event_model, str) or not event_model.strip()):
                    raise OmnirouteError("gateway_sse_identity_missing")
                if response_id is None:
                    response_id, response_model = event_id, event_model
                elif event_id != response_id or event_model != response_model:
                    raise OmnirouteError("gateway_sse_identity_changed")
                choices = data.get("choices") if isinstance(data, dict) else None
                if not isinstance(choices, list): raise OmnirouteError("gateway_sse_schema_invalid")
                # OpenAI-compatible streams may send usage in a final chunk
                # with no choices before the [DONE] sentinel.
                if not choices:
                    if not isinstance(data, dict) or "usage" not in data:
                        raise OmnirouteError("gateway_sse_schema_invalid")
                    if usage_seen:
                        raise OmnirouteUsageError("gateway_usage_duplicate")
                    usage = OmnirouteUsage.from_dict(data["usage"])
                    usage_seen = True
                    yield OmnirouteStreamEvent("delta", "", None, usage)
                    continue
                if len(choices) != 1 or not isinstance(choices[0], dict): raise OmnirouteError("gateway_sse_schema_invalid")
                choice, delta = choices[0], choices[0].get("delta", {})
                if (not isinstance(delta, dict) or not isinstance(delta.get("content", ""), str)
                        or (choice.get("finish_reason") is not None and not isinstance(choice.get("finish_reason"), str))):
                    raise OmnirouteError("gateway_sse_schema_invalid")
                if finish_seen:
                    raise OmnirouteError("gateway_sse_after_finish")
                if choice.get("finish_reason") is not None:
                    if choice["finish_reason"] != "stop":
                        raise OmnirouteError("gateway_finish_incomplete")
                    finish_seen = True
                usage = OmnirouteUsage.from_dict(data["usage"]) if "usage" in data else None
                if usage is not None:
                    if usage_seen:
                        raise OmnirouteUsageError("gateway_usage_duplicate")
                    usage_seen = True
                yield OmnirouteStreamEvent("delta", delta.get("content", ""), choice.get("finish_reason"), usage)
            if not completed:
                raise OmnirouteError("gateway_sse_truncated")
            if not usage_seen:
                raise OmnirouteUsageError("gateway_usage_missing")
        except (OSError, requests.RequestException) as exc: raise OutcomeUnknown("omniroute_stream_failure") from exc
        except OmnirouteError as exc:
            # Parsing fails after the POST was accepted, even if no event was
            # yielded. The upstream request may already have consumed tokens.
            raise OutcomeUnknown("omniroute_stream_invalid") from exc
        finally: response.close(); self.close()
    def _get(self, path, missing_ok=False):
        session = self._session_for_request()
        try:
            response = session.get(f"{self.endpoint.removesuffix('/v1')}/{path}", timeout=self.timeout,
                                   allow_redirects=False, stream=True)
            if missing_ok and response.status_code == 404: return {}
            self._raise_http(response, path); data = _read_bounded_json(response)
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
def chat_with_external_model(messages, **kwargs):
    raise NotDispatched("gateway_admission_unavailable")


def chat_with_local_model(messages, **kwargs):
    # A gateway alias alone does not verify local execution.
    raise NotDispatched("gateway_locality_unverified")


def memory_agent_search(query, *, user=None, operation_id=None, risk_accepted=False):
    """Run the pinned Nous memory route through its fail-closed budget boundary."""
    if (user is None or not getattr(user, "is_authenticated", False)
            or not getattr(user, "is_active", False)
            or not isinstance(operation_id, str) or not operation_id.strip()):
        raise NotDispatched("memory_route_unavailable")
    from home.memory_agent_dispatch import dispatch_memory_agent
    return dispatch_memory_agent(
        query=query,
        user=user,
        operation_id=operation_id,
        risk_accepted=risk_accepted,
    )


def memory_agent_recall(query, reason, *, user=None, budget=None, caller=None,
                        operation_id=None, risk_accepted=False):
    """Bounded recall call routed through the same budgeted Nous dispatcher."""
    from home.memory_agent_dispatch import memory_agent_recall as dispatch_recall
    return dispatch_recall(
        query=query,
        reason=reason,
        user=user,
        budget=budget,
        caller=caller,
        operation_id=operation_id,
        risk_accepted=risk_accepted,
    )
