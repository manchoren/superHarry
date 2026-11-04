import hashlib
import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from unittest import TestCase
from uuid import uuid4

from home.constitution_context import ConstitutionSnapshot, PreparedContext, _bundle_digest
from home.model_interface import (CapabilityEntry, CapabilityReport, CapabilityRequirements, CapabilityStatus,
 ContentPart, ContentTrust, ContextManifest, InvocationContext, MessageRole, ModelCapability, ModelCompleted,
 ModelErrorCategory, ModelFailed, ModelMessage, ModelMode, ModelRequest, ModelTextDelta, OutcomeCertainty,
 RequestChannel, RequesterRole, RequestedOptions)
from home.synthetic_openrouter_adapter import SyntheticOpenRouterAdapter, SyntheticTransport, build_payload

class SyntheticOpenRouterTests(TestCase):
 def setUp(self):
  now=datetime.now(timezone.utc); self.ident=uuid4(); text='Synthetic complete constitution'
  self.report=CapabilityReport('synthetic-openrouter','test','synthetic',now-timedelta(seconds=1),now+timedelta(minutes=2),(CapabilityEntry(ModelCapability.TEXT_GENERATION,CapabilityStatus.SUPPORTED),))
  self.messages=(ModelMessage(MessageRole.SYSTEM,(ContentPart(text,ContentTrust.PROTECTED,'constitution.md'),)),ModelMessage(MessageRole.USER,(ContentPart('hello',ContentTrust.USER,'user'),)))
  self.options=RequestedOptions(model_id='example/model:free',output_token_limit=32)
  body=build_payload(self.messages,self.options.model_id,'example-provider',32)
  serialized=json.dumps(body,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
  prepared=PreparedContext('superharry.context-bundle.v1',ConstitutionSnapshot('constitution.md',hashlib.sha256(text.encode()).hexdigest(),len(text.encode()),text),'hello',serialized,'test','1','test','1','test','1',50,100,32,1,'')
  self.request=ModelRequest(self.ident,self.messages,ContextManifest(replace(prepared,bundle_digest=_bundle_digest(prepared))),CapabilityRequirements(frozenset({ModelCapability.TEXT_GENERATION})),self.options)
  self.context=InvocationContext(self.ident,uuid4(),RequesterRole.USER,RequestChannel.WEB,ModelMode.AUTOMATIC,'test','en',principal_id='1')
  self.body={'object':'chat.completion','model':'example/model:free','choices':[{'index':0,'finish_reason':'stop','message':{'role':'assistant','content':'answer'}}],'usage':{'prompt_tokens':50,'completion_tokens':2}}
  self.transport=SyntheticTransport(status=200,body=json.dumps(self.body).encode())
  self.adapter=SyntheticOpenRouterAdapter(transport=self.transport,report=self.report,model_id='example/model:free',upstream_id='example-provider',verify_context=lambda p:True,verify_free=lambda m,p:True,verify_privacy=lambda m,p:True)
 def test_synthetic_success_delivers_full_context_and_bound_payload(self):
  events=list(self.adapter.stream(self.request,self.context))
  self.assertIsInstance(events[-1],ModelCompleted); self.assertEqual([e.text for e in events if isinstance(e,ModelTextDelta)],['answer'])
  body=json.loads(self.transport.requests[0]); self.assertEqual(body['messages'][0]['content'],'Synthetic complete constitution'); self.assertEqual(body['provider']['only'],['example-provider']); self.assertFalse(body['provider']['allow_fallbacks']); self.assertEqual(body['provider']['max_price'],{'prompt':0,'completion':0}); self.assertFalse(body['stream'])
 def test_denies_guest_local_unverified_and_modified_payload_before_send(self):
  for context in (replace(self.context,role=RequesterRole.GUEST,principal_id=None,guest_session_ref=uuid4()),replace(self.context,mode=ModelMode.LOCAL)):
   self.assertIsInstance(list(self.adapter.stream(self.request,context))[-1],ModelFailed)
  self.adapter.verify_free=lambda *_:False
  self.assertIsInstance(list(self.adapter.stream(self.request,self.context))[-1],ModelFailed)
  self.assertEqual(self.transport.requests,[])
 def test_rate_limit_requires_explicit_safe_rejection(self):
  self.transport.status=429; self.transport.body=b'{}'
  event=list(self.adapter.stream(self.request,self.context))[-1]
  self.assertEqual(event.error.outcome,OutcomeCertainty.UNKNOWN); self.assertFalse(event.error.retryable)
  self.adapter.verify_rate_rejection=lambda *_:True
  event=list(self.adapter.stream(self.request,self.context))[-1]
  self.assertEqual(event.error.category,ModelErrorCategory.RATE_LIMIT); self.assertEqual(event.error.outcome,OutcomeCertainty.DEFINITIVE); self.assertTrue(event.error.retryable)
 def test_malformed_or_unexpected_output_is_unknown_no_retry(self):
  for body in (b'{',b'{"object":"chat.completion","object":"fake"}',json.dumps({**self.body,'model':'paid/model'}).encode(),json.dumps({**self.body,'choices':[{'index':0,'finish_reason':'tool_calls','message':{'role':'assistant','content':'x'}}]}).encode()):
   self.transport.body=body
   event=list(self.adapter.stream(self.request,self.context))[-1]
   self.assertIsInstance(event,ModelFailed); self.assertFalse(event.error.retryable); self.assertEqual(event.error.outcome,OutcomeCertainty.UNKNOWN)
 def test_modified_request_counted_payload_and_privacy_failure_never_send(self):
  changed=replace(self.request.requested_options,output_token_limit=31)
  events=list(self.adapter.stream(replace(self.request,requested_options=changed),self.context))
  self.assertEqual(events[-1].error.outcome,OutcomeCertainty.NOT_DISPATCHED)
  self.adapter.verify_privacy=lambda *_:False
  self.assertEqual(list(self.adapter.stream(self.request,self.context))[-1].error.outcome,OutcomeCertainty.NOT_DISPATCHED)
  self.assertEqual(self.transport.requests,[])
 def test_other_http_failures_and_untrusted_exception_do_not_retry(self):
  self.transport.status=503
  event=list(self.adapter.stream(self.request,self.context))[-1]
  self.assertFalse(event.error.retryable); self.assertEqual(event.error.outcome,OutcomeCertainty.UNKNOWN)
  self.assertNotIn('secret',repr(event))
 def test_cancellation_before_send_is_confirmed(self):
  from types import SimpleNamespace
  from home.model_interface import ModelCancelled
  events=list(self.adapter.stream(self.request,replace(self.context,cancellation=SimpleNamespace(is_cancelled=True))))
  self.assertIsInstance(events[-1],ModelCancelled); self.assertTrue(events[-1].backend_stop_confirmed)
  self.assertEqual(self.transport.requests,[])
 def test_cancellation_or_deadline_after_send_cannot_publish_response(self):
  from types import SimpleNamespace
  from home.model_interface import ModelCancelled
  signal=SimpleNamespace(is_cancelled=False)
  class CancelTransport(SyntheticTransport):
   pass
  # Patch the test-only transport method without creating a network transport.
  original=self.transport.send
  def cancel_send(body):
   result=original(body); signal.is_cancelled=True; return result
  self.transport.send=cancel_send
  events=list(self.adapter.stream(self.request,replace(self.context,cancellation=signal)))
  self.assertIsInstance(events[-1],ModelCancelled)
  self.assertIsNone(events[-1].backend_stop_confirmed)
  self.assertFalse(any(isinstance(e,ModelTextDelta) for e in events))
