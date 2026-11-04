"""Bounded Responses stream adapter; not wired into the application runtime.

The caller must supply independently verified capability, context and budget
checks. This module alone does not implement accounting, fallback, admission,
tokenization, durable recovery or an authorization policy.
"""

import logging
import math
from datetime import datetime, timezone

from home.chat_events import MAX_OUTPUT_CONTENT_BYTES
from home.model_interface import (
    ContentTrust, MessageRole, ModelCancelled, ModelCompleted, ModelError,
    ModelErrorCategory, ModelFailed, ModelMode, ModelStarted, ModelTextDelta,
    ModelUsageUpdate, OutcomeCertainty, RequesterRole, UsageSource,
    require_capabilities, validate_invocation,
)

logger = logging.getLogger(__name__)


class OpenAIResponsesAdapter:
    """Map a protected text request to an injected SDK client and typed events."""

    def __init__(self, *, client, report, model_id, timeout, verify_context, verify_budget):
        if not isinstance(model_id, str) or not model_id.strip():
            raise ValueError('invalid model')
        if type(timeout) not in (float, int) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError('invalid timeout')
        if not callable(verify_context) or not callable(verify_budget):
            raise ValueError('missing verification')
        self.client = client
        self.capability_report = report
        self.model_id = model_id
        self.timeout = float(timeout)
        self.verify_context = verify_context
        self.verify_budget = verify_budget

    def stream(self, request, context):
        sequence = 1
        yield ModelStarted(sequence, self.capability_report.adapter_id, self.capability_report.revision)
        sequence += 1
        source = None
        dispatched = False
        try:
            validate_invocation(request, context)
            if context.role not in (RequesterRole.USER, RequesterRole.ADMIN) or context.mode is ModelMode.LOCAL:
                raise ValueError('scope')
            require_capabilities(self.capability_report, request.capability_requirements, now=datetime.now(timezone.utc))
            options = request.requested_options
            if (options.model_id != self.model_id or options.output_token_limit is None
                    or options.reasoning_effort not in (None, 'low') or options.service_mode is not None
                    or options.response_format is not None):
                raise ValueError('options')
            if len(request.messages) != 2:
                raise ValueError('messages')
            protected, user = request.messages
            if (protected.role is not MessageRole.DEVELOPER or len(protected.parts) != 1
                    or protected.parts[0].trust is not ContentTrust.PROTECTED
                    or user.role is not MessageRole.USER or len(user.parts) != 1
                    or user.parts[0].trust is not ContentTrust.USER):
                raise ValueError('messages')
            prepared = request.context.prepared_context
            if options.output_token_limit > prepared.output_reserve:
                raise ValueError('reserve')
            if context.deadline is not None and datetime.now(timezone.utc) >= context.deadline:
                raise ValueError('deadline')
            if context.cancellation is not None and context.cancellation.is_cancelled:
                yield ModelCancelled(sequence, backend_stop_confirmed=True)
                return
            payload = {
                'model': self.model_id,
                'input': [{'role': 'developer', 'content': protected.parts[0].text},
                          {'role': 'user', 'content': user.parts[0].text}],
                'max_output_tokens': options.output_token_limit,
                'store': False,
                'truncation': 'disabled',
                'stream': True,
            }
            if options.reasoning_effort is not None:
                payload['reasoning'] = {'effort': options.reasoning_effort}
            self.verify_context(prepared)
            if self.verify_budget(prepared, payload) is not True:
                raise ValueError('budget')
            self.verify_context(prepared)
            if context.cancellation is not None and context.cancellation.is_cancelled:
                yield ModelCancelled(sequence, backend_stop_confirmed=True)
                return
            client = self.client.with_options(timeout=self.timeout, max_retries=0)
            dispatched = True
            source = client.responses.create(**payload)
            output_bytes = 0
            completed = False
            for event in source:
                if context.cancellation is not None and context.cancellation.is_cancelled:
                    yield ModelCancelled(sequence, backend_stop_confirmed=None)
                    return
                if context.deadline is not None and datetime.now(timezone.utc) >= context.deadline:
                    raise TimeoutError()
                event_type = getattr(event, 'type', None)
                if event_type == 'response.output_text.delta':
                    delta = getattr(event, 'delta', None)
                    if not isinstance(delta, str) or not delta:
                        raise ValueError('delta')
                    output_bytes += len(delta.encode('utf-8', errors='strict'))
                    if output_bytes > MAX_OUTPUT_CONTENT_BYTES:
                        raise ValueError('output limit')
                    self.verify_context(prepared)
                    yield ModelTextDelta(sequence, delta)
                    sequence += 1
                elif event_type == 'response.completed':
                    response = getattr(event, 'response', None)
                    if getattr(response, 'status', None) != 'completed':
                        raise ValueError('status')
                    usage = getattr(response, 'usage', None)
                    input_tokens = getattr(usage, 'input_tokens', None)
                    output_tokens = getattr(usage, 'output_tokens', None)
                    if (type(input_tokens) is not int or input_tokens < 0
                            or type(output_tokens) is not int or output_tokens < 0):
                        raise ValueError('usage')
                    self.verify_context(prepared)
                    yield ModelUsageUpdate(sequence, UsageSource.PROVIDER_REPORTED,
                                           input_tokens, output_tokens, complete=True)
                    sequence += 1
                    completed = True
                    break
                elif event_type in ('response.created', 'response.in_progress', 'response.output_text.done'):
                    continue
                elif event_type in ('response.output_item.added', 'response.output_item.done'):
                    if getattr(getattr(event, 'item', None), 'type', None) not in ('message', 'reasoning'):
                        raise ValueError('unexpected item')
                elif event_type in ('response.content_part.added', 'response.content_part.done'):
                    if getattr(getattr(event, 'part', None), 'type', None) != 'output_text':
                        raise ValueError('unexpected content')
                else:
                    raise ValueError('unexpected event')
            if not completed:
                raise ValueError('stream incomplete')
            yield ModelCompleted(sequence)
        except Exception:
            yield ModelFailed(sequence, ModelError(
                ModelErrorCategory.INTERNAL, 'openai_unavailable', False,
                OutcomeCertainty.UNKNOWN if dispatched else OutcomeCertainty.NOT_DISPATCHED,
            ))
        finally:
            if source is not None:
                try:
                    source.close()
                except Exception:
                    logger.warning('openai_stream_close_failed')
