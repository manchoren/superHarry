"""Disabled-by-default OpenRouter adapter; caller must supply trusted evidence.

Evidence callbacks must verify current policy and never be user-controlled.
This module does not configure, enable, or register any provider.
"""

import json
from datetime import datetime, timezone

from home.chat_events import MAX_OUTPUT_CONTENT_BYTES
from home.constitution_context import ensure_prepared_context_integrity
from home.model_interface import (
    ContentTrust,
    MessageRole,
    ModelCancelled,
    ModelCompleted,
    ModelError,
    ModelErrorCategory,
    ModelFailed,
    ModelMode,
    ModelStarted,
    ModelTextDelta,
    ModelUsageUpdate,
    OutcomeCertainty,
    RequesterRole,
    UsageSource,
    require_capabilities,
    validate_invocation,
)
from home.provider_http_transport import MAX_REQUEST_BYTES, ProviderTransport

_MAX_RESPONSE_BYTES = 128 * 1024


def build_payload(messages, model_id, upstream_id, output_limit):
    return {
        'model': model_id,
        'messages': [
            {'role': 'system', 'content': messages[0].parts[0].text},
            {'role': 'user', 'content': messages[1].parts[0].text},
        ],
        'max_completion_tokens': output_limit,
        'stream': False,
        'provider': {
            'only': [upstream_id],
            'allow_fallbacks': False,
            'require_parameters': True,
            'max_price': {'prompt': 0, 'completion': 0},
            'data_collection': 'deny',
            'zdr': True,
        },
    }


def _decode(raw):
    if not isinstance(raw, bytes) or len(raw) > _MAX_RESPONSE_BYTES:
        raise ValueError('invalid response')

    def pairs(items):
        obj = {}
        for key, value in items:
            if key in obj:
                raise ValueError('duplicate')
            obj[key] = value
        return obj

    def reject_constant(_):
        raise ValueError('constant')

    parsed = json.loads(
        raw.decode('utf-8'),
        object_pairs_hook=pairs,
        parse_constant=reject_constant,
    )
    if not isinstance(parsed, dict):
        raise ValueError('invalid response')
    return parsed


