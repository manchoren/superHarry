# T214 Gmail local read-only/draft contract

Date: 2026-11-15

## Implemented boundary

- `home/gmail_contracts.py` accepts only a Gmail mailbox identity and the
  exact `gmail.readonly` scope.
- It validates bounded, untrusted inbound message fields and reuses the T233
  `ChannelAttachment` reference contract without reading or copying bytes.
- Local drafts are immutable values bound to the configured mailbox identity,
  retain the source message reference, and require human review.
- Draft creation requires an injected audit sink and emits only non-content
  metadata (account, source message id, draft id and attachment storage ids).
  An unavailable or failing audit sink fails closed before the draft is
  returned.
- `SEND` is explicitly rejected; no SMTP, Gmail send, native Gmail draft,
  OAuth, HTTP, filesystem or credential operation exists in this module.

## Validation

```text
manage.py test home.test_t214_gmail_contracts
manage.py check
git diff --check
```

## Limits and open gates

This is a local contract only. It does not prove Google consent, account
ownership, OAuth client review, protected token custody, Gmail API access,
SPF/DKIM/DMARC, channel transport, T238 persistence/authorization, attachment
staging execution, VM validation, deployment or production acceptance. T214
remains Pending.