class OpenRouterAdapter:
    def __init__(
        self, *, transport, report, model_id, upstream_id, verify_context,
        verify_free, verify_privacy, verify_credential, verify_response,
    ):
        if (
            type(transport) is not ProviderTransport
            or transport._host != 'openrouter.ai'
            or transport._path != '/api/v1/chat/completions'
            or not isinstance(model_id, str)
            or not model_id.endswith(':free')
            or not isinstance(upstream_id, str)
            or not upstream_id.strip()
            or model_id.casefold().startswith('openai/')
            or upstream_id.casefold().split('/')[0] == 'openai'
            or any(not callable(x) for x in (
                verify_context, verify_free, verify_privacy, verify_credential,
                verify_response,
            ))
        ):
            raise ValueError('openrouter_configuration_invalid')
        self.transport, self.capability_report, self.model_id, self.upstream_id = (
            transport, report, model_id, upstream_id
        )
        self.verify_context, self.verify_free, self.verify_privacy = (
            verify_context, verify_free, verify_privacy
        )
        self.verify_credential = verify_credential
        self.verify_response = verify_response

    def stream(self, request, context):
        sequence = 1
        yield ModelStarted(
            sequence, self.capability_report.adapter_id,
            self.capability_report.revision,
        )
        sequence += 1
        dispatched = False
        try:
            validate_invocation(request, context)
            if (
                context.role not in (RequesterRole.USER, RequesterRole.ADMIN)
                or context.mode is not ModelMode.AUTOMATIC
            ):
                raise ValueError('scope')
            require_capabilities(
                self.capability_report, request.capability_requirements,
                now=datetime.now(timezone.utc),
            )
            if context.deadline is not None and datetime.now(timezone.utc) >= context.deadline:
                raise ValueError('deadline')
            if context.cancellation is not None and context.cancellation.is_cancelled:
                yield ModelCancelled(sequence, backend_stop_confirmed=True)
                return
            options = request.requested_options
            if (
                options.model_id != self.model_id
                or type(options.output_token_limit) is not int
                or options.output_token_limit <= 0
                or options.reasoning_effort is not None
                or options.service_mode is not None
                or options.response_format is not None
                or len(request.messages) != 2
            ):
                raise ValueError('options')
            protected, user = request.messages
            if (
                protected.role is not MessageRole.SYSTEM
                or len(protected.parts) != 1
                or protected.parts[0].trust is not ContentTrust.PROTECTED
                or user.role is not MessageRole.USER
                or len(user.parts) != 1
                or user.parts[0].trust is not ContentTrust.USER
            ):
                raise ValueError('messages')
            prepared = request.context.prepared_context
            ensure_prepared_context_integrity(prepared)
            if (
                prepared.output_reserve < options.output_token_limit
                or prepared.constitution.text != protected.parts[0].text
                or prepared.user_request != user.parts[0].text
                or self.transport._host != 'openrouter.ai'
                or self.transport._path != '/api/v1/chat/completions'
                or self.verify_credential(self.transport) is not True
            ):
                raise ValueError('binding')
            payload = build_payload(
                request.messages, self.model_id, self.upstream_id,
                options.output_token_limit,
            )
            body = json.dumps(
                payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
            ).encode('utf-8')
            if (
                len(body) > MAX_REQUEST_BYTES
                or body != prepared.serialized_input
                or self.verify_context(prepared) is not True
                or self.verify_free(self.model_id, self.upstream_id) is not True
                or self.verify_privacy(self.model_id, self.upstream_id) is not True
            ):
                raise ValueError('verification')
            if context.cancellation is not None and context.cancellation.is_cancelled:
                yield ModelCancelled(sequence, backend_stop_confirmed=True)
                return
            dispatched = True
            status, raw = self.transport.send(body)
            if context.cancellation is not None and context.cancellation.is_cancelled:
                yield ModelCancelled(sequence, backend_stop_confirmed=None)
                return
            if context.deadline is not None and datetime.now(timezone.utc) >= context.deadline:
                raise ValueError('deadline')
            if type(status) is not int:
                raise ValueError('status')
            if status != 200:
                raise ValueError('status')
            response = _decode(raw)
            if (
                response.get('object') != 'chat.completion'
                or response.get('model') != self.model_id
                or self.verify_response(response, self.model_id, self.upstream_id) is not True
            ):
                raise ValueError('identity')
            choices = response.get('choices')
            if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
                raise ValueError('choices')
            choice = choices[0]
            message = choice.get('message')
            if (
                choice.get('index') != 0
                or choice.get('finish_reason') != 'stop'
                or not isinstance(message, dict)
                or message.get('role') != 'assistant'
                or set(message) - {'role', 'content', 'refusal'}
                or message.get('refusal') is not None
            ):
                raise ValueError('message')
            content = message.get('content')
            usage = response.get('usage')
            if (
                not isinstance(content, str)
                or not content
                or len(content.encode('utf-8')) > MAX_OUTPUT_CONTENT_BYTES
                or not isinstance(usage, dict)
            ):
                raise ValueError('content')
            inp, out = usage.get('prompt_tokens'), usage.get('completion_tokens')
            if (
                type(inp) is not int
                or inp < 0
                or type(out) is not int
                or out < 0
                or self.verify_context(prepared) is not True
                or self.verify_free(self.model_id, self.upstream_id) is not True
                or self.verify_privacy(self.model_id, self.upstream_id) is not True
                or self.verify_credential(self.transport) is not True
            ):
                raise ValueError('usage')
            yield ModelTextDelta(sequence, content)
            sequence += 1
            if context.cancellation is not None and context.cancellation.is_cancelled:
                yield ModelCancelled(sequence, backend_stop_confirmed=None)
                return
            yield ModelUsageUpdate(sequence, UsageSource.PROVIDER_REPORTED, inp, out, complete=True)
            sequence += 1
            if context.cancellation is not None and context.cancellation.is_cancelled:
                yield ModelCancelled(sequence, backend_stop_confirmed=None)
                return
            yield ModelCompleted(sequence)
        except Exception:
            yield ModelFailed(
                sequence,
                ModelError(
                    ModelErrorCategory.INTERNAL, 'openrouter_provider_failed', False,
                    OutcomeCertainty.UNKNOWN if dispatched else OutcomeCertainty.NOT_DISPATCHED,
                ),
            )
